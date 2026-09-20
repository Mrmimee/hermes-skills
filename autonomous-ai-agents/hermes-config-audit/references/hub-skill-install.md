# Hub Skill Installs

For installing skills from the Skills Hub (`hermes skills search/install`),
distinct from bundled plugins and MCP servers.

## Procedure

1. **Check installed first** — run `hermes skills list` and filter for the
   target names before searching; update in place instead of reinstalling
   a duplicate.
2. **Prefer provenance in this order** — `official` catalog entry, then
   `trusted` upstream repo, then community mirrors; when several community
   mirrors share a name, pick the upstream author's repo.
3. **Install non-interactively** — `hermes skills install <identifier> --yes`
   so nothing blocks on a prompt; a backgrounded install is polled, not
   re-run.
4. **Verify each one** — `hermes skills list` shows it enabled, `skill_view`
   loads its SKILL.md, and any bundled CLI reports its version.
5. **Report per skill** — install location under `$HERMES_HOME/skills/`,
   what it is for, how it is invoked, and whether it conflicts with an
   already-loaded skill (complementary scopes are not conflicts).

## Pitfalls

- Honor an explicit exclusion list verbatim — never substitute a skipped
  skill with a lookalike.
- A scan verdict that names concrete risky patterns is authoritative —
  report it and stop rather than guessing the code is safe.
- `hermes skills check` may report `update_available` immediately after a
  fresh install; re-run `update` once and move on instead of chasing it.
