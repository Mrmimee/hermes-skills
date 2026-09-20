# External Capability-Layer Tools

For CLIs that extend the agent but are not Hermes plugins or MCP servers
(web-access layers, per-platform readers, skill routers). They own their own
directories and lifecycle; Hermes only consumes their skill file and shell.

## Procedure

1. **Isolate the runtime** — install into a dedicated venv (`~/.<tool>-venv`),
   never into the Hermes venv and never assuming a global installer exists.
2. **Run the check-only mode first** — most installers ship a safe default
   (`--dry-run`, safe-mode check) that reports missing pieces without
   changing the host; run it before anything that writes.
3. **Gate writes on explicit approval** — flags like `--system` that install
   dependencies or write configs run only after the user approves.
4. **Keep the workspace clean** — tool repos, tokens, and temp files go in
   the tool's own dirs (`~/.<tool>/`, `/tmp/`), never the agent workspace.
5. **Verify with the tool's own doctor** — report per-channel status and
   name what still needs credentials; credential-gated channels need
   user-supplied cookies/keys, preferably on secondary accounts.

## Pitfalls

- A missing global installer is an environment detail, not a blocker — fall
  back to `python -m venv` plus the repo archive URL.
- Record where the tool drops its SKILL.md (it may serve several agents
  from one shared path) so future sessions can re-read routing without
  reinstalling.
