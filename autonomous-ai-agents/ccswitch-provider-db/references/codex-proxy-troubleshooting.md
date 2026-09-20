# Codex / CC Switch local proxy — request-failure diagnostics

For 4xx/5xx errors when Codex (or Claude Desktop) talks to a third-party upstream through CC Switch's local proxy (default `http://127.0.0.1:15721/v1`). Goal: separate proxy-health, upstream-health, and payload-incompatibility failures before touching any provider card.

## Log locations (read these first, cheapest signal)

| What | Where |
|---|---|
| Codex per-turn outcome incl. full upstream error text | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (live) and `~/.codex/archived_sessions/rollout-*.jsonl`. `task_complete` events carry the error as a **nested JSON string** — decode it once; the inner `cause:` field holds the real upstream error. |
| Which upstream each request actually hit | `~/.cc-switch/logs/cc-switch.log` — lines like `[Codex] >>> 请求目标: <url> (model=<id>)`. Confirms whether the active provider matches your assumption. |
| Active provider selection | `~/.cc-switch/settings.json` → `currentProviderCodex` / `currentProviderClaudeDesktop` (UUID → look up the name in the `providers` table). |
| Live proxy health | `curl -s -o NUL -w "%{http_code}" http://127.0.0.1:15721/v1/models` — a 200 proves the proxy and the key path work, before blaming the model. |

## Isolation ladder (each step is a separate failure class)

1. **Proxy up?** `GET /v1/models` on the proxy. Dead proxy → restart CC Switch; log shows the forwarder lines, so confirm which provider is actually being hit.
2. **Baseline no-tools request?** `POST /responses` with `{"model": <active-model>, "input": "reply with just the word OK", "stream": false, "max_output_tokens": 20}` and **no `tools` field**. 200 → proxy + upstream + key all healthy; the failure is payload-specific.
3. **Tool-variant isolation?** Same request, one `tools` entry per probe, three variants: `"type": "function"` (normal function), `"type": "namespace"` (Codex's MCP packaging), `"type": "mcp"`. Record which variant 400s. An upstream that rejects `namespace`/`mcp` but accepts `function` means the model works for plain chat; only Codex's bundled-tool sessions fail.

## Known incompatibility: `namespace` tools

Codex desktop's bundled plugins (`computer-use`, `unified-computer-use`, `browser` in `~/.codex/config.toml` under `[plugins."...@openai-bundled"]`) package their MCP tools as Responses-API `type: "namespace"` entries. Most third-party upstreams behind the proxy (free aggregators, vendor gateways) only implement `function`, and reject the request with `unknown variant 'namespace'` / `unsupported tool type`. The `node_repl` MCP server can also contribute tools.

**Fix (disable the namespace emitters):**

```toml
# ~/.codex/config.toml — back up before editing (cp config.toml config.toml.bak-<ts>)
[plugins."browser@openai-bundled"]
enabled = false

[plugins."unified-computer-use@openai-bundled"]
enabled = false

[plugins."computer-use@openai-bundled"]
enabled = false
```

Document-type plugins (`documents`, `pdf`, `spreadsheets`, `presentations`, `template-creator`) emit plain `function` tools — leave them enabled. Codex must be **restarted** for config.toml changes to take effect. CC Switch proxy restart is NOT needed for this fix. Verify by sending a short message in Codex; a new `task_complete` without `error` confirms it.

Pitfall: disabling these plugins removes Codex's computer-use/browser capability — trade-off the user must accept while on those upstreams; a fully Responses-native upstream (official OpenAI) is the only path that keeps them.

## Craft pitfalls (these cost real time)

- **Never put non-ASCII literals in curl `-d` payloads on this host** — MSYS git-bash mangles Chinese text in inline `-d`, and the proxy then returns a 500 `invalid unicode code point` that looks like a proxy fault. Write the request body to a pure-ASCII JSON file (`printf '%s' '...' > file`) and use `curl --data @file`.
- **Write scratch files to `%LOCALAPPDATA%/Temp`, not `/tmp`** — native Windows tools (curl, node, python .exe) cannot read MSYS `/tmp`; use `$LOCALAPPDATA/Temp` so both bash and native tools share the path.
- **Do not trust `~/.codex/logs/` for this** — Codex's operational detail lives in the SQLite `logs_2.sqlite` (hard to read fast); the rollout JSONL in `sessions/` and `archived_sessions/` is the human-readable record and contains the full upstream error inside `task_complete.payload.error.message` (double-encoded JSON — `json.loads` it twice, or regex the inner `cause:` text).
- **Confirm which provider is live before diagnosing** — `settings.json`'s `currentProviderCodex` is the UUID; the CC Switch log's `请求目标` lines are the ground truth of what URL each request hit. Mismatch between the two is itself the bug.
