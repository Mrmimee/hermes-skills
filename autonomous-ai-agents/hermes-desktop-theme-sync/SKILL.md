---
name: hermes-desktop-theme-sync
description: "Use to sync or rollback Hermes desktop theme from GitHub."
---

# Hermes Desktop Theme Sync & Rollback

Syncs, updates, or rolls back the user's Hermes desktop theme plugin from its upstream GitHub repo. Covers version matching, CRLF handling, and byte-level verification.

## When to Use

- User says the theme "has an update" / "check for updates" / "pull latest".
- User says a version has a bug and wants to revert / roll back.
- User asks to verify which version of the theme is currently installed.

## User-Specific Standing Rules

- **Local clone does NOT exist on disk.** The user's theme repo is `Mrmimee/hermes-telegram-neon-flow`, main branch `telegram-glass-v2`. Despite what memory may say about a local clone, there is no local git clone to pull from. Clone from GitHub into `$LOCALAPPDATA/Temp` (or a scratch dir), operate on the fresh clone, then clean it up.
- **File-level sync only.** Never run `switch`, `reset`, `merge`, `push`, or `rebase` on the local clone or any other repo for this user. Copy `plugin.js` out of a commit, overwrite the installed file, done.
- **Installed path:** `C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js`. This is the only file that matters — no other files are part of the install.
- **After any update or rollback, tell the user to hot-reload:** `⌘K → Reload desktop plugins` in the Hermes desktop app. The plugin watcher picks up the file change but the user should confirm the reload happened.
- **Obsidian project note:** `C:/Users/mnb77/OneDrive/Documents/Obsidian Vault/Projects/Hermes Telegram Neon Flow/Progress.md` is the primary, kept-current record (latest commit SHA + root-cause summary). An older `运维速查/Hermes Telegram Neon Flow主题.md` also exists but is not kept up to date — treat `Projects/.../Progress.md` as the source of truth. Update it after any commit/fix; the user prefers to log completed-task learnings there without being asked first.
- **Memory note is stale.** Memory says a local clone lives at `C:/Users/mnb77/Downloads/hermes-telegram-neon-flow` — that path does not exist. Do not try `cd` into it. Use GitHub clone workflow below.

## Update Workflow (apply latest version)

1. Clone the repo into a scratch dir (not the user's home):
   ```bash
   cd "$LOCALAPPDATA/Temp" && rm -rf hermes-neon-flow-sync && \
   git clone --depth 1 --branch telegram-glass-v2 \
     https://github.com/Mrmimee/hermes-telegram-neon-flow.git hermes-neon-flow-sync
   ```
2. Show the user what's changing before writing. For this repo, check `CHANGELOG.md` and `package.json` for the version, and `git log --oneline -5` for recent commits. Diff summary:
   ```bash
   diff <(cat plugin.js) "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js" | head -80
   ```
3. Syntax-check the new file before overwriting:
   ```bash
   node --check plugin.js   # exit 0 = OK
   ```
4. Copy into place:
   ```bash
   cp plugin.js "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js"
   ```
5. Verify:
   ```bash
   ls -la "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js"
   node --check "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js"
   ```
6. Clean up scratch dir: `rm -rf "$LOCALAPPDATA/Temp/hermes-neon-flow-sync"`
7. Report to user: which version/commit was applied, byte size before and after, and remind them to `⌘K → Reload desktop plugins`.

## Rollback Workflow (user says current version has a bug)

This is the higher-risk path — you need to find the exact previous commit whose `plugin.js` matches the installed byte size, not just "the parent of the current HEAD."

1. Clone with full history (no `--depth`):
   ```bash
   cd "$LOCALAPPDATA/Temp" && rm -rf hermes-neon-flow-sync && \
   git clone https://github.com/Mrmimee/hermes-telegram-neon-flow.git hermes-neon-flow-sync
   ```
2. Get the current installed byte size first — it's the target to match:
   ```bash
   wc -c "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js"
   ```
   Note: the installed file uses CRLF line endings (Windows), so a `git show <commit>:plugin.js | wc -c` gives the LF byte count. To get the CRLF byte count, append a carriage return to every line: `git show <commit>:plugin.js | sed 's/$/\r/' | wc -c`. Compare that against the installed size.
3. List commits that touched `plugin.js` and check byte sizes:
   ```bash
   git log --all --oneline -- plugin.js
   ```
   For each candidate commit, compute CRLF byte count:
   ```bash
   git show <commit-sha>:plugin.js | sed 's/$/\r/' | wc -c
   ```
   The commit whose CRLF byte count matches the installed file byte count is the version to restore.
4. Extract, verify syntax, overwrite, clean up:
   ```bash
   git show <matched-sha>:plugin.js | sed 's/$/\r/' > "$LOCALAPPDATA/Temp/restored-plugin.js"
   node --check "$LOCALAPPDATA/Temp/restored-plugin.js"
   cp "$LOCALAPPDATA/Temp/restored-plugin.js" "C:/Users/mnb77/AppData/Local/hermes/desktop-plugins/hermes-telegram-neon-flow/plugin.js"
   ```
5. Tell the user which commit was restored and remind them to hot-reload.

## Push to GitHub (only when the user explicitly asks, e.g. "同步到 github")

The "file-level sync only" rule above applies to the **local** sync direction (pull → overwrite installed file). When the user says "sync to GitHub" / "同步到 GitHub" / "push", they mean the opposite direction: push the currently working local `plugin.js` state to remote `main`. Do this only on explicit request — never auto-push after a local sync or rollback.

Procedure:
1. Clone the full repo (no `--depth`, no branch restriction): `git clone https://github.com/Mrmimee/hermes-telegram-neon-flow.git hermes-neon-flow-sync` in `$LOCALAPPDATA/Temp`.
2. Copy the installed `plugin.js` (the one at `desktop-plugins/hermes-telegram-neon-flow/plugin.js`, i.e. the local state the user has validated) into the clone's working tree.
3. **Before committing, `git fetch` and diff against `origin/main`** — check whether remote has reverted any previously-fixed bug (a `revert:` commit that restored old, buggy CSS). If remote is behind local state, your local file is the correct one to push. Never push a file that is older than `origin/main` without explaining to the user what you are overwriting.
4. `git add plugin.js && git commit -m "<short description>"`.
5. Push with the stored token: `TOKEN=$(head -n1 ~/.git-credentials | sed -E 's#https://[^:]+:([^@]+)@.*#\1#')`, then `git push "https://Mrmimee:${TOKEN}@github.com/Mrmimee/hermes-telegram-neon-flow.git" main`. If the token is rejected (expired/rotated), tell the user to update `~/.git-credentials` — do not ask for a token in chat.
6. Clean up: `rm -rf "$LOCALAPPDATA/Temp/hermes-neon-flow-sync"`.

## Pitfalls

- **`cd C:/Users/mnb77/Downloads/hermes-telegram-neon-flow` will fail** — the local clone referenced in memory does not exist. Always work from a fresh GitHub clone in a scratch dir.
- **CRLF vs LF byte counts differ.** `git show <commit>:plugin.js` produces LF-terminated content; the installed file on disk is CRLF-terminated. Byte-compare only after `sed 's/$/\r/'` on the git-show output, or the match will be off by one byte per line.
- **`/tmp/` is `C:/Users/mnb77/AppData/Local/Temp/` in MSYS (git-bash). `node` (a native Windows binary) cannot resolve MSYS paths like `/tmp/foo.js`.** Use absolute Windows-style paths (`C:/Users/mnb77/...` or `$LOCALAPPDATA/Temp/...`) when passing files to `node`, `git`, or other native tools.
- **Don't `git switch` or `git reset` the scratch clone** — the user's rule is file-level sync only. Extract the file, copy it out, that's the whole operation.
- **If the rollback target commit is on a branch other than the one you cloned (e.g., `main` vs `telegram-glass-v2`), the `git log --all` approach finds it regardless of branch** — don't restrict to `--branch` when hunting for a past commit.
- **The repo's active branch is `main`.** `telegram-glass-v2` is a stale branch (its last commit predates several fix commits that landed on `main`). Clone with `--branch main` for updates and pushes; only use `--branch telegram-glass-v2` if the user explicitly asks for that older branch. When hunting for a rollback target, use a full clone (no branch restriction) so `git log --all` covers everything.

## Verification

- `node --check <installed-path>` exits 0.
- Byte size of installed file matches the expected version's CRLF byte count (computed as above).
- If a rollback: the installed content does NOT contain identifiers that were only introduced in the buggy version (e.g., for the 2026-09 v2.4.0 bug, `MOTION_ID` constant was the new feature; its absence confirms the rollback landed).

## Related

- `hermes-agent` skill → `references/desktop-plugins.md` — general desktop plugin SDK reference.
- `hermes-desktop-theme-sync` → `references/theme-css-pitfalls.md` — CSS-authoring pitfalls for this theme (Radix popper/tooltip exclusion, light/dark mode branching, verifying without CDP).
- Obsidian project note `Projects/Hermes Telegram Neon Flow/Progress.md` — human-readable project history; update after significant changes.
