---
name: hermes-credentials-setup
description: "Use when configuring Hermes API keys and credentials."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, credentials, apikey, env, configuration]
---

# Hermes Credentials Setup

Workflow for locating, parsing, evaluating, and applying user-supplied API keys and service tokens to Hermes.

## Procedure

1. **Locate the source credential file**:
   - Check standard user locations. On Windows, OneDrive Known Folder Move frequently relocates the desktop: check `~/Desktop`, `~/OneDrive/Desktop`, and localized paths like `~/OneDrive/桌面`.
   - Verify file existence before guessing or falling back to empty templates.

2. **Securely parse and catalog keys**:
   - Never print unmasked secrets into chat transcripts, stdout, or logs.
   - Extract key names, service identifiers, and masked prefixes/suffixes (`sk-...1234`).
   - Group the discovered keys by functionality:
     - **Web Search & Extraction**: `EXA_API_KEY`, `FIRECRAWL_API_KEY`, `TAVILY_API_KEY`
     - **Media & Voice (STT/TTS)**: `FAL_KEY` (image/video gen), `GROQ_API_KEY` (Whisper STT), `VOICE_TOOLS_OPENAI_KEY`
     - **Model Providers**: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `NVIDIA_API_KEY`, `NOUS_API_KEY`, `HF_TOKEN`, `OPENCODE_ZEN_API_KEY`
     - **Developer Tools**: `GITHUB_TOKEN` (Skills Hub & gh CLI rate limits)
     - **Messaging Gateways**: `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, QQ Bot AppID/Secret
     - **Local Integrations**: Obsidian Local REST API, Maps API keys

3. **Present an actionable numbered review list**:
   - When the user asks what to configure, list the keys they *actually possess* from the file, not generic empty placeholders.
   - For each item, state the key name, masked value preview, and a concise explanation of what capability it unlocks and how it makes workflows more convenient.
   - Provide clear selection options (e.g. "All recommended", or choose by number).

4. **Write confirmed credentials to Hermes**:
   - Target `$HERMES_HOME/.env` (defaults to `~/.hermes/.env` or `%LOCALAPPDATA%/hermes/.env`).
   - Maintain the hard invariant: secrets belong in `.env`, settings in `config.yaml`.
   - Update existing lines or append idempotently without duplicating environment variables.
   - On Windows, ensure any file paths written to `.env` use forward slashes (`/`).

5. **Verify activation**:
   - Check that the active `.env` loads the newly added variables.
   - Run `hermes doctor` or inspect provider availability where applicable.

6. **Messaging Gateway verification & activation**:

## Model-Chain & Custom-Provider Pitfalls

When wiring a primary + fallback chain in `config.yaml`, verify each node BEFORE writing config, because a node that cannot resolve only surfaces at request time:

- **`hermes fallback add` is an interactive picker** with no flags — it will hang the terminal. To write a fallback chain programmatically, edit `config.yaml` (via `hermes config set` or a script that loads/saves `load_config`/`save_config`), never block on the interactive picker.
- **Custom provider names go in the `providers:` dict (new style)**, not `custom_providers` (legacy). A fallback entry's `provider` field can reference a named `providers:` entry, and the entry's `base_url`/`key_env`/`api_mode` fields are honored by the fallback resolver.
- **`resolve_provider_client` / provider resolution reads env vars via `agent.secret_scope.get_secret`, and the running gateway's env is loaded from `.env` at startup.** To dry-test whether a provider actually resolves, load `.env` with `python-dotenv` first (`dotenv.load_dotenv($HERMES_HOME/.env)`) — a bare process without the env will report "Vertex AI credentials not found" even when `.env` is correct. This is the single most confusing failure mode when verifying chains.
- **A `mcp_servers` remote HTTP entry needs the `mcp` Python package with streamable-HTTP support installed** (`mcp` v2.x has it). Verify with `importlib.metadata.version('mcp')`.
- **Secret-bearing remote MCP servers (e.g. `https://api.githubcopilot.com/mcp/`) authenticate via `headers: Authorization: Bearer <PAT>`** — read the PAT from the credentials file, never inline it in chat. The `github_pat_` prefix PAT works as a Bearer against the Copilot MCP endpoint.
- **Enable a plugin that reads a key (e.g. `web-tavily`)** with `hermes plugins enable web/tavily` and append the key to `.env` (`TAVILY_API_KEY`). "Takes effect on next session" is the expected confirmation, not an error.
- **Never hand-type the full `.env` / `config.yaml` content into a reply or transcript** — quote only masked prefixes (first ~4–8 chars) per the standing pitfall.

### Key env-var ↔ provider pairing quick reference (this machine)

| Config key / provider id | `.env` variable | Notes |
|---|---|---|
| `opencode-free` (keyless free tier) | *(none — anonymous)* | `https://opencode.ai/zen/v1`, empty `Authorization`. Contributor-tier models (`*-contributor-free`) trigger a data-training confirm; set `security.allow_data_training_tiers_noninteractive: true` for unattended runs, else `-z` probes are refused. |
| `vertex` | `VERTEX_CREDENTIALS_PATH` + `VERTEX_PROJECT_ID` + `VERTEX_REGION` | Service-account JSON resolved at startup; verify by loading `.env` before probing. |
| `agnes-ai` (custom provider) | `AGNES_API_KEY` | `base_url: https://apihub.agnes-ai.com/v1`, model `agnes-3.0-flash` (512K ctx, free tier). |
| `opencode-zen` | `OPENCODE_ZEN_API_KEY` | Paid/credited tier; free models without `-contributor` here report `CreditsError: No payment method` — use the keyless `opencode-free` id instead. |
| GitHub Copilot MCP | `GITHUB_TOKEN` (PAT `github_pat_`) | Used as Bearer for `mcp_servers.github.headers`, not an env-var provider. |
| `web-tavily` plugin | `TAVILY_API_KEY` | Enable plugin + key; takes effect next session. |

## Pitfalls

- On Windows 11 with OneDrive sync enabled, `ls ~/Desktop` fails with `No such file or directory`; always inspect `~/OneDrive/` for `Desktop` or `桌面`.
- Never show full secrets in replies or output when quoting user files.
- When the user refers to a local file (e.g. "桌面apikey"), read and match their actual keys first rather than listing Hermes' generic unfilled template.
- When a credential file lists tokens for multiple different agents (e.g. Antigravity, Openclaw, Claude Code alongside Hermes), do not send one-off test messages from non-Hermes tokens; configure and activate only the Hermes-specific bots unless explicitly requested.
- Before running `hermes send` for Telegram or Discord, ensure `python-telegram-bot` and `discord.py` are installed in Hermes's venv; they are optional dependencies not bundled in base installs.
- Telegram bots cannot send proactive messages to users who haven't started a chat; inspect `getUpdates` to resolve the user's `chat.id` rather than guessing.
- Discord bots connect successfully to the gateway but silently ignore all incoming user messages unless an allowlist is configured; set `DISCORD_ALLOW_ALL_USERS=true` or list allowed channel IDs in `DISCORD_ALLOWED_CHANNELS`.
- Tencent QQ Bot endpoint `https://bots.qq.com/app/getAppAccessToken` returning code `100016: invalid appid or secret` means the secret was reset, expired, or belongs to a different QQ portal; switch to the QR code binding flow (`_create_bind_task` in `gateway.platforms.qqbot.onboard`) which lets the user authorize directly from mobile QQ.
- When reverting or cleaning up applied credentials on user request, always retain the backup `.env.bak` file rather than deleting it immediately, so an accidental rollback command can be reversed without re-authenticating.
- When creating temporary background poller scripts for asynchronous OAuth/QR binding tasks, write clean standalone `.py` script files with verified syntax and error handling rather than fragile multi-line shell heredocs.
- On Windows, a background process displaying as "Bun" in Task Manager is frequently Cline's backend sidecar (`C:\Users\<user>\AppData\Local\Cline\code-sidecar.exe`), which is compiled with the Bun runtime.
