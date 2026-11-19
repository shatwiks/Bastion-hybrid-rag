# Change Report

## 2026-11-19 10:49 IST — Unify `/workspace` with `tasteskill 2.5.1` (`stone-blueprint` + `urbanist` + `sharp` + `ui-pipe` Tool Marks)

### Objective
Apply the dealt `tasteskill 2.5.1` design system (`stone-blueprint` palette, `Urbanist` + `DM Mono` typography, `sharp` radius scale, dealt `ring` brand mark, and `ui-pipe` / `ui-win` visual grammar with real full-colour tool icons and a live execution terminal log) to the interactive RAG workspace at `/workspace`.

### Files Modified
- `frontend/src/app/(workspace)/layout.tsx` — Switched workspace fonts to `Urbanist` + `DM Mono`, set `data-type="software"` and `data-radius="sharp"`, and linked `/favicon.svg`.
- `frontend/src/app/globals.css` — Replaced Limestone Atelier CSS tokens with the dealt `tasteskill 2.5.1` `stone-blueprint` tokens (`--ground: #dfdedb`, `--mineral: #d3d2ce`, `--paper: #ffffff`, `--ink: #26251e`, `--shell-bg: #26251e`, `--copper: #2456d6` blueprint cobalt) and added `.taste-mark-ring`.
- `frontend/src/components/PersonaBar.tsx` — Added dealt `ring` mark (`taste-mark-ring`), `Bastion / workspace` breadcrumb, `← Overview` link to `/`, and `stone-blueprint` inverse dark segmented switchers.
- `frontend/src/components/ChatViewport.tsx` — Added `.b-win__bar` / `.ui-win__bar` window sub-bar (`acme_corp · support_tier_1`, `scope_hash`, `pgvector HNSW · Dual-FTS · 0.65 Gate`).
- `frontend/src/components/TelemetryInspectorDrawer.tsx` — Styled inspector header after `ui-pipe__head` (`bastion/rag / acme_corp #f51251`), added real full-colour tool icons on `22×22` light tiles (`FastAPI`, `Redis`, `PostgreSQL`, `Python`, `Ollama`, `Docker`) to all 6 stages, and added a live `$` terminal execution log strip (`ui-pipe__log`).
- `frontend/src/components/CitationPopover.tsx` & `frontend/src/components/AdminIngestionModal.tsx` — Aligned modal backdrops and borders with `stone-blueprint` and `sharp` radius tokens.
- `frontend/public/assets/chapter-scope.png`, `frontend/public/assets/ui-preview.png`, `docs/assets/ui-desktop.png`, `docs/assets/ui-mobile.png` — Refreshed live Chromium screenshots at `1440×900` and `390×844`.

### Verification Commands & Results
- **TypeScript & Route Typegen:** `cd frontend; npx next typegen; npx tsc --noEmit` -> `TSC_EXIT=0`
- **XSS Audit:** `XSS_COUNT=0`
- **Live Screenshots (`shoot.mjs`):** Captured and visually verified `1440×900` and `390×844` views of `http://localhost:3005/workspace`.

---

## 2026-11-19 10:35 IST — Bastion Hybrid RAG Product Landing Page (`/`) & Live Workspace Route (`/workspace`) (`tasteskill 2.5.1`)

### Objective
Execute `/design-taste-frontend` (`tasteskill 2.5.1`) to build a production product landing page for **Bastion Hybrid RAG** at `/` while preserving the interactive Limestone Atelier RAG workspace at `/workspace`, and pass the `tasteskill 2.5.1` headless Chrome finish gate (`gate.mjs`).

### Files Created, Modified, or Deleted
- **Created:**
  - `frontend/src/app/(landing)/layout.tsx` — Root layout for `/` declaring `data-type="software"`, `data-radius="sharp"`, `data-ground="sand"`, `data-buttons="tonal"`, `data-motion=""`, Urbanist + DM Mono font links, `tasteskill` kit stylesheets, and `/assets/bastion-enter.js`.
  - `frontend/src/app/(landing)/page.tsx` — 6-section (`9` screens) Bastion Hybrid RAG landing page at `/` with dealt `centred` hero (`gradient-mesh` ground + dark application window), `app-frame` split window (`window` + `pipeline-board`), 2×2 guardrails section (`chat`, `terminal-run`, `search`, and `hub` diagram), dealt `pinned-chapters` scroll walkthrough with 3 live Bastion workspace captures, benchmark specification split with `stat` chart, and 4-question open FAQ with 28×28 full-colour stack marks (`Postgres`, `Redis 8`, `FastAPI`, `Ollama`) and `footer--dark` (`close-type`).
  - `frontend/src/app/(workspace)/layout.tsx` & `frontend/src/app/(workspace)/workspace/page.tsx` — Relocated the Limestone Atelier interactive RAG workspace intact to `/workspace`.
  - `frontend/src/components/LandingScripts.tsx` — Client script loader that mounts `/assets/backgrounds/backgrounds.js`, `/assets/system.js`, `/assets/motion/motion.js`, `/assets/layout/layout.js`, and `/assets/diagrams/mount.js` after hydration.
  - `frontend/public/assets/bastion-landing.css` — Dealt `stone-blueprint` + `urbanist` + `sharp` tokens and responsive layout rules for `.hero__window`, `.b-win`, `.app.ui`, `#engine`, `#benchmarks`, `.stack-icons`, and `#walkthrough`.
  - `frontend/public/assets/bastion-enter.js`, `frontend/public/favicon.svg`, `frontend/public/share.png` — Dealt `ring` mark favicon, hero entrance script, and OpenGraph preview image.
  - `frontend/public/assets/*` — Untouched `tasteskill 2.5.1` runtime kit (`system.css`, `system.js`, `layout/`, `ui/`, `motion/`, `backgrounds/`, `diagrams/`, `effects/`, `moments/`, `icons/`) and workspace chapter screenshots (`chapter-scope.png`, `chapter-citation.png`, `chapter-refusal.png`, `ui-preview.png`).
- **Modified:**
  - `frontend/src/components/PersonaBar.tsx` — Linked the `Bastion` brand mark in the workspace top command bar back to `/`.
  - `.gitignore` — Added `.taste-skill/` to ignore local headless Chrome verification profiles and gate crops.
- **Deleted:**
  - `frontend/src/app/layout.tsx` & `frontend/src/app/page.tsx` — Replaced by route groups `(landing)` (`/`) and `(workspace)` (`/workspace`).

### Verification Commands & Results
- **`tasteskill 2.5.1` Finish Gate (`gate.mjs`):**
  - Command: `cd frontend; node "C:\Users\shatw\.gemini\config\skills\taste-skill\scripts\gate.mjs" http://localhost:3005/`
  - Result: `gate: no open FAIL` / **`GATE: PASS`** (0 waivers, 0 kit edits, verified across `1440x900`, `1280`, `1152`, `1024`, `896`, `820`, `768x1024`, `390x844`, and `320x640`, plus reduced-motion, no-script, WebGL shader-fallback, and copy lint passes).
- **TypeScript & Route Typegen:**
  - Command: `cd frontend; npx next typegen; npx tsc --noEmit`
  - Result: `TSC_EXIT=0` (`✓ Types generated successfully`).
- **XSS / `dangerouslySetInnerHTML` Audit:**
  - Command: `(Select-String -Path "frontend\src\**\*.tsx","frontend\src\**\*.ts" -Pattern "dangerouslySetInnerHTML").Count`
  - Result: `XSS_COUNT=0`.
- **Live HTTP Endpoint Checks:**
  - `GET http://localhost:3005/` -> `200 OK`
  - `GET http://localhost:3005/workspace` -> `200 OK`
  - `GET http://127.0.0.1:8000/api/v1/health` -> `200 OK`
