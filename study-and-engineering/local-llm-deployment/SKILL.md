---
name: local-llm-deployment
description: "Use when deploying or running local LLMs on user hardware."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [LLM, llama.cpp, GGUF, Quantization, CUDA, LocalDeployment]
---

# Local LLM Deployment

Guidelines and procedures for deploying, sizing, and running local language models (GGUF, llama.cpp, on-device runtimes) on user-constrained hardware.

## 1. Hardware Sizing & Quantization Selection

Always inspect available system resources before recommending or downloading models:
- **GPU & VRAM**: Run `nvidia-smi` to check total VRAM, currently occupied VRAM, and driver CUDA capability.
- **System RAM**: Check total and available RAM.

### Sizing Heuristics
- **4GB VRAM (e.g. RTX 3050 Laptop)**:
  - Optimal model size: 1B to 3B parameters (e.g., MiniCPM5-2B, Qwen2.5-3B).
  - Quantization: **Q4_K_M** is the gold standard (~1.5 GB file size). At 4K context length, weights + KV cache consume ~1.9 GB VRAM, fitting 100% inside GPU with `-ngl 99`.
  - **Rule**: Avoid aggressive sub-4-bit quantizations (Q2_K, Q3_K) on models <= 3B parameters — parameter density is high and degradation in reasoning and coherence is disproportionately severe compared to the minor VRAM savings.
- **6GB - 8GB VRAM**: 7B to 8B models with Q4_K_M.
- **Zero-idle footprint**: Prefer standalone binaries (`llama.cpp`) over daemonized background services when the user needs zero background RAM/VRAM consumption when not in use.

## 2. Model & Binary Acquisition

### Handling Restricted Regional Networks
In environments where direct GitHub release downloads drop or reset connections (`objects.githubusercontent.com` TLS handshake failures):
1. **GitHub Release Accelerators**: Use tested mirrors such as `https://ghfast.top/https://github.com/...` for binaries and release archives.
2. **ModelScope for GGUF Weights**: For domestic/China networks, download GGUF files directly from ModelScope (`https://www.modelscope.cn/api/v1/models/<repo>/repo?Revision=master&FilePath=<file>`) for high sustained throughput without proxies.

### Hugging Face Authentication (gated models / downloads)
- The CLI is `hf`; `huggingface-cli` is deprecated and only prints a redirect hint.
- Login non-interactively from the stored token: `hf auth login --token "$TOKEN"`; verify with `hf auth whoami` and `hf auth list` before downloading.
- Public weights need no login; gated repos additionally require web access approval on the model page first — a valid login alone still 403s without it.

### llama.cpp Windows CUDA Packaging
Windows CUDA releases of llama.cpp require two components unzipped into the same directory:
1. `llama-<tag>-bin-win-cuda-<ver>-x64.zip` (Core executables: `llama-cli.exe`, `llama-server.exe`)
2. `cudart-llama-bin-win-cuda-<ver>-x64.zip` (CUDA runtime libraries: `cudart64_*.dll`, `cublas64_*.dll`)

## 3. Execution & Flag Discipline

### CLI Interactive vs Non-Interactive Pitfall
- Modern `llama-cli.exe` builds default to conversation mode and block indefinitely on `stdin`.
- When running automated health checks, test prompts, or scripted completions, **always pass `-st` (`--single-turn`)** to force immediate exit upon response completion.

### Server Flags for Low-Memory Hardware
```bash
llama-server.exe -m "<model.gguf>" -ngl 99 -c 4096 -fa on --host 127.0.0.1 --port 8080
```
- `-ngl 99`: Offload all transformer layers into GPU VRAM, leaving host RAM completely unburdened.
- `-c 4096`: Restrict context length to budget KV cache memory predictably.
- `-fa on`: Enable Flash Attention (`on`, `off`, `auto`). Never pass a bare `-fa` flag without an argument; in newer llama.cpp builds (`b10976+`), a bare `-fa` before `--host` causes the parser to treat `--host` as the argument to `-fa`, failing immediately with `unknown value for --flash-attn: '--host'`.

## 4. Windows Desktop Integration

### OneDrive Desktop Path Resolution
Never assume the desktop path is `C:\Users\<user>\Desktop`. On machines with OneDrive folder backup active, the desktop is redirected to `C:\Users\<user>\OneDrive\Desktop` or localized names (e.g. `C:\Users\<user>\OneDrive\桌面`).
- Query the registry to resolve the canonical path reliably:
  ```python
  import winreg
  key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
  desktop_path, _ = winreg.QueryValueEx(key, "Desktop")
  ```

### Launcher & Shortcut Generation
1. Write a clean `.bat` script that starts `http://127.0.0.1:8080` in the default browser and runs `llama-server.exe`. Use `cd /d "%~dp0"` in the batch script so it reliably executes from its own directory regardless of how it was launched.
2. Generate or extract a multi-resolution `.ico` file (256x256 down to 16x16).
3. Use PowerShell and `WScript.Shell` to create a `.lnk` shortcut pointing to the batch script with the working directory and icon configured.
4. **Script escaping in Windows bash**: When generating Windows scripts via Python from a bash terminal, use forward slashes for all paths (`C:/Users/...`) across file writing, path joining, and string interpolation. Even inside triple-quoted raw strings (`r"""..."""`), backslashes followed by `\U` or `\u` trigger syntax errors in Python string compilation.

## 5. Integrating with Coding Agents (OpenCode)

When local LLM inference should be exposed to client coding tools like OpenCode (`~/.config/opencode/opencode.json`):
- Configure as an OpenAI-compatible endpoint:
  ```json
  "llama": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "Local Llama (MiniCPM5)",
    "options": {
      "baseURL": "http://127.0.0.1:8080/v1",
      "apiKey": "none"
    },
    "models": {
      "MiniCPM5-2B": {
        "name": "MiniCPM5-2B (Local)",
        "reasoning": true,
        "interleaved": { "field": "reasoning_content" },
        "limit": { "context": 4096, "output": 2048 }
      }
    }
  }
  ```
- Models that produce thinking tokens need `reasoning: true` and `interleaved.field: "reasoning_content"` to stream chain-of-thought correctly.

## 6. Project & Vault Alignment

Before picking arbitrary deployment paths (like `Downloads/` or `AppData/`), search the user's workspace and knowledge base (e.g. Obsidian Vault `运维速查/` or `AGENTS.md`) for established deployment paths:
- If a standardized location exists (e.g. `C:\Users\<user>\LocalLLM\<Model>\`), conform to it directly to avoid duplicate downloads, broken downstream scripts, and disorganized filesystems.
- **Preserve functional breakthroughs over historical stubs**: When aligning with documentation, adopt the documented directory locations and launcher names, but never downgrade functioning runtime advancements (such as full CUDA acceleration, working flags, or newer binary features) to mirror obsolete limitations recorded in older notes. Keep the optimal execution while matching the expected file locations.
