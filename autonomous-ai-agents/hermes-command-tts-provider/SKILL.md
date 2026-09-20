---
name: hermes-command-tts-provider
description: "Add command-type TTS/STT providers to Hermes config."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, tts, stt, command-provider, voice, configuration]
    related_skills: [hermes-agent, hermes-model-chain-wiring]
---

# Command-Type TTS/STT Provider for Hermes

Hermes has no built-in provider for every audio vendor. The escape hatch is a **command-type provider** under `tts.providers.<name>` (STT: `stt.providers.<name>`): a shell command that reads the text and writes the audio file, wired into config so `text_to_speech` / transcription tools dispatch to it.

## When to Use

- The requested TTS/STT vendor is not in the built-in catalog (`edge/elevenlabs/openai/gemini/mistral/minimax/xai/neutts/piper/kittentts/deepinfra`), or is free only via a third-party endpoint.
- The vendor's API is not OpenAI-audio-compatible or needs custom headers/UA.
- Don't use when a built-in provider or an OpenAI-compatible base_url override covers the vendor — use `references/providers-and-models.md` from the hermes-agent skill instead.

## Step 0 — Probe the upstream API first (before touching config)

- Verify model availability and rate-limit headers with a real request from the venv python (NOT the system python).
- Read response headers `x-ratelimit-*` to learn the real per-org caps (RPM/TPM); the doc table is only a summary.
- Some third-party-hosted models (e.g. `canopylabs/orpheus-*` on Groq) return `400 model_terms_required` until the account admin accepts the model terms in the provider's console — the terms page usually has no visible checkbox; opening the model's playground page triggers the acceptance flow.
- Some CloudFlared endpoints reject the default python `User-Agent` with `error code: 1010` (browser-like UA required) even though auth works.

## Step 1 — Write the helper script

Place it in `$HERMES_HOME/` (non-OneDrive, non-synced). Contract:
- Args (positional, in this order): `{input_path} {output_path} [voice] [model]`.
- Read the text from `input_path` (UTF-8), call the API, write audio to `output_path`.
- **Honor the requested output container**: Hermes passes the FINAL delivery path — `.ogg` on voice-bubble platforms, `.mp3` elsewhere, `.wav` if `output_ext: .wav`. If the upstream only returns WAV, convert via ffmpeg; when ffmpeg is absent, write the WAV bytes to the requested path and let Hermes's format sniffer fall back. (`produced no output at <path>` after a 200 almost always means bytes landed in the wrong container.)
- **Secret reachability is two-layer**: Hermes runs command providers with a scrubbed env; `env_passthrough` in config copies only vars that already exist in the parent process. Make the script fall back to reading `$HERMES_HOME/.env` when the env var is empty — this makes it testable standalone AND robust in-process (the gateway parent has the `.env` values in its env; a bare subprocess does not).
- Cap input text to the API limit (Orpheus: 200 chars); Hermes pre-chunks long text via `max_text_length`.
- Never accept the key on argv; read from env / `.env` only.

## Step 2 — Wire config.yaml (the shape that breaks most often)

The provider is declared as ONE rendered command string, not `command`+`args`:

```yaml
tts:
  provider: groq-tts
  groq-tts:
    command: 'C:/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe "C:/Users/<user>/AppData/Local/hermes/groq-tts.py" {input_path} {output_path} {voice} {model}'
    timeout: 60
    output_ext: .wav
    supports_streaming: false
    supports_instructions: false
    voice_compatible: true    # opt in to native voice-bubble delivery
    max_text_length: 180
    env_passthrough:
      - GROQ_API_KEY
```

Placeholders Hermes renders (quote-aware, single or `{{double}}` braces): `{input_path} {text_path} {output_path} {format} {voice} {model} {speed}`. There is no `args:` list — a list of placeholders is not parsed; everything rides in the `command` string.

Write the block via Python `load_config()`/`save_config()` (or careful text surgery). Then re-read and print the parsed `command` to confirm the placeholders survived.

## Pitfalls

- **`{placeholder}` tokens are not valid YAML scalars.** `hermes config set tts.x '{input_path}'` parses the braces as a mapping and writes `input_path: null` (corrupting the block). After ANY `hermes config set` touching placeholder values, verify with `python -c "import yaml; ..."` and repair by direct text edit if needed. The same trap hit `voice_compatible_keys: ['groq']` — use the scalar `voice_compatible: true` instead (the code reads `voice_compatible`, not `voice_compatible_keys`).
- **Do not hand-edit config.yaml with `write_file`/`patch`** — Hermes refuses agent writes to its own config file; route through `hermes config set` or the `load_config()`/`save_config()` Python API.
- **Config key validation warnings are fine**: `hermes config set` on unrecognized `tts.<provider>.<key>` keys prints "not a recognized config key — saved anyway"; command-provider keys are valid, just not in the CLI's schema hint.
- **Test the helper script standalone first** (env key set, all three containers: mp3/ogg/wav), then test through Hermes.
- **`hermes doctor`'s vendor `⚠ (HTTP 403)` is the audio probe's default User-Agent hitting Cloudflare, not a rejected key** — the same run's API Connectivity section is the authoritative signal; confirm with a browser-UA request before touching credentials.

## Step 3 — Verify end-to-end through the Hermes tool, not just the script

```python
import sys; sys.path.insert(0, '<HERMES_INSTALL>/hermes-agent')
from tools.tts_tool import text_to_speech_tool
r = text_to_speech_tool(text='test', provider='<your-provider>',
                        output_path='C:/.../Temp/x.mp3')
print(r)   # expect success:true, .ogg on desktop voice-bubble delivery
```

A failure envelope like `exited with code 1: stderr: <KEY> not set` means the key didn't reach the child → check `env_passthrough` + the script's `.env` fallback. `produced no output at <path>` → container mismatch (Step 1 note).

STT is the same mechanism (`stt.providers.<name>`, same placeholder + env_passthrough plumbing) — only the endpoint and output direction differ.

## STT Troubleshooting Quick Notes (Windows Native)

- **Local STT fallback is unreliable for Chinese**: without an explicit `stt.provider`, Hermes auto-detects `local` (faster-whisper) first. On Windows, CUDA runtime libraries (`cublas64_12.dll`) are frequently missing, causing silent CPU int8 degradation with poor Mandarin accuracy. For Chinese content, always set `stt.provider: groq` explicitly via `hermes config set stt.provider groq`.
- **Verifying STT provider resolution**: run `python -c "from tools.transcription_tools import transcribe_audio; r = transcribe_audio('audio.ogg'); print(r['provider'], r['transcript'])"` from the Hermes source directory. The `provider` field in the result confirms which backend was actually used (local vs. groq vs. openai).
- **Groq STT is free and fast**: `whisper-large-v3-turbo` via Groq handles Chinese accurately with sub-second latency and zero local VRAM cost — strongly preferred over local base/small models for this user's environment.

## Groq Orpheus specifics (as of wiring time)

- Model `canopylabs/orpheus-v1-english`; voices: troy, autumn, hannah, austin, daniel, diana; endpoint `https://api.groq.com/openai/v1/audio/speech`; `GROQ_API_KEY`.
- Free-tier caps: RPM 10 / RPD 100 / TPM 1.2K / TPD 3.6K (audio) — plenty for chat TTS.
- Model availability changes: `qwen/qwen3.8-27b` was in the 13-model list; re-probe `/openai/v1/models` rather than trusting the list.
- Groq STT: `stt.provider: groq` with whisper-large-v3-turbo; ~500 tok/s generation observed on qwen3.8-27b under an 8000 TPM org cap.
