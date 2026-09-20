---
name: hermes-model-chain-wiring
description: "Wire custom provider chains with fallback into Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, models, providers, fallback, mcp, config]
    related_skills: [hermes-agent, hermes-credentials-setup, vertex-provider-setup]
---

# Hermes Model Chain Wiring

Wire main models, fallback chains, named custom providers, and lightweight remote MCP servers into Hermes config without hand-editing config.yaml.

## When to Use

- User asks to set or replace the primary inference model/provider
- User wants a fallback chain across multiple vendors
- User wants to add a custom OpenAI-compatible provider not in the built-in catalog
- User wants to add a remote HTTP MCP server (e.g. context7, grep.app, GitHub Copilot remote)
- User asks which free models a provider/gateway exposes → use `references/claude-desktop-3p-gateway-inference.md` § Free model catalog probes
- Don't use for: installing the `mcp` Python SDK itself (use `pip install mcp`), or for provider OAuth flows (`hermes auth`)

## Procedure

### 0. Pre-flight & User Confirmation Gate (Mandatory)
When the user asks to alter the model chain or provider routing:
1. **Consult Obsidian operational notes first** (e.g. `运维速查/Hermes运维速查.md`, `各供应商免费额度机制.md`) to read known-good endpoints, token limits, and past pitfalls.
2. **Do NOT apply changes immediately**: Present an itemized proposal list (Primary, Fallback 1, Fallback 2/兜底, Auth source, Endpoints) to the user.
3. **Wait for explicit approval** ("确认" or "开干") before writing any changes to `config.yaml` or `.env`.

### 1. Read-before-write: inspect current state
```python
# Load live config without triggering gateway restart
from hermes_cli.config import load_config
import json, sys
sys.path.insert(0, '<HERMES_INSTALL_PATH>/hermes-agent')
cfg = load_config()
print(json.dumps(cfg.get('model'), indent=2))
print(json.dumps(cfg.get('fallback_providers'), indent=2))
print(json.dumps(cfg.get('providers'), indent=2))
```
Note: `<HERMES_INSTALL_PATH>` is typically `C:\Users\<user>\AppData\Local\hermes\hermes-agent` on Windows or `~/.hermes/hermes-agent` on Linux/macOS.

### 2. Confirm provider & model IDs against built-in catalog
```python
from providers import list_providers
names = [getattr(p, 'name', str(p)) for p in list_providers()]
print([n for n in names if 'agnes' in n.lower() or 'opencode' in n.lower() or 'nara' in n.lower()])
```
If the provider is not in the built-in catalog, it must be registered as a **named custom provider** under `providers:` in config.yaml (see step 3). If it must also appear in the model picker (`hermes model`, desktop Models page, `/api/model/options`) with a live `/models` catalog, register a **user-level model-provider plugin** instead — `providers:` dict entries do not feed the picker. Layout: `$HERMES_HOME/plugins/model-providers/<name>/__init__.py` calling `register_provider(ProviderProfile(name=..., env_vars=(...,), base_url=..., fallback_models=(...), default_aux_model=...))` plus a minimal `plugin.yaml` (`name`, `kind: model-provider`, `version`, `description`). Discovery is lazy on first `list_providers()`; user plugins win on name collision. Verify picker visibility directly:
```python
import sys; sys.path.insert(0, '<HERMES_INSTALL_PATH>/hermes-agent')
import model_tools  # side effect: runs plugin discovery
from providers import get_provider_profile
from hermes_cli.models import provider_model_ids
from hermes_cli.inventory import build_model_options_payload, load_picker_context
assert get_provider_profile('<name>') is not None
print(provider_model_ids('<name>', force_refresh=True))
rows = build_model_options_payload(load_picker_context(), refresh=True)['providers']
print([r for r in rows if r['slug'] == '<name>'])  # expect authenticated: True + model list
```

### 3. Register named custom providers
Write to `providers:` dict (not `custom_providers:` list — the dict form is the modern shape):
```python
cfg.setdefault('providers', {})['agnes-ai'] = {
    'base_url': 'https://apihub.agnes-ai.com/v1',
    'key_env': 'AGNES_API_KEY',       # resolve from $HERMES_HOME/.env at runtime
    'api_mode': 'chat_completions',   # or 'codex_responses'
    'models': ['agnes-3.0-flash']
}
```
Hard invariants:
- **Secrets live in `.env` only** — use `key_env: <NAME>` and write the actual key to `$HERMES_HOME/.env`, never into config.yaml.
- **Never hand-edit config.yaml directly** — use `hermes config set` or the Python `load_config()` / `save_config()` API, which preserves YAML structure and validates types. Hand-edits risk corrupting the live gateway's view of the file.

### 4. Set the primary model
```bash
hermes config set model.default '<model-id>'
hermes config set model.provider '<provider-id>'
# Remove stale endpoint pins if switching to a built-in provider:
hermes config unset model.base_url 2>/dev/null || true
hermes config unset model.api_mode 2>/dev/null || true
```

### 5. Build the fallback chain
```python
cfg['fallback_providers'] = [
    # tried in order when the primary fails with 429/5xx/connection errors
    {'provider': 'vertex', 'model': 'google/gemini-3.8-flash',
     'base_url': '<vertex-openapi-endpoint>', 'api_mode': 'chat_completions'},
    {'provider': 'agnes-ai', 'model': 'agnes-3.0-flash',
     'base_url': 'https://apihub.agnes-ai.com/v1', 'key_env': 'AGNES_API_KEY',
     'api_mode': 'chat_completions'},
]
cfg.pop('fallback_model', None)  # legacy key; drop it so fallback_providers is the single source of truth
```
Verify with:
```bash
hermes fallback list
```

### 5.5 Wire the MoA preset (reference models + aggregator)
MoA presets live under `moa.presets.<name>` with `reference_models` (list of `{provider, model, enabled}`) and one `aggregator` (`{provider, model}`). Write them via the same `load_config()`/`save_config()` API, then validate before declaring done:
```python
cfg = load_config()
m = cfg.setdefault('moa', {})
m['default_preset'] = 'default'
p = m.setdefault('presets', {}).setdefault('default', {})
p['enabled'] = True
p['reference_models'] = [
    {'provider': '<ref-provider>', 'model': '<ref-model>', 'enabled': True},
]
p['aggregator'] = {'provider': '<agg-provider>', 'model': '<agg-model>'}
from hermes_cli.moa_config import validate_moa_payload
assert validate_moa_payload(cfg.get('moa')) == [], validate_moa_payload(cfg.get('moa'))
save_config(cfg)
```
Rules:
- Every `(provider, model)` slot must already exist in the verified provider catalog (`provider_models_cache.json` or a live `/models` probe) — a slot pointing at an unregistered provider fails silently at turn time.
- Keep `enabled: True` on each slot; a slot without it may be skipped by the runtime normalizer.
- Prefer architecturally diverse references (different vendors/backbones) plus the strongest available aggregator; subscription-billed models (e.g. OAuth) cost zero marginal per call and suit the aggregator seat.

### 6. Verify each node actually resolves before declaring done
Do NOT stop at config-file correctness — probe each provider's real endpoint with a minimal request:
```python
import httpx, os
# Keyless built-in (opencode-free example)
headers = {'Authorization': '', 'User-Agent': 'HermesAgent/x.y.z',
           'x-opencode-session': 'session_<uuid>'}
r = httpx.post('https://opencode.ai/zen/v1/responses',
               json={'model': '<id>', 'input': [{'role':'user','content':'reply OK'}]},
               headers=headers, timeout=15)
print(r.status_code, r.text[:200])
```
A node is "verified" only when a real 200 response returns content — never assume success from a clean config write or a passing `hermes doctor`.

### 7. Handle data-training-tier confirmation gates
Some built-in free tiers (e.g. OpenCode Zen `*-contributor-free` models) refuse non-interactive runs unless the user explicitly accepts that their prompts may be used for training. When a probe is blocked by this gate:
```bash
hermes config set security.allow_data_training_tiers_noninteractive true
```
Only set this flag after the user has been told, in plain language, what "trains on your data" means for their use case.

### 8. Add lightweight remote MCP servers (prefer HTTP over local npx)
For a user with constrained hardware (e.g. laptop with 4GB VRAM / 16GB RAM), prefer **remote HTTP MCP** over stdio/npx servers — no local process, no npm install, no Node runtime needed. Edit `mcp_servers:` via the same `load_config()`/`save_config()` API:

```python
# Proven remote MCP presets:
# 1. Context7 (Official framework/library documentation)
cfg.setdefault('mcp_servers', {})['context7'] = {
    'url': 'https://mcp.context7.com/mcp',
    'headers': {'Authorization': 'Bearer <CONTEXT7_API_KEY>'},
    'timeout': 60, 'connect_timeout': 30,
    'sampling': {'enabled': False}
}

# 2. Grep.app (Global open-source code search, keyless)
cfg.setdefault('mcp_servers', {})['grepapp'] = {
    'url': 'https://mcp.grep.app',
    'timeout': 60, 'connect_timeout': 30,
    'sampling': {'enabled': False}
}

# 3. GitHub Copilot Remote MCP (Repository/Issue/PR/Code search management, 44 tools)
cfg.setdefault('mcp_servers', {})['github'] = {
    'url': 'https://api.githubcopilot.com/mcp/',
    'headers': {'Authorization': 'Bearer <GITHUB_PAT>'},
    'timeout': 60, 'connect_timeout': 30,
    'sampling': {'enabled': False}
}

# 4. Cloudflare Remote MCP (Docs, OpenAPI search, and execute JS for Workers/KV/D1/R2/DNS)
cfg.setdefault('mcp_servers', {})['cloudflare'] = {
    'url': 'https://mcp.cloudflare.com/mcp',
    'headers': {'Authorization': 'Bearer <CFAT_ACCOUNT_TOKEN>'},
    'timeout': 60, 'connect_timeout': 30,
    'sampling': {'enabled': False}
}
```
Do **not** use `hermes mcp add <name>` for this — it is an interactive, discovery-first flow that can block waiting on TTY input in an agent session; writing the `mcp_servers:` dict directly via the config API is deterministic and non-interactive.

Verify:
```bash
hermes mcp test <server-name>
```

### 9. Restart the gateway so new config takes effect
Model/provider changes are picked up on the next agent process start; a running gateway does not hot-reload `config.yaml`.
```bash
hermes gateway restart   # or, on Windows with Job-Object issues: schtasks /Run /TN Hermes_Gateway
```

### 10. OpenAI Codex OAuth Device-Code Flow (Zero-API-cost ChatGPT models)
To connect the user's ChatGPT Plus/Team/Pro subscription without separate API costs:
1. Run `hermes auth add openai-codex --type oauth --no-browser --timeout 300` in the background (using `terminal(background=true)`).
2. Read the live output using `process_manage(action='log')` to capture the device URL (`https://auth.openai.com/codex/device`) and the one-time code.
3. Immediately present the link and code to the user in chat so they can approve in their browser.
4. Poll until the command completes and verify via `hermes auth list`.
5. This unlocks access to `gpt-5.6-luna`, `gpt-5.6-luna-900k`, `gpt-5.6-sol`, etc., billed under their existing ChatGPT subscription.

### 11. Prefer Native Plugins over Local stdio/npx MCPs for Simple APIs
For services that have a built-in Hermes plugin (e.g. Tavily search):
- Avoid `npx tavily-mcp` (spawns an extra Node.js resident process, vulnerable to Windows npm timeouts).
- Prefer enabling the bundled plugin: `hermes plugins enable web-tavily` and inject `TAVILY_API_KEY` into `$HERMES_HOME/.env`. This runs in-process with zero extra memory overhead.

### 11.5 Unknown Key-Prefix / Router Providers
When the user hands over a key with a prefix Hermes has no built-in profile for (e.g. `atr_`, `tr_`, `sk-apx`):
1. **Never guess the base URL** — a wrong endpoint silently burns turns. Try the likely `/v1/models` list endpoint with the key (`GET <base>/models`, Bearer header).
2. If the list endpoint returns 404/401 or the provider has no documented list API, register it as a **generic OpenAI-compatible router** under `providers:` (`base_url` + `key_env` + `api_mode: chat_completions`, no `models` field) — model names are then passed verbatim by the user via `hermes -z "..." -m <model> --provider <name>`. Say so explicitly in the reply.
3. **Always archive the key into the user's central credential catalog** (e.g. desktop `apikey.txt`) with a labeled section before or after wiring it, per the standing catalog-sync rule.

### 12. Subagent / Delegation Model & Reasoning Configuration
Standing preference: `delegate_task` calls carry no per-call model pin — children inherit the running model. Only write a `delegation.model`/`provider` pin when the user explicitly asks for a dedicated subtask model.
To dedicate a specific high-capability model (e.g. `gpt-5.6-luna`) and reasoning depth (e.g. `high`) to subtasks / child agents without changing the primary interactive model:
```python
cfg = load_config()
d = cfg.setdefault('delegation', {})
d['provider'] = 'openai-codex'
d['model'] = 'gpt-5.6-luna'

a = cfg.setdefault('agent', {})
a['reasoning_effort'] = 'high'
a.setdefault('reasoning_overrides', {})['gpt-5.6-luna'] = 'high'
save_config(cfg)
```
Child subagents automatically inherit enabled MCP toolsets (`inherit_mcp_toolsets: true`), enabling them to autonomously access GitHub, Context7, and other remote tools.

### 13. Trim skill bloat via skills.disabled (prompt-size triage)
When every skill shows enabled and the built system prompt is oversized, disable by name globally:
```bash
hermes config set skills.disabled '["skill-a", "skill-b"]'
hermes config get skills.disabled
hermes skills list   # tail line reports "N enabled, M disabled"
```
Rules:
- Resolve names from the loader (`_find_all_skills`), not from the truncated table display.
- `hermes-agent` is in `ESSENTIAL_SKILLS` and is silently dropped from any disabled list — never include it.
- Disabled state is global-union-platform (`skills.disabled` plus `skills.platform_disabled.<platform>`); globally disabled stays disabled everywhere.
- Takes effect on new sessions only — `/reset` or open a new session; long-history sessions keep the old system prompt.
- Verify three layers agree: raw YAML under `skills:` in config.yaml, `hermes skills list` counts, and `get_disabled_skills(load_config(), None)` returning the same set.

## Pitfalls

- **Writing `skills.disabled` requires `--force`** — without it the CLI writes nothing (`nothing was written`); verify with `config get` and `skills list` counts afterward.

- **Never hand-edit `config.yaml` with `write_file` or `patch`** — Hermes internal safety guardrails actively reject direct tool writes (`Refusing to write to Hermes config file: Agent cannot modify security-sensitive configuration`). Always route changes through `hermes config set/unset` CLI or the Python `load_config()`/`save_config()` API.
- **Probe vendor free-tier restrictions and payment walls before wiring as primary:** Models marked "free" frequently have deceptive prerequisites: OpenCode contributor models (`*-contributor-free`) enforce caller origin checks and reject external API / Hermes calls with `HTTP 403: OpenCode's free tier can only be used from within OpenCode`; router free pools (e.g. NaraRouter) often block uncredited accounts with 403 (`Your plan does not include the requested model`) or 402/429 (`Insufficient credits`). Always probe `/v1/chat/completions` with the user's real key before setting a model as primary.
- **Avoid small-parameter over-distilled models as agent primary brains:** Free models below 30B (e.g. LongCat) exhibit severe hallucination rates under multi-step agent tool loops and code execution. For an autonomous agent driving tools, default to battle-tested frontier base models (e.g. Google Vertex Gemini Flash) or full-scale reasoning models (e.g. DeepSeek-R1) to prevent hallucinated commands and looping.
- **`fallback_model` is legacy** — if both `fallback_model` and `fallback_providers` exist, the chain merges with dedup; drop `fallback_model` after migrating so there's one source of truth.
- **Don't confuse `providers:` (named custom provider registry) with `mcp_servers:` (MCP tool servers)** — they are unrelated config sections; a provider entry never registers MCP tools and vice versa.
- **Keyless built-in providers need the right extra headers** — e.g. `opencode-free` requires `x-opencode-session` on every request for session-affinity routing; a plain empty-Authorization POST returns 400 `MissingSessionID` without it.
- **`hermes doctor` does not validate provider connectivity** — it checks local file/venv/SSl state only; a clean doctor run says nothing about whether a provider endpoint actually accepts your model ID or key.
- **The picker reads a 1h disk cache** (`$HERMES_HOME/provider_models_cache.json`) — after registering a provider, open the picker with Refresh (`/api/model/options?refresh=true`) or the new vendor stays invisible.
- **The desktop app spawns its own `serve` backend at launch** — new provider plugins appear only after a full app restart, and only when the desktop is connected to the local backend (a remote/cloud backend has its own plugin dir).
- **A key added to `.env` is invisible to a running backend until it restarts.** `is_provider_explicitly_configured()` reads `os.environ`, which `load_hermes_dotenv()` populates once at process startup — a live gateway, desktop `serve` backend, or bare `venv python` probe all keep seeing the old env. Symptom: the model switcher (chat pickers default `explicit_only=true`) hides the provider, and Refresh Models cannot help because the disk cache is keyed on the same gate. Fix: fully quit the desktop app (the serve backend dies with it) or restart the gateway, then confirm with `is_provider_explicitly_configured('<slug>')` in a dotenv-loaded python before declaring the wiring broken. `hermes auth status <slug>` reporting logged-in does not prove this — pool entries and the explicit gate are separate signals.
- **Verify `key_env` against the `.env` FILE content, not `printenv`.** Grep the `KEY=` line in `$HERMES_HOME/.env` — a transient shell export makes the process env look set while the persistent file is missing or uses a near-miss name (e.g. `ATR_API_KEY` vs official `ATRIA_API_KEY`), and the setting vanishes on gateway restart.
- **A `⚠ <vendor> (HTTP 403)` next to a `✓` in doctor's API Connectivity is the probe's default User-Agent hitting Cloudflare, not a bad key** — re-probe with a browser UA before rotating anything.
- **Do not run `hermes mcp add` in an agent/CLI session** — it is an interactive TTY prompt flow and will hang waiting for input; write `mcp_servers:` entries via the config API instead.
- **Disable `sampling` for untrusted remote MCP servers** — `sampling.enabled` defaults to `true`, letting a remote server request LLM completions through the agent; set `sampling: {enabled: false}` unless you specifically need it.
- **Windows OneDrive-synced desktop paths** — if a user keeps `apikey.txt` or similar on `~/OneDrive/桌面/`, resolve via `~/OneDrive/桌面`, not `~/Desktop` (Known Folder Move redirects Desktop there).
- **OneDrive sync churn** — never leave the only copy of a service-account JSON or credentials file on a OneDrive-synced path; copy into `$HERMES_HOME/` (non-synced) before wiring it into config.
- **Central credential catalog sync** — when discovering new credentials from subdirectories (e.g. `新机设置/cloudflare.txt`), always sync them into the user's central credentials file (`apikey.txt` on desktop) and `$HERMES_HOME/.env` simultaneously so keys never diverge.
- **Cloudflare Account Token (`cfat_`) vs User Token (`cfut_`)** — Cloudflare account tokens (`cfat_...`) authenticate against `/accounts/<account_id>/ai/v1` and the remote MCP endpoint, but `/user/tokens/verify` will return HTTP 401 because that endpoint is strictly for user tokens; test account tokens against `/accounts/<account_id>/ai/v1/chat/completions` directly.
- **Cloudflare web asset detection (Workers vs Pages)** — web apps and static sites on Cloudflare can be deployed under either Cloudflare Pages (`/pages/projects`) or Cloudflare Workers (`/workers/scripts`); query both endpoints when listing, inspecting, or deleting user web assets.
- **OpenAI Codex OAuth quota attribution** — inspect the JWT payload (`chatgpt_plan_type`) to verify account tier; device-code OAuth binds to the user's ChatGPT subscription (drawing from rolling rate limits without developer API credit charges), but high-turn autonomous loops can exhaust free-tier windows.
- **Preserve exact model ID capitalization for case-sensitive vendors** — e.g. `Atria-Dawn-Preview` must keep its capitals across config, env, and request bodies; lowercasing breaks routing even when endpoint and key are correct.
- **Check input modalities before wiring** — text-only models reject binary attachments, so block image/PDF reads or pre-extract to text upstream; image-capable models (e.g. `agnes-3.0-flash` accepting `image_url`) need no such guard.
- **Label the benchmark source and harness per score; never merge different harnesses into one ranked column.** Vendors self-report on disjoint sets (HF card vs tech report vs Artificial Analysis), so mixed cells imply a head-to-head that never ran — use `-` for missing同口径 values with the source in the note.
- **On Telegram, present model comparisons as short bullets plus an optional xlsx, never Markdown tables.** Telegram renders tables as crushed plain text — one line per metric with a verdict tag (第一 / 中上 / 中档 / 偏弱) beats a table, and reserve the xlsx skill for the full matrix.
- **Precision when restoring disabled toolsets** — when the user asks to "restore/open closed tools but keep originally disabled ones closed", compare against the session's initial baseline; never blindly re-enable toolsets that were already disabled at session start (e.g. `video`, `kanban`, `a2a`).
- **Sync live chain changes back into the Obsidian ops notes** — the vault drifts within days (stale fallback lists mislead the next triage); after any model/fallback/MCP change, update the matching速查 sections and bump their `updated` field in the same session.
- **Gateway streaming has two switches with different scopes** — top-level `streaming.enabled` is the gateway master while `display.streaming` is CLI-only, so a `true` there with the gateway `false` still delivers whole-turn replies that feel slow; check `hermes config get streaming` before blaming the model.
- **Confirm a referenced file exists before mounting it in config** — adding a missing path (e.g. an `instructions` entry) silently breaks the consumer; `read_file` the target first and recreate it from the canonical source when absent, then reference it.
- **Probe every candidate provider before declaring a model unavailable** — a single provider's 500/403 (e.g. OpenCode Zen free tier) does not mean the model is unusable; the same model ID often runs free on another gateway (e.g. OpenRouter). Scan the full provider set, check the live catalog and pricing, then run a minimal 200 probe (or the appropriate 200-content request) on each candidate before switching or reporting unavailability.
- **OAuth-backed MCPs park and retry with no cached token** — a headless `mcp test` reporting missing cached tokens means the server keeps emitting retry noise; either complete `hermes mcp login <name>` interactively or remove the server instead of leaving it parked.
- **Decommissioning a vendor means sweeping every slot that names it** — `fallback_providers`, `providers:`, `moa.presets.*.reference_models`, plus sibling consumers (OpenCode `opencode.json`, ops notes). A leftover reference keeps calling the dead endpoint. Save via the config API, then grep the file for the vendor string and require zero hits — a merge-style save can resurrect a deleted entry, so verify from disk, never from the in-memory dict.
- **Silent fallback masking primary failure causes latency and model misidentification** — when a configured primary model fails with 5xx/429, Hermes retries 3 times before silently routing to `fallback_providers` (e.g. falling back to Vertex). The conversation turn succeeds, but each turn pays a multi-second retry penalty, and runtime switch notes in prompt context will mislead the agent into claiming it is running as the failed primary. When verifying model switches or triaging unavailability reports, inspect `logs/agent.log` for `Fallback activated: <model> → <fallback>` and test the endpoint directly with curl/httpx. If the primary consistently returns 500, immediately switch `model.default` off it rather than leaving turns to ride on fallback.
- **Third-party gateway models must be pinned explicitly, not auto-discovered** — a gateway that speaks a vendor-neutral or non-Claude-flavored model catalog (OpenRouter model IDs like `stealth/union-alpha`, `nvidia/nemotron-3.5-lightning:free`, etc.) does not reliably surface every entry through the provider's generic model-list flow. When `modelDiscoveryEnabled` is on and discovery either 4xx/429s or filters out non-Claude names, the client falls back to a default that is often a paid Claude model, which then 403s on a key whose monthly quota is exhausted. For OpenRouter-as-gateway deployments, set `modelDiscoveryEnabled: false` and list the exact target model IDs in `inferenceModels`, with the desired default first.
- **OpenRouter HTTP 403 `Key limit exceeded (monthly limit)` is a key-level quota error, not a misconfiguration** — it fires when the request would bill a paid model (typically a Claude model auto-selected by discovery/default fall-through) on a key whose rolling monthly spend cap has been hit. It is NOT the same root cause as 429 `rate_limit_exceeded` on a free shared-pool model (`stealth/union-alpha`, `openrouter/free`), which is transient. Before changing configuration in response to a 403, confirm which model ID the request actually carried — if it was a paid Claude model, switch to a known-200 free model (verified live in the same session) instead of rotating keys or editing the endpoint.
- **The same model ID can succeed at one OpenAI-compatible endpoint and fail at the Anthropic Messages endpoint** — OpenRouter's `/api/v1/chat/completions` returning 200 for a model does not guarantee `/api/v1/messages` works for the same model, and vice versa; when wiring a client that speaks the Anthropic Messages protocol (Claude Desktop 3P, Claude Code gateway mode), probe the specific `POST /v1/messages` endpoint you will actually use, not just any 200 from a sibling endpoint. Full key map, JSON recipe, and 403/429 triage table for the Claude Desktop 3P window: see `references/claude-desktop-3p-gateway-inference.md`.

### 14. Claude Desktop 3P (gateway) inference configuration
Claude Desktop's "Configure Third-Party Inference" path is a **separate, user-level config store** — not Hermes `config.yaml`/`.env`, not Claude Code's `ANTHROPIC_BASE_URL`/`settings.json` env vars.
- Location (Windows, single-user, no MDM): `%LOCALAPPDATA%\Claude-3p\configLibrary\<appliedId>.json` (`appliedId` from the sibling `_meta.json`). Changes only take effect on a full app quit+relaunch.
- Open the in-app window via **Help → Troubleshooting → Enable Developer Mode** (app restarts), then **Developer → Configure Third-Party Inference…**, fill in **Connection** (provider = `Gateway`, `Gateway base URL`, `Credential kind`, `Gateway API key`, `Gateway auth scheme`) and the **Models** section, then **Apply Changes → Save & Restart**.
- For OpenRouter: `inferenceGatewayBaseUrl = https://openrouter.ai/api` (NOT `/api/v1`); full Messages path is `/api/v1/messages`; `inferenceCredentialKind = static`; `inferenceGatewayAuthScheme = bearer`; paste the raw key with no `Bearer ` prefix.
- `inferenceModels` entries are either plain ID strings or objects (`{"name": <exact gateway model ID>, "labelOverride": <display name>}`); the first entry is the default model. `labelOverride` is display-only — the app still sends `name` to the gateway.
- Because auto-discovery filters out model IDs that are not recognizably Claude, non-Claude-named gateway models (e.g. `stealth/union-alpha`, `nvidia/nemotron-3.5-lightning:free`) generally require `modelDiscoveryEnabled: false` plus an explicit `inferenceModels` list, or they never appear in the picker / default falls through to a paid Claude model.
- `supports1m` / `prefer1m` are capability assertions — only set them if you have separately confirmed that specific deployment accepts a 1M-token context window; do not guess them on.
- Do not confuse this with Hermes or Claude Code CLI gateway env vars: editing `ANTHROPIC_BASE_URL`/`settings.json` has no effect on the desktop app's 3P routing.

### 15. Refresh & audit the provider model catalog
When the user asks to refresh provider model lists, check which models are still available, or audit retired/changed models:
1. **Refresh the picker disk cache with a non-interactive command:**
```bash
hermes model --refresh </dev/null
```
This wipes `$HERMES_HOME/provider_models_cache.json` and re-fetches every configured provider's live `/v1/models` list. Piping `/dev/null` keeps the provider picker from blocking on TTY input and it exits with "No change" without altering `config.yaml`.
2. **Verify the refresh actually landed** — don't trust the command's exit: read the cache back and confirm each provider's `at` timestamp is seconds-to-minutes old and the model counts look sane.
```python
import json, time
data = json.load(open(r'C:/Users/mnb77/AppData/Local/hermes/provider_models_cache.json'))
for slug, v in data.items():
    print(slug, time.ctime(v.get('at')), len(v.get('models', [])))
```
3. **Report the delta, not just success** — compare counts against the pre-refresh state and call out anything that disappeared (retired models) or newly appeared, plus the current default model/provider if it changed. This is what the user actually wants to know.

### 16. Scheduled headless health probe & watchdog pattern (Zero-resident, Zero-token)
To protect against primary model dropouts (e.g. 403 provider changes) without burning tokens or running heavy resident daemons:
1. **Deploy a standalone probe script** under `$HERMES_HOME/scripts/model_chain_probe.py`:
   - Inspects `config.yaml` to detect the live primary and fallback chain.
   - For Vertex providers, call `from agent.vertex_adapter import get_vertex_credentials` after loading `$HERMES_HOME/.env` to obtain a fresh OAuth2 Bearer token (raw HTTP without this returns 401).
   - Sends a minimal single-word probe (`max_tokens: 5`, 10s timeout) to verify HTTP 200.
2. **Register a Hermes native Cronjob with `no_agent: true`**:
   - Schedule at user-desired intervals (e.g. `every 8h`).
   - Use `no_agent: true` so the Hermes scheduler runs the script directly with 0 LLM inference tokens and no reasoning overhead.
3. **Enforce the Watchdog Silent Pattern**:
   - Healthy state: produce **empty stdout** and exit 0. Under `no_agent: true`, empty stdout sends nothing to messaging platforms, avoiding alert spam.
   - Failure state: print an itemized alert with fallback candidate availability and exit non-zero, immediately notifying the user.
   - Recovery state: if previous state was failed and now passes, print a brief recovery notice.

### 17. Post-automation side-effect verification (Mandatory)
After wiring automated health checks or cron jobs, verify four criteria with real tool outputs before declaring done:
1. **Process & Memory Footprint**: inspect task list (`tasklist | grep python`) to confirm zero new resident daemon processes; the probe must run on Gateway's existing internal scheduler and exit in <2s.
2. **Token & Billing Overhead**: confirm `no_agent: true` is set, ensuring 0 LLM reasoning tokens are billed for maintenance.
3. **Noise & Messaging Interruption**: confirm healthy runs produce empty stdout, preventing recurring chat notification clutter.
4. **Configuration Integrity**: run `hermes config check` to confirm `config.yaml` remains pristine and uncorrupted.

Pitfalls:
- **Vertex bare probe 401 authentication trap** — Vertex AI openapi endpoints require a rolling OAuth2 bearer token, not a static API key. Probing it from an external script requires loading `$HERMES_HOME/.env` first, then calling `from agent.vertex_adapter import get_vertex_credentials` to mint the token; hitting the endpoint directly without this headers returns `401 Request is missing required authentication credential`, falsely flagging the provider as down.
- **Retired stealth/preview models leave a ghost in the picker:** a slug like `x-preview-f-free` can stay selectable in the OpenCode Zen picker even after the relay retires it — selecting it fails every request (401/404). A fresh `--refresh` prunes it from the cached list; if it still shows, it is a picker-side bug, not a live model.
- **Windows path gotcha:** native Windows programs (git, rg, node, python) do not accept MSYS-style `/c/...` paths — pass `C:/Users/<user>/...` style paths or they fail with 'cannot change to' / 'not found'. Use bash builtins (`cd`, `ls`) freely, but when a native tool reads a file, use the native path form.
- **The cache file is keyed by provider slug, not model name** — each entry carries `fp` (fingerprint), `at` (fetch time), and `models` (list). A stale `at` older than an hour means the last refresh predates the provider's catalog change; refresh before drawing conclusions about availability.

## Verification Checklist

- [ ] `hermes fallback list` shows the exact chain the user requested, in order
- [ ] `hermes config get model` reflects the new primary provider+model
- [ ] A real 200-content probe succeeded for each provider in the chain (not just a config write)
- [ ] `hermes mcp test <name>` connects and lists expected tools for each new remote MCP server
- [ ] Gateway restarted after config changes (`hermes gateway status` shows a fresh PID)
- [ ] No secrets were written into `config.yaml`; all keys live in `$HERMES_HOME/.env` (referenced via `key_env`)
- [ ] After a catalog refresh: `provider_models_cache.json` `at` timestamps are current for every provider, and any model the user flagged as retired is confirmed absent from its provider's list
