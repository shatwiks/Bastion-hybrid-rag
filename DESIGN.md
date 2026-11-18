# Design System — Limestone Atelier

## Visual Identity
- **Mode:** Operate (high-clarity enterprise knowledge workspace & live technical inspector).
- **World:** Limestone Atelier — an architectural security dossier pairing a committed deep patina-teal command bar with a warm limestone telemetry rail and crisp off-white paper reading sheets.
- **Anti-Patterns Refused:** Zero dark-neon AI themes, zero violet/indigo accents, zero nested rounded card stacks, zero decorative eyebrows/kickers above headings, zero thick colored `border-left` callouts, and zero blinking status dots.

## Color Tokens (`frontend/src/app/globals.css`)

| Role | Token | Value | Usage |
| :--- | :--- | :--- | :--- |
| Command Shell | `--shell-bg` | `#133136` | Top persona & scope bar |
| Shell Controls | `--shell-surface` / `--shell-rule` | `#1b4046` / `#28565e` | Utility buttons & segmented frame |
| Workspace Ground | `--ground` | `#f2f0ea` | Telemetry rail, modal headers, subtle chips |
| Reading Paper | `--paper` | `#fcfbf8` | Chat reading canvas, composer, inspection modals |
| Secondary Mineral | `--mineral` | `#e7e3d9` | Track backgrounds & skeleton loaders |
| Hairline Rules | `--rule` / `--rule-strong` | `#d7d2c6` / `#beb8aa` | `1px` architectural dividers & inputs |
| Ink Scale | `--ink` / `--ink-secondary` / `--ink-muted` | `#162124` / `#465558` / `#5f6e71` | Primary prose (`>13:1`), metadata (`>7:1`), captions (`>4.6:1`) |
| Primary Accent | `--copper` / `--copper-soft` | `#b55228` / `#faf0eb` | Active role, primary Ask/Ingest button, inline citation chips, focus rings |
| Pass / Cache Hit | `--jade` / `--jade-soft` | `#116b4f` / `#eaf5f0` | Completed stages, `>= 0.65` gauge pass, Redis cache hit |
| Refusal / 403 | `--crimson` / `--crimson-soft` | `#a82828` / `#fdefef` | `< 0.65` deterministic refusal banner, HTTP 403 RBAC guard |
| Caution Notice | `--ochre` / `--ochre-soft` | `#8f5609` / `#faf4e8` | Public persona ingestion warning & init retry banner |

## Typography (`frontend/src/app/layout.tsx`)
- **UI & Reading Sans:** `Source Sans 3` (`400`, `500`, `600`, `700`) — `15px / 1.68` prose on a `68ch` max reading measure.
- **Data & Code Mono:** `JetBrains Mono` (`400`, `500`, `600`) — reserved strictly for identifiers (`tenant_id`, `scope_hash`, `chunk_id`, `trace_id`), inline code spans, and `font-variant-numeric: tabular-nums` latency/score tables.

## Layout & Signature Move
- **Structure:** Edge-to-edge split workspace (`62%` paper chat / `38%` collapsible limestone telemetry rail) separated by a single `1px` hairline, stacking vertically below `1024px` (`lg:`) with zero horizontal overflow at `390px`.
- **Progressive Disclosure:** The 4 starter scenario rows appear cleanly on the empty canvas and collapse once a turn starts, remaining accessible via the `"Guided Scenarios"` toggle in the composer bar.
- **Signature Move:** The **Calibrated `0.65` Refusal Gate Vernier Gauge** inside Step 4 of `TelemetryInspectorDrawer`, rendering calibrated ticks (`0.00`, `0.25`, `0.50`, `0.65 gate`, `1.00`) and switching cleanly between jade `PASS` and crimson `REFUSED` alongside the tabular 6-step transit rail and RRF → Cross-Encoder Candidate Funnel.

## Surface & Accessibility Rules
- Custom copper text selection (`::selection`), copper text caret, `2px` copper `:focus-visible` ring, subtle limestone scrollbars, `prefers-reduced-motion` compliance, `Escape` dismissal on dialogs, and zero `dangerouslySetInnerHTML`.
