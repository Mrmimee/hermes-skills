---
name: hermes-gateway-triage
description: Triage slow Hermes gateway replies and skill bloat.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, performance, triage]
    related_skills: [systematic-debugging]
---

# Hermes Gateway Triage

Diagnose slow window replies and skill bloat on a Hermes gateway
without guessing. Distinguish compression, rate-limit, and history
bloat from evidence, then fix the dominant cause first.

## When to Use

- Window reply is slow and user suspects auto-compression
- Telegram/Discord/QQBot latency grows over a session
- Audit which plugins, skills, MCP servers are actually active
- Decide which skills can be disabled for this machine
- Don't use for: one-off transient provider errors that retry
  already fixed; editing bundled `hermes-agent` internals.

## Prerequisites

- Hermes CLI works: `terminal(command="hermes doctor", timeout=45)`
- Gateway home resolves via `$HERMES_HOME`, never hardcoded
  `~/.hermes` when a profile is active
- Logs live under `$HERMES_HOME/logs/`: `agent.log`,
  `errors.log`, `gateway.log`

## How to Run

```
terminal(command="hermes skills list", timeout=30)
terminal(command="hermes tools --summary", timeout=20)
terminal(command="hermes mcp list", timeout=20)
terminal(command="hermes sessions list", timeout=20)
```

## Procedure

1. Snapshot active surface first.
   Run `hermes skills list`, `hermes tools --summary`,
   `hermes mcp list` in one batch. Read `plugins.enabled` /
   `plugins.disabled` from `config.yaml` with `read_file`, list
   `$HERMES_HOME/desktop-plugins/` and `$HERMES_HOME/plugins/`.
   Done when you can state counts: plugins, desktop-plugins, MCP
   servers, enabled vs disabled skills.
2. Check session shape before blaming compression.
   Run `hermes sessions list` and `hermes sessions stats`.
   A history above ~300 messages with 150k+ request tokens is
   the prime suspect even when cache hit rate is 95%+.
   Done when you know the slow session ID and its message count.
3. Verify compression from telemetry, not from feel.
   Search `agent.log` for `conversation_compression` for that
   session ID. `commit_status: committed` with messages
   `483->37` style reduction means compression worked.
   Note `summary_generation_ms` and output tokens.
   Done when you can say compressed or not, with numbers.
4. Check rate-limit and stale-stream evidence next.
   Search `errors.log` for `429`, `RESOURCE_EXHAUSTED`, `401`,
   `ACCESS_TOKEN_EXPIRED`; search `agent.log` for
   `Stream stale for 300s` and `Rate-limit backoff`.
   Repeated 429 with 60s cooldown plus fallback activation means
   the provider is throttling, not the compressor failing.
   A 300s stale kill at 170k-240k tokens means oversized
   context. Done when 429/stale/401 counts are stated.
5. Check gateway delivery times.
   Search `gateway.log` for `response ready` and `time=` for the
   slow session. Rising times across turns (17s to 49s to 146s)
   confirm history growth as the driver.
   Done when latency trend is quoted from logs.
6. Fix in dominance order: new session for bloated history,
   switch or cool down throttled provider, then trim skills.
   Trim per-platform via `hermes skills config`, never by
   deleting bundled skill dirs. Re-verify with one fast turn.
   Done when the next reply latency drops or the new cause is
   named with log evidence.
7. Probe enabled-but-broken integrations when slowness persists.
   Follow `references/enabled-but-broken-probe.md`: `mcp test` every
   server, one minimal probe per fallback node, `key_env` presence
   per provider, `doctor` for enabled-skill dependencies.
   Done when every enabled integration is OK or named as broken
   with its blast radius.

## Pitfalls

- Treat `commit_status: committed` as compression success even when the window still feels slow — slowness then comes from rate-limit or history size, not a compression bug.
- Check fallback chain resolves to a different backend before trusting it — a fallback entry pointing at the same URL is skipped and the 60s cooldown still applies.
- Read `Stream stale 300s` kills as oversized-context signal, not network flake — request tokens near the model limit with hundreds of history messages cause it.
- Start a fresh session for 400+ message histories before tuning anything else — cache hits do not offset system-prompt plus history growth.
- Audit the 18k-char system prompt cost of 50+ enabled skills on constrained machines — per-platform disable beats global delete, and bundled skills are never hand-edited.
- Never persist transient 429 or 401 lines as durable rules — capture the retry-plus-fallback procedure, not `provider X is broken`.
- Check the gateway streaming master before blaming the model — `streaming.enabled: false` delivers whole-turn replies that feel slow on a fast backend; `display.streaming` is CLI-only and proves nothing about the gateway.
- Treat parked OAuth MCPs as background-noise suspects — a server with no cached token retries on a loop and litters the logs; log in interactively or remove it instead of leaving it parked.

## Verification

- Slow session ID, message count, and compression numbers stated
- 429/stale/401 evidence quoted or explicitly absent
- Gateway `time=` trend quoted or explicitly absent
- Fix matches the dominant evidence, follow-up latency checked
