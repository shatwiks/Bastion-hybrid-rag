# Change Report

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
