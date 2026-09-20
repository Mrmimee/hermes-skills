---
name: vertex-provider-setup
description: "Use when wiring Vertex AI credentials into Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, vertex, gcp, providers, credentials]
---

# Vertex Provider Setup (Hermes)

Wire a Google Cloud service-account JSON into the Hermes `vertex` provider so
`agent/vertex_adapter.py` can mint OAuth2 tokens for the OpenAI-compatible endpoint.

## Procedure

1. Copy the SA JSON to a stable path under `$HERMES_HOME` (e.g.
   `$HERMES_HOME/vertex-sa-<project>.json`). Never leave the only usable copy
   under a synced or non-ASCII path — sync churn and unicode paths break SDK
   file reads at auth time.
2. Set identity settings through the CLI, never by hand-editing config.yaml:
   `hermes config set vertex.project_id <id>` and
   `hermes config set vertex.region global`. A stray indent corrupts the file
   and breaks the live gateway.
3. Append credential pointers to `$HERMES_HOME/.env` (secrets live in `.env`,
   settings in `config.yaml`): `VERTEX_CREDENTIALS_PATH`, `VERTEX_PROJECT_ID`,
   `VERTEX_REGION`. Prefer `VERTEX_CREDENTIALS_PATH` over
   `GOOGLE_APPLICATION_CREDENTIALS` — the generic var leaks across multiplexed
   profiles and can mint (and bill) another profile's identity.
4. Check for existing active `VERTEX_*` lines in `.env` before appending so a
   re-run stays idempotent instead of stacking duplicates.
5. Verify by minting a real token, not by file presence: import
   `agent.vertex_adapter` from the hermes-agent tree and call
   `get_vertex_config()`; require a non-empty token plus the expected
   `.../projects/<id>/locations/<region>/endpoints/openapi` URL.
   `hermes doctor` does not cover Vertex, so never treat doctor-green as
   Vertex-verified.
6. Leave the default model untouched unless asked; tell the user to pick Vertex
   via `hermes model` or `/model` in chat.

## Pitfalls

- Never print or paste the SA `private_key` into chat, logs, or replies;
  verify with project_id/client_email/type fields only.
- Write Windows paths in `.env` with forward slashes — backslashes get
  misinterpreted as escapes by dotenv parsing.
- Env/secret wins over `config.yaml` in the adapter; set both so the CLI view
  (`hermes config get vertex`) and the runtime resolution agree.
