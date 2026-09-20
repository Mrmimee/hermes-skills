---
name: ccswitch-provider-db
description: "Add or edit CC Switch providers by writing its SQLite DB."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cc-switch, provider, codex, claude-desktop, sqlite, gateway, config]
    related_skills: [claude-desktop-llm-gateway, hermes-model-chain-wiring]
---

# CC Switch Provider DB

Write or edit provider entries in CC Switch's SQLite database directly, without driving the GUI. Use when the user asks to "add a provider to CC Switch", "wire up keys in ccswitch", or "configure Codex/Claude-Desktop providers" and CC Switch is already installed.

CC Switch stores all provider state in `~/.cc-switch/cc-switch.db` (SQLite). The running app caches the provider list in memory; after a DB write, CC Switch picks up new providers on next launch. The target app (Codex / Claude Desktop) must be restarted for the config to take effect.

## When to Use

- "Add OpenRouter / Nous / NVIDIA as a Codex or Claude Desktop provider in CC Switch"
- "Configure CC Switch for free models"
- "Write a new provider card without clicking through the UI"
- "Import existing keys from `apikey.txt` into CC Switch"

Do not use when CC Switch is not installed, or when the user wants to drive the GUI interactively — in that case just point to the preset in the CC Switch add-provider panel.

Also use this skill's territory when Codex or Claude Desktop requests fail through the CC Switch local proxy (400/401/upstream errors). Diagnostic method, log locations, and the tool-variant fix: `references/codex-proxy-troubleshooting.md`.

## Procedure

### 1. Locate the DB

On Windows: `%USERPROFILE%\.cc-switch\cc-switch.db`. The relevant table is `providers`.

### 2. Read existing provider rows to understand the schema

Before writing anything, dump at least one existing provider row for each `app_type` you plan to touch. This shows the exact shape of `settings_config` and `meta`.

```python
import sqlite3, json
con = sqlite3.connect('C:/Users/mnb77/.cc-switch/cc-switch.db')
cur = con.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info(providers)').fetchall()]
row = cur.execute("SELECT * FROM providers WHERE app_type=? AND is_current=1", ('codex',)).fetchone()
d = dict(zip(cols, row))
# Inspect: settings_config, meta, provider_type, category, icon, icon_color
```

**Never fabricate a schema from memory** — read the actual rows first. The `settings_config` structure differs per `app_type` and can change between CC Switch versions.

### 3. Get the real API key

The key must come from one of these sources, in priority order:
1. An existing CC Switch provider row of the same type already in the DB (most reliable)
2. The user's local credential catalog (`apikey.txt` on desktop / OneDrive)
3. A live `/v1/models` endpoint call to confirm the key works and to read `context_length`

Never invent a placeholder key. If you cannot find a real key, stop and ask the user — do not write a row with a fake key. If a draft INSERT ever runs with a placeholder anyway, DELETE the row and `con.rollback()` before continuing — a fake-key row committed to the DB looks like a working card.

When reading keys out of DB rows or `apikey.txt` for reuse, keep the full key inside the script and print only a prefix + length (`sk-or-v1-2... len 73`) — never echo the full key in output, per the user's no-plaintext-keys rule.

### 4. Build the settings_config JSON

The `settings_config` column is a JSON string. Its shape depends on `app_type`:

**For `codex`** — `settings_config` contains three top-level keys:
```json
{
  "auth": { "OPENAI_API_KEY": "<key>" },
  "config": "<TOML string for config.toml>",
  "modelCatalog": { "models": [ ... ] }
}
```

The `config` field is a **TOML string**, not a dict. Example for a Responses-API provider:
```
model_provider = "custom"
model = "<model-id>"
model_reasoning_effort = "high"
disable_response_storage = true

[model_providers.custom]
name = "<provider>"
base_url = "https://example.com/v1"
wire_api = "responses"
requires_openai_auth = true
```

For OpenAI-Chat-format providers (e.g. NVIDIA NIM) the same TOML shape is used, but `meta` carries `"apiFormat": "openai_chat"` and optionally a `codexChatReasoning` block (see §5).

**For `claude-desktop`** — `settings_config` is simpler:
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://example.com",
    "ANTHROPIC_AUTH_TOKEN": "<key>"
  }
}
```

Model routes for claude-desktop go in `meta.claudeDesktopModelRoutes` (a dict keyed by role: `claude-sonnet-5`, `claude-opus-5`, `claude-haiku-4-5`).

### 5. Build the meta JSON

The `meta` column is also a JSON string. It carries flags and model-catalog data that CC Switch uses to render the provider card and drive local routing.

**Required meta keys for Codex third-party providers:**

| Key | Value | When |
|---|---|---|
| `apiFormat` | `"openai_responses"` or `"openai_chat"` | Always for non-official Codex providers. `openai_responses` = provider speaks native Responses API; `openai_chat` = provider speaks OpenAI Chat Completions and CC Switch's local proxy does the conversion |
| `endpointAutoSelect` | `true` | Usually |
| `codexFastMode` | `false` | Usually |

**`codexChatReasoning` block** (only when `apiFormat == "openai_chat"`):
```json
{
  "supportsThinking": false,
  "supportsEffort": true,
  "thinkingParam": "none",
  "effortParam": "reasoning_effort",
  "effortValueMode": "passthrough",
  "outputFormat": "reasoning_content"
}
```
Adjust `supportsThinking`/`supportsEffort` to match the actual upstream vendor.

**For Claude Desktop providers**, `meta` carries:

| Key | Value |
|---|---|
| `claudeDesktopMode` | `"proxy"` |
| `apiFormat` | `"anthropic"` or `"openai_chat"` |
| `claudeDesktopModelRoutes` | `{"claude-sonnet-5": {"model": "<real-id>", "labelOverride": "<label>"}, "claude-opus-5": {"model": "<1m-model>", "labelOverride": "<label>", "supports1m": true}}` |

For any route targeting a 1M context model (e.g. `claude-opus-5`), set `"supports1m": true` inside the route object. Without this flag, Claude Desktop defaults to a 200K context cap and ignores the upstream's 1M capacity.

### 6. Insert the row

The `providers` table has **16 columns**. Use a full-column INSERT — never rely on defaults for `meta` or `settings_config` (they must be JSON strings):

```python
import uuid, time, json
pid = str(uuid.uuid4())
cur.execute(
    """INSERT INTO providers
       (id, app_type, name, settings_config, website_url, category,
        created_at, sort_index, notes, icon, icon_color, meta,
        is_current, in_failover_queue, cost_multiplier, provider_type)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1.0, ?)""",
    (pid, 'codex', 'My Provider',
     json.dumps(settings_config),
     'https://example.com', 'aggregator',
     int(time.time() * 1000), 10, '', 'openrouter', '#6566F1',
     json.dumps(meta),
     None)
)
con.commit()
```

- `created_at` is **milliseconds** since epoch (not seconds)
- `is_current` = 0 (the new provider is not the active one until the user enables it)
- `provider_type` is `None` (NULL) for third-party providers; `"codex_oauth"` for the official ChatGPT Codex provider
- `icon` and `icon_color` are cosmetic only — any valid icon name and hex color work; copy from an existing row of the same vendor if unsure

### 7. Validate against the live endpoint

Before telling the user the provider is ready, curl the model list to confirm the key works and to get accurate context windows:

```bash
curl -s -H "Authorization: Bearer <key>" "<base_url>/v1/models" | python -c "import json,sys; d=json.load(sys.stdin); [print(m['id'], m.get('context_length','?')) for m in d.get('data',[]) if ':free' in m.get('id','')]"
```

Use the returned `context_length` values to fill `contextWindow` in `modelCatalog.models` entries — do not guess. Agnes AI (`apihub.agnes-ai.com/v1/models`) lists no `context_length`; its spec is Flash family 512K context / 64K output, Pro family 1M context / 64K output — use those.

### 7b. Sync the live Codex model catalog file when the card is active

The Codex desktop app reads its catalog from `~/.codex/cc-switch-model-catalog.json` (referenced by `model_catalog_json` in `~/.codex/config.toml`). CC Switch regenerates that file when it applies a card, but a card that is already `is_current=1` keeps the old file while you edit the DB. After changing `modelCatalog.models` (e.g. adding `contextWindow`), also write the same per-model `context_window` / `max_context_window` into the live JSON so an active Codex session immediately sees the new windows. Codex applies it on next session/config reload.

### 8. Tell the user what to do next

CC Switch must be **restarted** to pick up new DB rows (it caches the provider list in memory at launch). Codex / Claude Desktop must also be restarted for the config to take effect.

## Pitfalls

- **Never fabricate API keys** — always read the real key from an existing DB row or `apikey.txt`. A placeholder key written to the DB will appear as a working provider card but will silently fail on every request, and the user will not know the difference until they enable it.
- **Full-column INSERT** — the `providers` table has 16 columns; if you list fewer columns than you provide values for, SQLite raises `OperationalError: N values for M columns`. Always match the column list exactly.
- **`created_at` is milliseconds** — use `int(time.time() * 1000)`, not `int(time.time())`.
- **`settings_config` and `meta` are JSON strings** — `json.dumps()` them before passing to the INSERT. Passing a Python dict directly will either fail or store the repr, not valid JSON.
- **The `config` field inside Codex `settings_config` is a TOML string** — it looks like a raw TOML block, not a JSON object. Build it as a multi-line string with embedded newlines.
- **Always back up the DB before the first write of a session** (`shutil.copy` to `cc-switch.db.bak-<purpose>`) — the app is running and its schema is not user-managed; one bad INSERT is recoverable only if a pristine copy exists.
- **Verify after commit** — re-SELECT the new rows (name, key prefix, catalog models, meta) so the confirmation to the user is based on actual DB state, not on the INSERT returning success.
- **When upstream `/v1/models` returns `context_length: null`**, leave `contextWindow` out of the catalog entries rather than guessing — note in the reply that the user can fill it in the card UI later.
- **Before choosing `apiFormat`, probe the upstream** — curl `<base_url>/v1/chat/completions` and `<base_url>/v1/responses` with the real key; a provider that answers `/v1/responses` natively should use `openai_responses` direct (no local-routing dependency), while chat-only providers need `openai_chat` + local routing.
- **CC Switch caches in memory** — writes to the DB are not picked up by a running CC Switch instance. Tell the user to restart CC Switch before the new cards appear.
- **DB card and the live Codex file can drift** — when a Codex card is currently active (`is_current=1`), the running Codex instance uses `~/.codex/cc-switch-model-catalog.json` (referenced by `model_catalog_json` in `~/.codex/config.toml`), not the DB. After editing a card's `modelCatalog` in the DB, also write the same values (per-model `context_window` / `max_context_window`) into that live file — CC Switch regenerates it on its next run, but an active Codex session keeps the old 128K fallback values until then.
- **Missing `contextWindow` in a Codex catalog silently truncates context** — without the field, Codex falls back to a ~128K window and clamps long-context models. Fill it from the provider's model spec or a live endpoint probe; never omit it on a model known to have more than 128K.
- **Claude Desktop 1M routes require `supports1m: true`** — when mapping a 1M model (such as Claude Opus to a 1M upstream) in `claudeDesktopModelRoutes`, omitting `"supports1m": true` causes Claude Desktop to clamp to the default 200K window.
- **Probe individual model tiers for 403 entitlement** — a provider's `/v1/models` endpoint lists all supported catalog models, but free API keys often only have permission for Flash/standard tiers; flagship/Pro tiers return `403 Forbidden`. Probe the specific candidate model before declaring it active or default.
- **Do not set `is_current=1` on a new provider** — leave it at 0. The user must explicitly enable the provider from the CC Switch UI or tray menu; auto-activating it will override the user's current provider without their knowledge.
- **For `claude-desktop` providers, `meta.apiFormat` controls routing behavior** — `"anthropic"` means direct connection; `"openai_chat"` means CC Switch's local proxy does the Anthropic→OpenAI conversion. Getting this wrong means requests silently fail.
- **Read existing rows before writing** — always dump at least one existing provider row for the target `app_type` first. The schema can differ between CC Switch versions.
- **400 on `/responses` with "unknown variant" tool-type errors is a Codex-side issue, not a provider issue** — Codex desktop bundles computer-use/browser plugins that emit Responses-API `type: "namespace"` tools; most third-party upstreams (free aggregators, vendor proxies) only accept `function`. Diagnose with the variant isolation test in `references/codex-proxy-troubleshooting.md`, then fix by disabling the namespace-emitting plugins in `~/.codex/config.toml` (back up first) and restarting Codex.
