# Theme CSS pitfalls (hermes-telegram-neon-flow plugin.js)

The plugin's CSS lives in one template-string `css` blob, injected as a `style` element at
register time; `plugin.js` is the single source of truth — edit the installed file at
`C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js`.

## Radix popper wrapper selectors must exclude tooltips

Desktop Radix components (menus, selects, dialogs, tooltips) all render their content inside a
`[data-radix-popper-content-wrapper]` element. A broad selector like
`[data-radix-popper-content-wrapper]>*` with `!important` background/border/box-shadow/backdrop-filter
is the pattern used to apply the theme's "glass" treatment to menus and popovers — but it also
matches **tooltip bubbles**, which are the one Radix surface that uses an **inverted** color
scheme by design:

- Tooltip content class: `bg-foreground text-background` (dark bubble, light text in light
  mode; light bubble, dark text in dark mode) — see
  `apps/desktop/src/components/ui/tooltip.tsx` `PaneClippedContent`.
- Menus/selects/dialogs use `bg-popover`/`bg-background` — same hue family the theme's glass
  rules target, so overwriting them is invisible.

Result of the bug: light mode renders a near-opaque white box with near-white text (unreadable);
dark mode renders near-black with near-black text (barely readable). Symptom users report: "white
box / black box appears on hover over model selector and other buttons, text hard to see in light
mode."

**Fix pattern:** wherever the theme's glass rules target
`[data-radix-popper-content-wrapper]>*`, scope it to
`[data-radix-popper-content-wrapper]>:not(.tooltip-bubble)` — in the background, border,
box-shadow, and backdrop-filter rules alike. The `.tooltip-bubble` class is stable (defined in
`components/ui/tooltip.css`); prefer that selector over trying to match by data-slot or other
attributes.

**Always verify** that when adding a new `[data-radix-popper-content-wrapper]`-based rule, the
same exclusion is applied — a rule added later for shadow or border without it reintroduces the
bug on tooltips specifically.

## Pushing a locally-validated fix to remote main

Before pushing any local `plugin.js` fix to remote `main`:

1. **`git fetch` and diff against `origin/main`** — a `revert:` commit on remote may have undone a previously-fixed bug. If remote is behind your local state, your local file is the correct one to push; never push a file older than `origin/main` without explaining to the user what you are overwriting.
2. **Commit with a short, accurate description** (e.g. `fix: exclude tooltips from glass overrides; split dialog/menu glass backgrounds by mode`).
3. **Push using the stored token** in `~/.git-credentials` (extract the token portion, embed it in the push URL, restore the remote URL afterward). If the token is rejected, tell the user to update the file — do not ask for the token in chat.

## Pitfalls in CSS authoring

The `css` blob uses `:root[data-hermes-theme="hermes-telegram-neon-flow"][data-hermes-mode="light"]`/`[dark]`
variants. If a rule sets a surface color that must differ between modes (e.g. sidebar, header,
composer background — the "light" branches at lines ~69-72 in the current file), it needs BOTH
branches written explicitly. A rule that only writes the shared (mode-agnostic) version inherits
`--dt-*` theme tokens, which flip with mode, but a hardcoded rgba value does NOT flip — if you
hardcode a surface, you must write both `[data-hermes-mode="light"]` and `[data-hermes-mode="dark"]`
overrides, matching the existing sidebar/header/composer pattern.

## Verification without CDP

The packaged desktop app (`release/win-unpacked/Hermes.exe`) does not expose a dev CDP port
(9222 is only open in dev-server runs; see the `inspecting-hermes-desktop-dom` skill for details).
When verifying a theme change on the running user app, you cannot read computed styles live —
rely on: the file syntax check (`node --check`), byte/diff review against the pattern above, and
asking the user to hover a model button / open a menu after hot-reloading to confirm the visible
result.
