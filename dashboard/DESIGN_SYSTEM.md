# RR PERFORMANCE LAB — Visual Design System

Permanent UI/UX and visual identity specification for all future analytics dashboards, exploratory visual reports, and presentation components in the **SupeRR Selector Season 2** project.

> **Scope Note:** This document defines permanent design standards only. Dashboard implementation is deferred until after data audit, validation, and modeling are complete.

---

## 1. Brand Identity

- **Name:** `RR PERFORMANCE LAB`
- **Tone:** High-trust, modern professional sports analytics (editorial clarity meets front-office scouting war-room precision).
- **Principles:**
  - Data clarity over decoration — every pixel serves readability or decision-making.
  - High contrast for dark-mode analytical surfaces, with restrained Rajasthan Royals pink and gold accents used strictly for hierarchy, highlights, and key KPIs.
  - Zero visual clutter: no excessive gradients, neon glows, heavy drop shadows, or distracting animations.

---

## 2. Color Palette

### Core Tokens

| Role | Name | Hex | Usage |
| :--- | :--- | :--- | :--- |
| Primary Background | Deep Plum | `#24172C` | Main page canvas, app shell, top header |
| Elevated Surface / Card | Secondary Plum | `#392940` | KPI cards, chart containers, sidebar panels, table headers |
| Primary Accent | Royals Pink | `#E83E80` | Active navigation, primary CTA, highlighted series, key metric badges |
| Secondary Accent | Royals Gold | `#D8B45A` | Rank #1 badges, benchmark lines, subtle KPI accents, secondary highlights |
| Primary Text / Light Canvas | Soft Light Grey | `#F5F1F5` | Primary typography on dark surfaces; optional light-mode / print export canvas |
| Muted Text / Gridlines | Muted Lavender | `#B8A6C2` | Secondary labels, subtitles, axis ticks, table borders (`rgba(184, 166, 194, 0.22)`), footnotes |

### Semantic & Chart Encoding Tokens

- **Positive / Above Baseline:** `#4FD1A5` (soft analytical teal-green — high contrast on `#24172C` / `#392940`)
- **Negative / Below Baseline:** `#F26A6A` (muted coral red — distinct from `#E83E80` brand pink)
- **Neutral / Baseline Reference:** `#B8A6C2` (dashed reference lines, league-average baselines)
- **Chart Series Order (max 4–5 series per view):**
  1. `#E83E80` (Primary spotlight — selected player / Royals target)
  2. `#D8B45A` (Comparison benchmark — top-decile / baseline)
  3. `#7C9EF2` (Secondary analytical comparison — e.g., T20I vs. IPL split)
  4. `#B8A6C2` (Cohort / league median background)
  5. `#4FD1A5` (Positive delta / consistency indicator)

---

## 3. Typography

- **Primary UI & Headings:** `Inter`, `Plus Jakarta Sans`, or system sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`).
- **Tabular Numerals (Mandatory for all metrics/tables):** `font-variant-numeric: tabular-nums;` or monospace accent (`JetBrains Mono`) for aligned numeric columns.
- **Type Scale:**
  - Page Title / Brand Header: `24px–28px`, SemiBold (`600`), tight tracking (`-0.02em`), `#F5F1F5`
  - Section Heading: `16px–18px`, SemiBold (`600`), `#F5F1F5`
  - Card / Chart Title: `14px–15px`, Medium/SemiBold (`500–600`), `#F5F1F5`
  - KPI Hero Value: `26px–32px`, Bold (`700`), tabular numerals, `#F5F1F5` (or `#E83E80` / `#D8B45A` for spotlight metrics)
  - Body / Table Cells: `13px–14px`, Regular (`400`), `#F5F1F5`
  - Metadata / Axis Labels / Captions: `11px–12px`, Regular/Medium (`400–500`), `#B8A6C2`

---

## 4. Layout, Spacing & Components

- **Grid System:** 12-column responsive CSS grid; max content width `1440px`; collapse cleanly to 2-column (tablet) and 1-column (mobile).
- **Spacing Scale:** Strict 4px/8px rhythm (`8px`, `12px`, `16px`, `24px`, `32px`).
  - Card internal padding: `16px–20px`
  - Grid gap between cards/charts: `16px–20px`
  - Section vertical separation: `24px–32px`
- **Compact Statistic (KPI) Cards:**
  - Surface `#392940`, 1px border `rgba(184, 166, 194, 0.18)`, corner radius `10px`.
  - Structure: uppercase muted label (`11px`, `#B8A6C2`), primary figure (`28px`, `#F5F1F5`), compact delta/context line beneath.
  - Optional 3px top or left accent bar in `#E83E80` or `#D8B45A` only on spotlight cards.
- **Tables & Leaderboards:**
  - Compact row height (`36px–40px`), right-aligned numeric columns, sticky header, subtle row divider (`rgba(184, 166, 194, 0.12)`), gentle hover highlight (`rgba(232, 62, 128, 0.08)`).
  - Always show sample sizes (`Balls`, `Innings`, `Matches`) alongside rate metrics.

---

## 5. Charting & Visualization Standards

- **Chart Hygiene:**
  - Direct clear titles + 1-line analytical subtitle stating units, sample filter, and competition scope (e.g., `IPL + T20I, 2022–2026`).
  - Explicit axis labels with units; clear, unobtrusive legends placed top-left or inline.
  - Horizontal gridlines only (thin `1px`, `rgba(184, 166, 194, 0.15)`); remove chart junk, 3D effects, and redundant spines.
  - Always display baseline reference lines (e.g., player usual performance or cohort median) with direct annotations.
  - Include data source & sample-size footer on every analytical figure.
- **Matplotlib / Static Export Compatibility:**
  - All Matplotlib exploratory/report figures should optionally support both the **RR Dark Theme** (`#24172C` figure / `#392940` axes) for dashboard/slide views and **RR Print Light Theme** (`#F5F1F5` / `#FFFFFF` background with `#24172C` text and `#E83E80` / `#D8B45A` accents) for PDF methodology reports.

---

## 6. Motion & Interaction Rules

- **Minimal Animations:** Fast, subtle state transitions only (`150ms–200ms ease-out` on hover/tab/filter change).
- **No decorative loops, pulsing glows, parallax, or heavy entrance choreography.**
- **Accessibility:** Maintain WCAG AA contrast (`>= 4.5:1`) for all primary text (`#F5F1F5` on `#24172C` exceeds `13:1`; `#F5F1F5` on `#392940` exceeds `10:1`). Never encode meaning by color alone — pair with rank labels, icons, or numeric deltas.

