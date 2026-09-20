# Claude Desktop 3P (gateway) inference — key map, recipe, and OpenRouter 403 triage

Companion to the `hermes-model-chain-wiring` skill. Use when the task is Claude Desktop's own **third-party (3P) gateway inference** (the in-app "Configure Third-Party Inference" window), NOT Hermes `config.yaml`/`.env` and NOT Claude Code CLI `ANTHROPIC_BASE_URL`/`settings.json` env vars. Those are three separate, non-interfering stores.

## Where the config actually lives (Windows, single-user, no MDM)

- Local user-level store: `%LOCALAPPDATA%\Claude-3p\configLibrary\<appliedId>.json`
- `appliedId` is in the sibling `_meta.json` (`{"appliedId": "<uuid>", "entries": [...]}`); the applied config is `<appliedId>.json` in the same directory.
- **Reads happen at launch only.** After editing the JSON, fully quit and relaunch Claude Desktop, otherwise the app keeps the in-memory old config.
- The in-app window (**Help → Troubleshooting → Enable Developer Mode**, then **Developer → Configure Third-Party Inference…**) writes the same file; `Apply Changes → Save & Restart` is the supported path and it does the relaunch for you.

## OpenRouter-as-gateway key map (verified field names)

| In-app form field | JSON key | Value |
|---|---|---|
| Inference provider = Gateway | `inferenceProvider` | `gateway` |
| Gateway base URL | `inferenceGatewayBaseUrl` | `https://openrouter.ai/api` |
| Credential kind = Static API key | `inferenceCredentialKind` | `static` |
| Gateway API key | `inferenceGatewayApiKey` | raw key, no `Bearer ` prefix |
| Gateway auth scheme = Bearer | `inferenceGatewayAuthScheme` | `bearer` (default; only switch to `x-api-key` if the gateway reads that header) |
| Model list (first entry = default) | `inferenceModels` | array of ID strings or `{"name": ..., "labelOverride": ...}` objects |
| Auto-discover models on launch | `modelDiscoveryEnabled` | `true`/`false` |

- The gateway actually calls `POST {inferenceGatewayBaseUrl}/v1/messages`. For OpenRouter that is `https://openrouter.ai/api/v1/messages`. Do NOT put `/v1` in the base URL and do NOT use the OpenAI `/chat/completions` path — different protocol, different model routing.
- `inferenceModels` entry shape: plain ID string, or `{"name": "<exact ID the gateway's /v1/models returns>", "labelOverride": "<display name>"}`. `name` is what's sent to the gateway; `labelOverride` is picker-display only. The **first** entry is the default model.
- `labelOverride`/`supports1m`/`prefer1m` are for display and 1M-context assertions — only set `supports1m` after you've separately confirmed that exact deployment accepts a 1M-token window.

## Auto-discovery filters non-Claude model names

With `modelDiscoveryEnabled: true`, Claude Desktop pulls the gateway's model list at launch and **only keeps IDs it can recognizably map to Claude**. Vendor-neutral / non-Claude-named IDs (`stealth/union-alpha`, `nvidia/nemotron-3.5-lightning:free`, `openrouter/free`, Bedrock ARNs, gateway routing aliases) get filtered out of the auto-discovered picker. When discovery is also unstable (4xx / 429 on the list endpoint, or your key is past quota), the app can throw `ModelsNotDiscoveredError` ("Your organization's model list hasn't loaded yet") and the model picker stays stuck on **loading**.

**Recipe for third-party gateway models that are not Claude-named:**

```json
{
  "inferenceProvider": "gateway",
  "inferenceCredentialKind": "static",
  "inferenceGatewayBaseUrl": "https://openrouter.ai/api",
  "inferenceGatewayApiKey": "<raw OpenRouter key, no Bearer prefix>",
  "inferenceGatewayAuthScheme": "bearer",
  "modelDiscoveryEnabled": false,
  "inferenceModels": [
    {"name": "nvidia/nemotron-3.5-lightning:free", "labelOverride": "Nemotron 3.5 Lightning (free)"},
    {"name": "stealth/union-alpha", "labelOverride": "Union Alpha"},
    {"name": "openrouter/free", "labelOverride": "Free Router"}
  ]
}
```

- `modelDiscoveryEnabled: false` + explicit `inferenceModels` is the reliable way to make a non-Claude-named model actually appear and be selectable. Order the list by the model you want as default (first).
- Keep a verified-working free fallback in the list (e.g. `nvidia/nemotron-3.5-lightning:free` or `openrouter/free`) so a rate-limited primary doesn't leave the picker empty.

## OpenRouter 403 vs 429 — do not conflate

| Symptom | Meaning | Action |
|---|---|---|
| `403` `Key limit exceeded (monthly limit)` on a **paid Claude** model (e.g. `anthropic/claude-haiku-4-5`, or whatever discovery/default resolved to) | Your OpenRouter key's rolling monthly spend cap is exhausted; the request would bill a paid model | Switch the default/picker to a verified-200 free model; do NOT rotate keys or change the endpoint. Confirm first which model ID the failing request actually carried. |
| `429` `rate_limit_exceeded` (`... is temporarily rate-limited upstream`) on a **free** model (`stealth/union-alpha` free shared pool, etc.) | Upstream free shared-pool throttling, transient | Retry in a few minutes; keep a different free model as fallback in `inferenceModels`. |

Diagnose before touching config: replay the failing request yourself against `https://openrouter.ai/api/v1/messages` with the exact model ID and your key, and note the status. If 200, the endpoint/auth are fine and the issue is model routing/discovery, not the key. If 403/429, the issue is that specific model's billing/availability, not your base URL.

## Model ID is endpoint-specific — verify the exact endpoint you'll use

OpenRouter's `/api/v1/chat/completions` (OpenAI protocol) returning 200 for a model does **not** prove `/api/v1/messages` (Anthropic protocol) works for that model, and vice versa. Claude Desktop 3P and Claude Code gateway mode speak the **Anthropic Messages** protocol, so probe `POST /v1/messages` directly when verifying, not just `/chat/completions`.

## Pitfalls (from live session)
- **`modelDiscoveryEnabled: true` + a free model that just came back from 429 does NOT auto-recover** — the app caches discovery results and won't re-probe the same model ID on the next turn; a model that 200s in your manual probe can still 403/429 from inside the app if it's mid rate-limit window when the request fires. If a pinned model misbehaves in-app but works in your direct probe, wait out the rate-limit window or move it down the list behind a verified-stable free model.
- **`alwaysStartWithDefaultModel: true`** makes the app open every new session on the first `inferenceModels` entry — put your most-stable free model first, not your aspirational one.
- **Do not set `inferenceModelPricingEnabled: true`** for free/gateway models you don't have negotiated rates for — it's for Anthropic list-price usage estimation only and adds no functionality for OpenRouter free models.
- **The 3P store is per-user and local**: if you later install an MDM/managed policy on the same machine, the managed source wins and the local `configLibrary` file is ignored entirely; don't edit the local file assuming it persists across a managed rollout.
- **Back up the config JSON before hand-editing** (`cp <appliedId>.json <appliedId>.json.bak_<label>`) — the app has no undo for the local config file, and a malformed JSON (dropped comma, wrong value type — remember booleans/arrays stored via MDM/registry are string-encoded, but the local `configLibrary` file is real JSON) makes the whole picker fail to load.

## Free model catalog probes
When the user asks what free models a provider/gateway exposes, fetch the live catalog directly before quoting a list:

- **OpenRouter**: `GET https://openrouter.ai/api/v1/models` with the user's key; filter `pricing.prompt == 0 and pricing.completion == 0` (or ID ends with `:free`). ~24 free entries as of late 2026-09 (NVIDIA Nemotron family, inclusionAI Ling, Poolside Laguna, Qwen, Gemma 4, GLM 5.2, Thinking Machines Inkling, Cohere North, Dots Studio, Nex AGI, plus `openrouter/free` router).
- **NaraRouter** (`https://router.bynara.id/v1`): `GET /v1/models` with the key returns `data[]` with per-1M-IDR price fields; free = `input_idr_per_1m == 0 and output_idr_per_1m == 0` or ID contains `:free`. ~11 free entries as of late 2026-09 (Nemotron 3/3.5 family, Ling 3.0 Flash, MiMo v2.5, Muse Spark 1.3 contributor, Laguna S 2.1, Nex n2.5 Pro).
- Parse the user's credentials catalog (`OneDrive/桌面/apikey.txt`) section-aware: labels and tokens alternate within each `#` section; a naive key/line pairing parser silently drops every entry. Read the whole file and pair label→token by order, not by regex on the token alone.
- Always re-probe the live catalog rather than trusting a previously reported list — free tiers churn (models retired or newly added) and counts go stale within days.
- The same free model ID is often simultaneously offered on multiple gateways (e.g. `nemotron-3.5-lightning:free` on both NaraRouter and OpenRouter); when one gateway's free tier is walled or rate-limited, the sibling gateway's catalog is the fallback path — probe before declaring a model unavailable.

## Verification
- After relaunch, open **Help → Troubleshooting → Generate Diagnostic Report → Export to file**; check `provider-status.txt` (provider settings complete/valid) and `deployment-mode.txt` (running in third-party mode) in the zip.
- Confirm the model picker shows your pinned `inferenceModels` list (not an empty/loading state) before declaring the 3P wiring done.
