# Enabled-but-broken probe

Run when replies are slow or after any provider/MCP change, to list
integrations that are enabled yet non-functional. Probe only — fix
separately.

1. MCP servers: `hermes mcp list`, then `hermes mcp test <name>` for
   each. Record timeouts, 401/403, and OAuth `no cached tokens`
   (parked) states.
2. Fallback chain: `hermes fallback list`, then one minimal request
   per node (an OK-only prompt or a direct endpoint call). A node is
   verified only on a real 200 with content.
3. Provider keys: for each `providers.<name>.key_env` in config, grep
   the `.env` FILE for the name and report present/absent — never print
   values, and never trust a transient shell export.
4. Enabled-skill dependencies: run `hermes doctor` and read each
   enabled skill's manifest for required commands, env keys, and
   packages; missing ones fail at use-time, so either install the
   dependency or disable the skill.
5. Report each broken item with its blast radius (which turns break)
   and the one-line fix; change nothing during the probe.
