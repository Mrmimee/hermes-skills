---
name: hermes-styling-and-theming
description: "Use when styling or theming Hermes CLI, TUI, or Dashboard."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Theming, Skins, Dashboard, CSS, Marquee, HarmonyOS, Telegram]
---

# Hermes Styling and Theming

Guidelines, design patterns, and operational procedures for creating, customizing, and activating color themes and visual skins across Hermes Agent surfaces (CLI, TUI, Web Dashboard, and Desktop GUI).

## 1. Theming Surfaces & Storage Architecture

Hermes divides visual customization across two primary configuration stores under `<hermes-home>` (`get_hermes_home()`):

1. **CLI / TUI Skins (`<hermes-home>/skins/<name>.yaml`)**:
   - Defines semantic color roles, spinner animations, and branding for terminal and console interfaces.
   - Activated via `display.skin` in `config.yaml`.
2. **Dashboard Themes (`<hermes-home>/dashboard-themes/<name>.yaml`)**:
   - Defines CSS-compatible 3-layer palettes (`background`, `midground`, `foreground`), typography, layout variants, component styles, and arbitrary `customCSS`.
   - Activated via `dashboard.theme` in `config.yaml`.
3. **Desktop GUI App Themes (`<hermes-home>/desktop-plugins/<id>/plugin.js`)**:
   - The Hermes Desktop app (Electron) runs on its own React renderer realm and does not repaint from CLI `display.skin` alone.
   - Requires registering a `DesktopTheme` via `THEMES_AREA` from `@hermes/plugin-sdk` or injecting custom styles via runtime desktop plugins.

---

## 2. Dual-Polarity Auto-Switching Skins (Dark/Light Pairing)

Hermes `SkinConfig` natively supports polarity pairing, allowing a single skin file to gracefully adapt when the user or terminal toggles between dark and light backgrounds.

### Schema Structure
```yaml
name: harmony-dual
description: Dual-mode adaptive skin — Dark Navy / Light Warm Orange

# Base fallback palette
colors:
  background: "#0e1621"
  ui_accent: "#2481cc"
  banner_accent: "#2481cc"
  banner_title: "#5288c1"
  banner_text: "#e4ecf2"
  ui_text: "#e4ecf2"
  banner_dim: "#708499"
  banner_border: "#232e3c"
  ui_border: "#232e3c"
  prompt: "#5288c1"
  input_rule: "#2481cc"
  response_border: "#2481cc"
  status_bar_bg: "#17212b"
  status_bar_text: "#e4ecf2"

# Evaluated when terminal/host reports dark mode
dark_colors:
  background: "#0e1621"
  ui_accent: "#2481cc"
  banner_title: "#5288c1"
  banner_text: "#e4ecf2"
  ui_text: "#e4ecf2"
  banner_border: "#232e3c"
  ui_border: "#232e3c"
  input_rule: "#2481cc"
  response_border: "#2481cc"

# Evaluated when terminal/host reports light mode
light_colors:
  background: "#f8f9fa"
  ui_accent: "#f56e00"
  banner_title: "#e05300"
  banner_text: "#1c1e21"
  ui_text: "#1c1e21"
  banner_border: "#e4e6eb"
  ui_border: "#e4e6eb"
  input_rule: "#f56e00"
  response_border: "#f56e00"
```

---

## 3. Soft Flowing Marquee & Breathing Border Effects (`customCSS`)

When crafting animated streaming light or marquee effects for chatboxes and input composers:

### Pitfalls to Avoid
- **Avoid rapid flashing or high-contrast strobe effects**: High-frequency keyframes induce eye strain during long working sessions.
- **Avoid hard multi-colored outlines**: Sharp rainbow borders look unpolished and clip irregularly on rounded elements.

### Recommended Recipe
Use slow-cycle (6s–8s), smooth sinusoidal easing (`ease-in-out`), and softly layered `box-shadow` with lower opacities (`0.15` to `0.25`) and moderate blur radii (10px–24px).

```yaml
name: soft-stream
label: Soft Stream Marquee
description: Gentle flowing marquee and breathing glow theme

palette:
  background:
    hex: "#0c0f17"
    alpha: 1.0
  midground:
    hex: "#818cf8"
    alpha: 1.0
  foreground:
    hex: "#5eead4"
    alpha: 0.15
  warmGlow: "rgba(129, 140, 248, 0.25)"
  noiseOpacity: 0.03

typography:
  fontSans: "'HarmonyOS Sans SC', system-ui, sans-serif"
  fontMono: "'JetBrains Mono', monospace"
  baseSize: "14px"
  lineHeight: "1.6"

customCSS: |
  @keyframes soft-marquee {
    0% {
      box-shadow: 0 0 10px rgba(94, 234, 212, 0.22), 0 0 20px rgba(129, 140, 248, 0.12);
      border-color: rgba(94, 234, 212, 0.5);
    }
    33% {
      box-shadow: 0 0 10px rgba(129, 140, 248, 0.22), 0 0 20px rgba(192, 132, 252, 0.12);
      border-color: rgba(129, 140, 248, 0.5);
    }
    66% {
      box-shadow: 0 0 10px rgba(192, 132, 252, 0.22), 0 0 20px rgba(244, 114, 182, 0.12);
      border-color: rgba(192, 132, 252, 0.5);
    }
    100% {
      box-shadow: 0 0 10px rgba(94, 234, 212, 0.22), 0 0 20px rgba(129, 140, 248, 0.12);
      border-color: rgba(94, 234, 212, 0.5);
    }
  }

  textarea,
  input[type="text"],
  [class*="composer"],
  [data-slot="composer"] {
    animation: soft-marquee 7s infinite ease-in-out !important;
    border-radius: 8px !important;
  }
```

---

## 4. Activation & Environment Execution Rules

1. **Never hand-edit `config.yaml`**: Always invoke `hermes config set display.skin <name>`. Hand edits risk YAML indentation corruption and break the live gateway process.
2. **Interpreter Resolution Pitfall on Windows**:
   - The default `python` executable in the host PATH may be an unbundled Python interpreter lacking project packages (e.g. `yaml`). Running `python -m hermes_cli.main config set ...` under that environment fails with `ModuleNotFoundError: No module named 'yaml'`.
   - **Resolution**: Directly invoke the dedicated virtual environment Python:
     ```bash
     "<hermes-home>/hermes-agent/venv/Scripts/python.exe" -m hermes_cli.main config set display.skin <name>
     ```
3. **Verification**:
   Confirm skin discovery and active selection via:
   ```bash
   "<hermes-home>/hermes-agent/venv/Scripts/python.exe" -m hermes_cli.main skin list
   ```
   The active skin will be flagged with `*` and marked as `user`.

---

## 5. Hermes Desktop (Electron GUI) Theme Adaptation & Injection

### The Pitfall: CLI Skins Do Not Automatically Theme the Desktop App
- **Mechanism**: The Electron desktop application (`apps/desktop`) maintains its own independent React renderer realm with its own theme registry (`THEMES_AREA`) and `localStorage` stores (`hermes-desktop-theme-v2`).
- Setting `display.skin` in `config.yaml` updates only terminal CLI/TUI surfaces. When users complain that changing a skin had no effect on the desktop app, it is because desktop requires registering a `DesktopTheme` through the desktop plugin door or switching via the desktop-specific `/skin` command.

### Desktop Plugin Theme Architecture
Desktop plugins live under `<hermes-home>/desktop-plugins/<plugin-id>/plugin.js`. The desktop app's runtime watcher automatically detects and hot-reloads them within seconds.

#### Registering a Desktop Theme
```javascript
import { host, requestTheme, THEMES_AREA, Tip } from '@hermes/plugin-sdk'
import { jsx } from 'react/jsx-runtime'

const MY_DESKTOP_THEME = {
  name: 'my-theme',
  label: 'My Custom Theme',
  description: 'Custom theme for Hermes Desktop',
  colors: {
    // Light mode palette (required keys: background, foreground, primary)
    background: '#ffffff',
    foreground: '#1f2328',
    primary: '#0053fd',
    card: '#f6f8fa',
    border: '#d0d7de',
    input: '#ffffff',
    ring: '#0053fd',
    composerRing: '#0053fd'
  },
  darkColors: {
    // Optional dark mode palette
    background: '#0e1621',
    foreground: '#e4ecf2',
    primary: '#2481cc',
    card: '#17212b',
    border: '#232e3c',
    input: '#0e1621',
    ring: '#2481cc',
    composerRing: '#2481cc'
  },
  typography: {
    fontSans: "'HarmonyOS Sans SC', system-ui, sans-serif",
    fontMono: "'Cascadia Mono', monospace"
  }
}

export default {
  id: 'my-theme-plugin',
  name: 'Custom Theme Plugin',
  register(ctx) {
    // 1. Register theme in desktop theme picker
    ctx.register({
      id: 'my-theme',
      area: THEMES_AREA,
      data: MY_DESKTOP_THEME
    })

    // 2. Switch theme programmatically from plugin code
    requestTheme('my-theme')

    // 3. Inject DOM styles directly for live effects (e.g. streaming marquee)
    if (typeof document !== 'undefined') {
      const style = document.createElement('style')
      style.id = 'my-theme-effects'
      style.textContent = `
        /* Target stable composer selectors */
        [data-slot="composer-rich-input"],
        form:has([data-slot="composer-rich-input"]) {
          border-radius: 12px !important;
          animation: softMarqueeAura 5.5s ease-in-out infinite !important;
        }
      `
      document.head.appendChild(style)
    }
  }
}
```

### Stable Desktop Selectors (for CSS Injection)
- **Composer input**: `[data-slot="composer-rich-input"]`
- **Thread viewport**: `[data-slot="aui_thread-viewport"]`
- **Assistant messages**: `[data-slot="aui_assistant-message-root"]`
- **Turn pairs**: `[data-slot="aui_turn-pair"]`
- **Profile rail**: `[data-slot="profile-rail"]`

### Hot Reload & Switching
- Users can reload desktop plugins immediately via `Ctrl+K` -> `Reload desktop plugins`.
- Users can cycle or switch installed themes inside the desktop chat via `/skin` or `/skin <name>`.

### The Desktop LocalStorage Theme Cache Pitfall (Lingering Themes in Appearance)
- **The Symptom**: After deleting a custom skin or theme YAML from disk, the theme still appears in the desktop app's Settings -> Appearance grid.
- **Root Cause & Mechanism**:
  1. Hermes Desktop caches backend-synced themes in renderer `localStorage` under `hermes-desktop-backend-themes-v1`. On app startup, `readCached()` loads all valid cached entries from this key before network sync.
  2. In `appearance-settings.tsx`, the delete button (`Trash2`) only renders when `removable = isUserTheme(theme.name)`. `isUserTheme` returns `true` ONLY for themes installed from the Marketplace into `hermes-desktop-user-themes-v1`; it returns `false` for backend-synced themes. Thus, no trash can icon appears on the card to manually delete it.
- **Resolution**:
  - To completely purge removed backend themes from the desktop client, clear the cache key in the renderer context:
    ```javascript
    window.localStorage.removeItem('hermes-desktop-backend-themes-v1')
    window.localStorage.setItem('hermes-desktop-backend-themes-v1', '{}')
    ```
  - This can be executed via a temporary one-shot desktop plugin or devtools, followed by a window reload (`Ctrl+R`).

---

## 6. Minimalist Theming Discipline (Avoiding UI Clutter)

- **Never patch Hermes core codebase when fixing a theme plugin**: When troubleshooting an external or user-authored theme plugin, never edit `apps/desktop/src/...` or other Hermes core files. All fixes, cache purges, and compatibility handling must be contained strictly inside the plugin's own `plugin.js` / repository.
- **Strictly adhere to declarative theme formats**: When tasked with creating or deploying a theme for Hermes (CLI, TUI, Dashboard, or Desktop), produce clean, standard theme specifications (Skin YAML or native `DesktopTheme` color definitions). A theme's core responsibility is palette data (`colors`, `darkColors`, `typography`, `terminal`).
- **Theme vs. Application Seam (Never Hijack App DOM / Structure)**:
  - Do not cross the line from theming into application-level UI hacking. When injecting CSS via `plugin.js`, NEVER attach backgrounds, borders, or shadows to structural outer containers like `[data-slot="aui_turn-pair"]` or `[data-slot="profile-rail"]`. Doing so creates "box-in-a-box" clunkiness that users perceive as invasive application tampering rather than a theme.
  - Confine additive CSS strictly to leaf elements (e.g. `[data-slot="aui_assistant-message-root"]` for glass cards, or `:focus-within` on the composer).
- **Avoid Over-Designed / Jarring Effects ("元素太突兀")**:
  - **No Persistent RGB/Marquee Outlines**: Never wrap inputs in constant animated rainbow borders (`::before` with rotating gradients). Resting state MUST be quiet and clean; animated breathing glows (alpha 0.10–0.20) are acceptable ONLY on active user interaction (`:focus-within` / typing).
  - **No Candy-Wrapper Gradients on Message Bubbles**: Avoid dual-tone diagonal linear-gradients on chat bubbles. Use clean, single-tone, authentic tints (e.g., Telegram light `#E3F2FD` / dark `#2B5278`) with subtle matching borders.
  - **Neutral, Unobtrusive Scrollbars**: Never apply glowing neon gradients or `box-shadow` to scrollbar tracks/thumbs; keep them semi-transparent neutral capsules that fade into the background.
- **Single Canonical Registration Only ("只保留最完全那个")**: Never leave secondary alias registrations (`theme-alias`) in the final deliverable. Multiple registrations pollute the Appearance settings grid with duplicate cards sharing the same label. Keep only the single, canonical `name`/`id` registration, and rely on startup cache eviction (`localStorage.removeItem` / JSON key deletion) to clear older entries.
- **Never bolt on unsolicited UI scaffolding**: Do not create custom floating bars, composer banner strips, or interactive test widgets (`::preview`) in the user's chat space unless explicitly asked. Users consider intrusive UI wrappers to be visual clutter and noise.
- **Enforce YAGNI**: Focus purely on the requested visual attributes (palettes, typography, subtle CSS animations), keeping the implementation zero-overhead, completely native, and free of extraneous runtime code.
- **Complete Reversal Protocol**: When asked to revert or restore visual customization work, ensure cleanup covers both the filesystem (YAML, `.css`, plugin directories) AND renderer persistence stores (`localStorage` cached theme registries) so that no ghost items remain in UI pickers.

---

## 7. Vibrant / Neon Light-Mode Palette Design (Preventing Bland "素" Light Modes)

### The Pitfall: Neon Themes Washing Out in Light Mode
- **Symptom**: A theme looks striking in dark mode (deep OLED black `#07070B` + glowing cyan/purple/pink neon), but when switched to light mode, the user complains it looks dull, plain, or washed-out ("怎么白色看着这么素").
- **Mechanism**: Translating dark neon directly by swapping background to off-white (`#F8F7FB` / `#FFFFFF`) while desaturating primary/accents to pale pastels (`#7B6FF2`, `#FF79B8`, `#F7E9F3`) strips out all visual identity. Without black contrast, low-saturation pastels render as an indistinct, generic gray interface.

### Telegram Official Dual-Palette Implementation Reference
Telegram's official Day and Night themes achieve clean, high-contrast, airy aesthetics through specific tinting rules:

1. **Telegram Light (Day & Crystal Blue)**:
   - **Background**: Cool air-slate tint (`#F0F2F5` / `#EEF1F4`, ~2% cool blue tint), NEVER muddy flat gray (`#EEEEEE` / `#F8F7FB`).
   - **Surfaces/Cards**: Pure crisp white (`#FFFFFF`). The slight air-slate background makes pure white cards float and breathe with clear depth.
   - **Primary Action**: Authentic Telegram Blue (`#24A1DE` / `#2AABEE`, 75%+ saturation), NEVER muted lavender/purple.
   - **User Chat Bubble**: Telegram's signature soft crystal-blue (`#E3F2FD` / `#E8F4FD`) with soft ice-blue border (`#C2E0F9`). This breaks up monochrome text blocks and gives chat rhythm.
   - **Border & Rings**: Cold gray border (`#DCE2E9`), electric neon cyan ring (`#00C6FF`), and electric pink accent (`#FF4FD8`).
   - **Text**: Deep slate black (`#111827`), secondary text (`#657786`).

2. **Telegram Dark (Night & Deep Sea)**:
   - **Background**: Prussian deep-sea night blue (`#0E1621`), not pitch black or flat gray.
   - **Surfaces/Cards**: Deep night slate (`#17212B`).
   - **Primary Action**: Night-adapted electric blue (`#5288C1`).
   - **User Chat Bubble**: Deep ocean blue (`#2B5278`) with border (`#386494`), keeping high contrast with pure white text (`#F5F5F5`).
   - **Border & Rings**: Deep border (`#243447`), glowing neon cyan ring (`#00C6FF`), and neon pink accent (`#FF4FD8`).

### Design Principles for Vibrant Light-Mode Adaptations
1. **Preserve High-Saturation Signature Colors**:
   - Do NOT pastel-wash the brand color. In Telegram/Neon themes, use the authentic vibrant brand blue (e.g. Telegram Blue `#24A1DE` / `#0088CC`) or vibrant neon purple (`#8A5CFF`) for `primary`.
2. **Maintain Electric Neon Accents**:
   - Keep `ring`, `composerRing`, and `accent` punchy (e.g. electric cyan `#00C6FF` or vivid magenta/pink `#FF4FD8`). A glowing border on an input box needs high saturation to be visible against white surfaces.
3. **Tinted Surfaces Over Flat Grays**:
   - Instead of neutral gray cards and user bubbles (`#F3F1F8`, `#F7E9F3`), give surfaces subtle branded tinting (e.g., Telegram light-blue message bubble `#E3F2FD` with border `#BEE3F8`, or pale aurora violet `#F3E8FF`).
4. **Contrast Integrity**:
   - Ensure text foreground (`#111827` or `#1E1B2E`) maintains high contrast against tinted cards, keeping typography crisp while letting the neon framing pop.

---

### Desktop Theme Resolution Precedence & the Backend-Skin Shadowing Bug

When diagnosing "light/dark toggle does nothing" (or a duplicated single-mode palette) on the desktop app for a **user/desktop-plugin-contributed theme that ALSO exists as a CLI skin** (`$HERMES_HOME/skins/<same-name>.yaml` + `display.skin` set to it):

**Root cause (verified in `apps/desktop` source):**

1. Desktop's theme resolver (`apps/desktop/src/themes/user-themes.ts::resolveTheme`) tries, in order: `BUILTIN_THEMES` → `$userThemes` (Marketplace installs, localStorage `hermes-desktop-user-themes-v1`) → `$backendThemes` (CLI skin sync, localStorage `hermes-desktop-backend-themes-v1`) → `contributedThemes()` (desktop plugins' `THEMES_AREA` registrations).
2. Backend-synced themes are converted by `apps/desktop/src/themes/skin.ts::skinToDesktopTheme`, which **deliberately assigns the SAME palette object to both `colors` and `darkColors`** — a CLI skin is single-mode by design, so the converter documents: "the light/dark toggle shouldn't invert it. `renderedModeFor` still paints `.dark` from luminance."
3. If the desktop plugin registers a theme with the SAME `name` as an active CLI skin, the `$backendThemes` entry (single-mode duplicate) resolves FIRST and shadows the plugin's correct distinct `colors`/`darkColors`. The light/dark toggle (`Shift+X` / Appearance → Color Mode) then flips between two identical palettes = no visible change, while all other (non-shadowed) themes toggle normally. This is the exact failure signature to check before suspecting the plugin's own code or the user's settings.

**Fix:** Never ship a third-party desktop-plugin theme's `name`/`id` matching a CLI skin file you also author for the same project, OR do not set `display.skin` to that name in `config.yaml` — keep the desktop-plugin theme (with real dual-mode palettes) and the CLI skin (single active polarity) as distinct, non-colliding names, or simply don't create/activate the redundant CLI skin at all if only the desktop app needs the theme.

**How to verify the shadow is live, not just configured:**
- `grep -ri "<theme-name>" $HERMES_HOME/backups/config/` and `$HERMES_HOME/logs/agent.log` for `skin_engine: Skin '<name>' not found` / stale `display.skin` entries — confirms whether a same-name CLI skin was ever active (which is what seeded `$backendThemes` even after the YAML is deleted, until the cache key is cleared).
- Since `$backendThemes` is a localStorage cache, deleting the YAML and resetting `display.skin` alone does NOT purge the already-synced duplicate entry; the user must also clear `hermes-desktop-backend-themes-v1` (see Section 5's cache pitfall) and reload the window before the shadow releases.
- **Self-healing via the plugin itself (no devtools needed):** If the shadow is baked into an already-running desktop app and the user will not open devtools, add cleanup code to the top level of the theme's `plugin.js` that runs on every plugin load:
  ```javascript
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      for (const storeKey of ['hermes-desktop-backend-themes-v1', 'hermes-desktop-user-themes-v1']) {
        const raw = window.localStorage.getItem(storeKey)
        if (raw) {
          const parsed = JSON.parse(raw)
          let changed = false
          for (const key of ['<old-skin-name>', '<new-plugin-name>']) {
            if (parsed && parsed[key]) { delete parsed[key]; changed = true }
          }
          if (changed) window.localStorage.setItem(storeKey, JSON.stringify(parsed))
        }
      }
    } catch (e) { /* ignore */ }
  }
  ```
- **Never use alias registration to paper over stale caches**: Do NOT register a secondary `theme-alias` (`ctx.register({ id: 'theme-alias', ... })`). Multiple theme registrations with the same `label` create duplicate identical cards in the Appearance settings grid ("看到两个一样的了"), which confuses and frustrates users. Always keep a **single canonical registration** (`id: 'theme'`, `name: '<canonical-id>'`), and let startup localStorage eviction purge the stale entry silently.
- **Locating the actual stale entry without devtools:** Electron's localStorage lives in LevelDB under `AppData/Roaming/Hermes/Local Storage/leveldb/*.ldb` + `*.log`. Grep those binary files for the theme name (e.g. `python -c "open('...ldb','rb').read()"` + substring search) to confirm which entries are actually cached before deleting — do not assume deletion of the source YAML cleared the cache.

---

## 8. Third-Party Theme Repository Ingestion & Deployment Workflow

When the user asks to pull and install an external GitHub theme project:

### Standard Ingestion Sequence
1. **Clone to Downloads**: Run `git clone <repo_url>` under the user's Downloads directory (`Downloads/<repo-name>`).
2. **Inspect Tokens & Assets**: Read `package.json`, `theme/*.ts` or `*.json`, and `styles/*.css` to extract:
   - Base colors (background, surface, text, border, primary/accent).
   - Dynamic gradients or effects (aurora flow, marquees, shadows).
   - Typography opinions (e.g. HarmonyOS Sans SC, monospace fonts).
3. **Tri-Surface Deployment**:
   - **CLI / TUI**: Create `<hermes-home>/skins/<id>.yaml` with full `colors`, `dark_colors`, `light_colors`, and `branding`.
   - **Dashboard**: Create `<hermes-home>/dashboard-themes/<id>.yaml` with `palette`, `typography`, and `customCSS`.
   - **Desktop GUI**: Create `<hermes-home>/desktop-plugins/<id>/plugin.js` registering `THEMES_AREA` via `@hermes/plugin-sdk` and injecting dynamic animation `<style>` tags if required.
   - **Pitfall**: If the repo ships its OWN ready-to-install desktop plugin (`plugin.js` registering `THEMES_AREA`, e.g. a `DesktopTheme` object with correct `colors` + `darkColors`), do NOT hand-roll a duplicate `plugin.js` in a different folder — install the repo's file as-is (copy it verbatim into `<hermes-home>/desktop-plugins/<id>/plugin.js`) to stay faithful to the upstream project's exact token values, and only fall back to hand-authoring if the repo is theme-data-only (no plugin entrypoint). Likewise, if the repo is desktop-plugin-only (per its own README), it is legitimate to SKIP the redundant CLI-skin + dashboard-theme YAMLs entirely rather than forcing all three surfaces — only author the extra YAMLs if the user actually uses the CLI/TUI terminal surface and wants that skin too. Re-verify against upstream: run `git pull` in the cloned repo and re-copy `plugin.js` whenever the user reports the repo has been updated.
4. **Verification**:
   - Verify CLI skin discovery via `<venv_python> -m hermes_cli.main skin list`.
   - Activate via `<venv_python> -m hermes_cli.main config set display.skin <id>`.
   - **If `display.skin` is set to a skin whose name matches a desktop-plugin theme name, verify Section 5's new "Backend-Skin Shadowing Bug" does not null out the desktop light/dark toggle before calling it done.**
5. **Concise User Handoff**:
   - Report the cloned location, installed files, and immediate switching instructions (`/skin <id>` in desktop chat, `Ctrl+K` -> `Reload desktop plugins`).

### Repeat Updates (user says 更新 / 又更新了 / 继续拉取)
Treat any one-word update prompt as pull-then-sync-then-verify in ONE command chain — never pull without syncing, because the Downloads clone is NOT the live file (the desktop app only reads `<hermes-home>/desktop-plugins/<id>/plugin.js`).
1. `git -C <clone> fetch --all --prune` + `git -C <clone> pull --ff-only` — fast-forward only, so a diverged local edit fails loudly instead of silently merging.
2. `cp <clone>/plugin.js <hermes-home>/desktop-plugins/<id>/plugin.js` every time, even when the pull reports no change — the live copy drifts whenever anyone edits either side.
3. Verify with `diff -q <clone>/plugin.js <live>/plugin.js` (expect silence = synced) plus `git log --oneline -3` and `git status -sb` (expect clean, tracking remote with no behind-count).
4. Ignore `diff -rq` noise about `assets/`, `README.md`, `styles/`, `theme/` existing only in the clone — the live folder legitimately holds just `plugin.js`; only a `plugin.js differs` line matters.
5. No restart needed — the desktop watcher hot-reloads within seconds; offer `Ctrl+K` -> `Reload desktop plugins` only as fallback when the user reports no visible change.
6. Reply in one concise line: old-hash → new-hash, commit subject, file stat (`+x/-y`), synced/live confirmation — match the weight of the ask, never a process replay.



