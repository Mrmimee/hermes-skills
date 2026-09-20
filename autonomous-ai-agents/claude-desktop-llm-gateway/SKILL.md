---
name: claude-desktop-llm-gateway
description: "Configure Claude Desktop's Developer-menu third-party LLM gateway routing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [claude-desktop, gateway, openrouter, third-party-inference, config]
    related_skills: [hermes-model-chain-wiring, obsidian]
---

# Claude Desktop Third-Party LLM Gateway

Configure Claude Desktop to route inference through a third-party gateway using the app's Developer menu. Use when the user wants Claude Desktop or Cowork to use a non-Anthropic provider without CC Switch or CLI env vars.

## UI localization / 汉化

Localizing the Claude Desktop UI is a separate concern with its own procedure and crash-prone traps: `references/zh-localization.md`.

## When to Use

- "Point Claude Desktop at OpenRouter / a LiteLLM gateway / a custom Anthropic-compatible endpoint."
- "Enable Developer Mode in Claude Desktop and configure third-party inference."
- "Make Claude Desktop use model X without a Claude subscription."

Do not use for CLI-only routing (`ANTHROPIC_BASE_URL` in shell or `~/.claude/settings.json`); that is a different surface and does not configure the Desktop app. Also not for CC-Managed proxy mode: when Claude Desktop runs behind CC Switch (`claudeDesktopMode = "proxy"`, env keys `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`), the model routing lives in CC Switch's DB (`meta.claudeDesktopModelRoutes`), not in the in-app config — see the `ccswitch-provider-db` skill.

## Procedure

### 1. Enable Developer Mode

Open Claude Desktop, then:

`Help` → `Troubleshooting` → `Enable Developer Mode`

The app may restart. After restart, a new `Developer` menu appears.

### 2. Open Third-Party Inference Config

`Developer` → `Configure Third-Party Inference…`

This opens the in-app configuration window. Fill the `Connection` section first.

### 3. Set Connection Fields

For an OpenRouter gateway:

| Form field | Value |
| --- | --- |
| Inference provider | `Gateway` |
| Gateway base URL | `https://openrouter.ai/api` |
| Credential kind | `Static API key` |
| Gateway API key | OpenRouter key (paste from the user's existing `apikey.txt`; do not echo it in chat) |
| Gateway auth scheme | `Bearer` |

For other gateways, use the vendor's documented base URL. The key must already be available on the user's machine; never type a key into chat.

### 4. Configure Models

Auto-discovery only shows model IDs it recognizes as Claude. For non-Claude aliases (e.g. `stealth/union-alpha`), explicitly set the model list (`inferenceModels`):

- A plain string is valid: `["stealth/union-alpha"]`.
- Object form is valid when you need a label or extra fields: `[{"name":"stealth/union-alpha","labelOverride":"Union Alpha"}]`.
- The first entry is the default model.
- Do not set `supports1m` unless the deployment actually accepts 1M-token requests.

### 5. Save and Restart

Click `Apply Changes`, then click `Save & Restart`. The app relaunches; the sign-in screen should now offer the third-party mode.

### 6. Verify

- Open a new conversation and confirm the selected model is the expected ID.
- If the picker is empty, check that `inferenceModels` is set explicitly (auto-discovery filtered out the non-Claude ID).
- If requests fail, check the diagnostic report: `Help` → `Troubleshooting` → `Generate Diagnostic Report` → `Export to file`, then inspect `managed-config.txt` and `provider-status.txt`.
- 401 → wrong key or Bearer scheme; 404 → wrong base URL or path; 400 → model ID not accepted by the gateway.

## Pitfalls

- **Desktop app ignores CLI env vars** — `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and `settings.json` env blocks configure the CLI/VS Code surfaces, not Claude Desktop. The Desktop app reads only the in-app third-party inference configuration (or MDM/registry policy).
- **UI localization: MSIX (Store) install is the blocker, not the patch** — `C:\Program Files\WindowsApps` 沙箱锁死写入（UAC/icacls 都白搭）；先 `Get-AppxPackage -Name Claude` 判安装形态，MSIX 先卸掉换 Squirrel 用户级 EXE（`%LOCALAPPDATA%\AnthropicClaude`）或 MSI 再汉化。详见 `references/zh-localization.md`。
- **Do not mix `/v1` into the base URL** — OpenRouter's base URL is `https://openrouter.ai/api`; the Messages endpoint is then `/v1/messages`. Do not enter `.../api/v1` or `.../chat/completions` in the base-URL field.
- **`supports1m` is per route, not per gateway** — in both the in-app config and CC Switch `claudeDesktopModelRoutes`, set it only on routes whose target model actually accepts 1M-token requests; a route mapped to a 200K-capped model without the flag will silently run in short-context mode.
- **Auto-discovery hides non-Claude models** — model IDs like `stealth/union-alpha` will not appear in the picker unless `inferenceModels` lists them explicitly.
- **Free pricing on a gateway is not guaranteed compatibility** — a 200 from a Chat Completions endpoint proves only that the gateway's chat path works; Claude Desktop speaks the Anthropic Messages API, so streaming and tool-use support must still be verified in the app.
- **Do not echo API keys in chat** — pull the key from the user's local credential catalog (`apikey.txt` on desktop) and reference it in the config file or paste field, not in the conversation.
- **A 3P gateway configuration makes Claude Desktop local-only** — with a gateway active, SSH sessions, Anthropic-hosted cloud sessions, and Remote Control are unavailable.

## References

- Claude Desktop in-app configuration: https://claude.com/docs/third-party/claude-desktop/in-app-configuration
- Claude Desktop gateway deployment: https://claude.com/docs/third-party/claude-desktop/gateway
- Configuration reference (all keys): https://claude.com/docs/third-party/claude-desktop/configuration
- OpenRouter base URL / auth: https://openrouter.ai/docs/guides/guides/claude-code-integration
