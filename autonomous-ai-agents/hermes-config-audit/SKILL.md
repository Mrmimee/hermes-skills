---
name: hermes-config-audit
description: "Audit and prune Hermes local plugins and MCP servers."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, config, audit, plugins, mcp, lightweight]
---

# Hermes Config Audit & Pruning

Audit active Hermes plugins and MCP servers, and prune redundant or high-overhead integrations to maintain a lightweight, zero-resident deployment profile.

## When to Use
- User wants to review enabled plugins or MCP servers
- User requests a lightweight/zero-resident configuration audit
- Pruning excessive MCP tool bloat (e.g., >20 tools from one provider)
- Adding low-overhead zero-resident utility plugins (e.g., `disk-cleanup`, `security-guidance`)

## Prerequisites
- `hermes` CLI is available in terminal
- `$HERMES_HOME` contains `config.yaml`
- No active blocking tasks that require the current exact toolset mid-conversation

## Procedure

1. **Snapshot active MCP servers.**
   Run `hermes mcp list` to display all configured remote/stdio MCP servers and their tool counts.
2. **Snapshot active and available plugins.**
   Run `hermes plugins list` for a non-interactive snapshot and check which ones are toggled on. Reserve bare `hermes plugins` for interactive toggling only — it prompts for input and blocks automation.
3. **Inspect `config.yaml` toolsets and plugin state.**
   Read `config.yaml` under `$HERMES_HOME` to review `plugins.enabled` and `mcp_servers`.
4. **Evaluate for bloat and redundancy.**
   - Identify MCP servers that expose very large toolsets (e.g., 48+ tools like Copilot GitHub) which may bloat the model's prompt or tool selection attention.
   - Identify low-utility remote API servers (e.g., Cloudflare API) that are rarely used but registered.
   - Check if any local `uvx` or `npx` stdio servers are running in the background (avoid these if the user prefers zero-resident). All remote HTTP MCPs are stateless on Hermes's side and highly recommended.
5. **Apply Pruning via CLI.**
   - Remove redundant or unwanted MCP servers:
     ```bash
     hermes mcp remove <server_name>
     ```
6. **Apply Configuration updates via CLI.**
   - Update enabled plugins:
     ```bash
     hermes config set plugins.enabled "['web/tavily', 'disk-cleanup', 'security-guidance']"
     ```
   - Update reasoning display toggle:
     ```bash
     hermes config set display.show_reasoning false
     ```
7. **Install lightweight remote MCPs from catalog if needed.**
   ```bash
   hermes mcp install <catalog_name>
   ```
   (e.g., `deepwiki`, `hugging_face`, `microsoft-learn` — these are remote and do not spawn local resident processes on the client machine).

## Full self-check

When the user asks for a full self-check, run in order: `hermes doctor` (baseline, allow a long timeout), `hermes portal info` plus `hermes config get model.provider` (which provider actually serves inference), the `platforms` block of `gateway_state.json` under `$HERMES_HOME` (telegram/discord/qqbot connection state), `hermes mcp list` + `hermes plugins list` + `hermes plugins compat`, `hermes cron list`, then tail `logs/gateway.log` for transport reconnects. Report what changed, what is verified, and what is left — never a replay of the process.

## Pitfalls
- **Never hand-edit `config.yaml`** to add/remove `mcp_servers` or `plugins.enabled` arrays manually — use `hermes mcp remove` or `hermes config set` to ensure proper JSON/YAML array serialization and clean up of OAuth tokens.
- **MCP tool bloat slows down model routing** — if a single MCP injects >40 tools, consider removing it and relying on built-in `terminal` / `search_files` / `web_search` instead.
- **Remote HTTP MCPs are not resident** — do not confuse remote URL-based MCPs with `command`-based (stdio) MCPs; remote ones leave no local process footprint.
- New or removed MCPs only load after the current session is reset or a new Hermes process is started (`/reset` or `hermes mcp reload`).
- **Never run interactive pickers in an agent session** — bare `hermes tools`, bare `hermes plugins`, and `hermes mcp picker` all block on TTY input and hang until timeout; use non-interactive variants (`hermes plugins list`, `hermes mcp list`, `hermes tools enable/disable NAME`, `hermes config get/set`) instead.
- **Verify browser backend from runtime state, not the config write** — a cloud selection such as `browser.cloud_provider: nous` only takes effect when `hermes portal tools` shows the Tool Gateway entitled; a clean config write with `not entitled` still routes locally, so check entitlement before declaring cloud browser done.
- **Surface paid/entitlement gates before switching backends** — when the preferred path needs a subscription or quota, say so first and offer the free fallback; never switch config and discover the gate afterward.
- **A BLOCKED hub-install scan is final without user approval** — report the verdict and its findings, then stop; re-run with `--force` only when the user explicitly approves after seeing them.
- **Gateway messaging adapters are plugins, not MCP servers** — a connected Telegram/Discord/QQBot session means its `-platform` adapter is already running; catalog search on the platform name returns unrelated plugins, so confirm the installed adapter with `hermes plugins list` and `gateway_state.json` before installing anything.

## External capability-layer tools

Non-plugin CLIs (isolated venv, safe-mode installs) live outside the plugin/MCP flow above — see `references/external-capability-tools.md` for the procedure.

## Hub skill installs

`hermes skills` hub installs follow their own check-first flow — see `references/hub-skill-install.md` for the procedure.
