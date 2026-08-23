# Design Spec: TrashTag — Field Ops Dashboard

*"Tag the trash. Flag the roads."*

**Handoff document.** This is a design brief + build spec for an internal ops dashboard, not the final code. Follow it as the source of truth; deviate only if something in here is technically unworkable, and note why.

---

## 0. Product context

**What it is:** the review dashboard for TrashTag, a pipeline that detects potholes and garbage dumps from citizen dashcam/phone/drone footage. AI flags candidate issues; a small ops/inspector team reviews evidence, confirms real issues, and files them via CPGRAMS or a city-specific portal (PMC Road Mitra, PCMC, etc.) as fallback.

**Naming note:** the product name is garbage-scoped by itself, so the tagline carries the pothole half of the scope — keep title lockups in this dashboard (header, browser tab title, loading states) paired with the tagline where space allows, not just the bare wordmark.

**Who uses it:** 3–15 municipal ops reviewers and field inspectors, at a desk or in a field vehicle, working through a queue of AI-flagged detections against a map. Not citizen-facing.

**The page's one job:** let a reviewer look at a cluster of evidence (photo + GPS + confidence), decide real/not-real in one motion, and push it toward filing — as fast and unambiguously as possible.

**Tone:** this is inspection paperwork, not a consumer product. It should feel like a well-run municipal engineering office that happens to have good tooling — precise, unfussy, slightly official. Not playful, not corporate-SaaS.

---

## 1. Design plan (token system)

### Grounding
The subject is road/civic infrastructure inspection — worked at night as often as day (dashcams), documented like engineering records, and classified using the same color logic India's own civic systems already use (road hazard markings, wet/dry waste bin colors, survey/blueprint conventions). The design should borrow directly from that vernacular rather than generic dashboard styling. Signature device: an **inspection docket** — every detection renders as a stamped, ticket-like card, not a generic list row or a rounded "material card."

### Color — "night patrol" palette
Dark base (dashcam footage, night patrolling, floodlit worksites are the natural environment), with *functional* accent colors tied to real-world civic color-coding rather than one decorative brand accent.

| Token | Hex | Use |
|---|---|---|
| `--asphalt-900` | `#15181A` | page background |
| `--asphalt-700` | `#1F2326` | panel/card surfaces |
| `--concrete-400` | `#8A9095` | secondary text, borders |
| `--chalk-100` | `#EDEFEC` | primary text |
| `--hazard-yellow` | `#F2B705` | pothole class, primary alerts, focus ring |
| `--waste-green` | `#4C8C5C` | garbage class (India's wet-waste bin green) |
| `--survey-blue` | `#5C8AA8` | map elements, geo/location data, "filed" state |
| `--stamp-red` | `#C5533A` | rejected/duplicate, destructive actions only |

No gradients. No glow effects. Color is a classification system first, decoration never.

### Type — three roles, no serif
- **Display / headers:** a condensed, slightly industrial grotesk with real personality at large sizes — e.g. **Archivo Expanded/Condensed** or **Barlow Condensed**, semibold/black, all-caps for section labels, tight tracking. Reads like stenciled signage, not editorial.
- **Body/UI:** a clean, highly-legible grotesk at normal width — **Inter** or **IBM Plex Sans** — for everything a reviewer reads quickly under time pressure.
- **Utility/data:** a monospace — **IBM Plex Mono** or **JetBrains Mono** — reserved *only* for GPS coordinates, timestamps, detection IDs, confidence scores. This is what makes the docket cards feel like real field records, and it gives the eye a fast way to distinguish "data" from "prose" at a glance.

Scale: display headers 28–40px condensed caps; body 14–16px; data/mono 12–13px, letter-spaced slightly for coordinate legibility.

### Layout concept
Command-center split: persistent filter rail, top status strip, map + docket queue as dual, resizable panes (map is the spatial truth, queue is the work truth — a reviewer needs both simultaneously, not tabs).

```
┌─────────────────────────────────────────────────────────────┐
│ TRASHTAG   [city: PUNE ▾]               ● 12 pending review  │  ← status strip
├───────────┬─────────────────────────────┬───────────────────┤
│  FILTERS  │                             │  DOCKET QUEUE      │
│           │                             │  ┌───────────────┐ │
│  Class    │         MAP VIEW            │  │ #A-0442  ⬤     │ │
│  ☑ Pothole│    (geo-clustered pins,     │  │ [photo thumb] │ │
│  ☑ Garbage│     yellow=pothole,         │  │ 18.52,73.85   │ │
│           │     green=garbage,          │  │ conf 0.91     │ │
│  Status   │     pulse = new)            │  │ [VERIFY][SKIP]│ │
│  ○ New    │                             │  └───────────────┘ │
│  ○ Filed  │                             │  ┌───────────────┐ │
│           │                             │  │ #A-0441  ⬤     │ │
│  Ward ▾   │                             │  │ ...           │ │
│  Date ▾   │                             │  └───────────────┘ │
└───────────┴─────────────────────────────┴───────────────────┘
```

Below the fold (or a secondary tab): a **filed log** — flat table of everything already submitted to an authority, for audit/tracking (status: submitted → in_progress → resolved).

### Signature element: the docket card
Every detection is a stamped ticket, not a card:
- Slightly rotated (−0.5° to 0.6°, randomized per card via nth-child, not per-render) rubber-stamp badge in the corner: `NEW` / `VERIFIED` / `FILED` / `REJECTED`, dashed circular or double-ring border, in the class or status color, mixed-blend so it looks pressed into the surface rather than pasted on.
- A perforated/torn top edge (CSS `mask` or repeating radial-gradient) separating a photo-evidence strip from the data strip below it — evoking a tear-off inspection docket.
- Data strip in monospace: detection ID, lat/long, timestamp, confidence — laid out like a manifest line, not prose.
- One-line reviewer actions: `Verify`, `Reject`, `Merge` (for duplicate/nearby detections) — active verbs, no icons-only ambiguity.

This is the one place the design spends its boldness. Everything else — filters, map chrome, tables — stays quiet, grid-aligned, and undecorated.

---

## 2. Self-critique (why this isn't a default)

- Not cliché #1 (cream + serif + terracotta): no serif, no cream, no single warm accent — dark base with a multi-color functional system instead.
- Not cliché #2 (near-black + one neon accent): base is dark but there are three co-equal functional accents (yellow/green/blue) tied to real classification meaning, not one decorative pop color.
- Not cliché #3 (broadsheet hairlines): grid is used for data density, not editorial hairline dividers; the docket-card device is the opposite of dense newspaper columns.
- Risk taken deliberately: the stamp/docket motif. If it reads as gimmicky in build, the fallback is to keep the perforation + mono data strip but drop the rotation — flag this as a build-time judgment call.

---

## 3. Content & microcopy voice

Write for a reviewer moving fast, not a citizen. Plain, declarative, no apology, no marketing language.

- Empty queue: `No pending detections in this ward.` (state the fact; don't say "Great job!")
- Action labels: `Verify`, `Reject`, `Merge with nearby`, `Export batch` — the label matches the resulting state exactly (a "Verify" action produces a `VERIFIED` stamp, never a generic "Done" toast).
- Errors: `Detection #A-0442 could not be filed — authority endpoint unreachable. Retry or export manually.` State what happened and the next action; never vague.
- Status strip counts are literal numbers, not vague health language ("12 pending review," not "mostly clear").

---

## 4. Motion (use sparingly)

- Page load: status strip and map settle in first (~150ms), docket queue cards stagger in (~40ms offset each, max 6 staggered, rest appear instantly) — orchestrated once, not per-scroll.
- New detection arriving in the queue: card slides in from top of queue list with a brief yellow/green left-edge flash matching its class, then settles. This is the one ambient "live system" cue — don't add others.
- Hover on docket card: subtle lift (2px translateY + shadow), stamp badge does *not* animate — it should feel fixed/official, not interactive.
- Respect `prefers-reduced-motion`: disable stagger and slide-in, keep instant state changes only.

---

## 5. Technical build notes

- **Format:** single self-contained `dashboard.html` (HTML + CSS + vanilla JS in one file, per the artifact convention) — no build step, no framework, since this is a spec/prototype handoff.
- **Data:** use realistic mock data (10–15 detections) hardcoded as a JS array — Pune-area lat/longs, mixed pothole/garbage classes, mixed confidence scores, mixed statuses — so the UI reads as populated and real, not lorem-ipsum.
- **Map:** no live map tiles/API dependency for this spec pass — render a stylized abstract map (SVG or CSS grid representing streets) with positioned pins, OR use Leaflet + OpenStreetMap tiles via CDN if network access in the artifact environment allows it. Prefer the stylized abstract version first — it's on-brand (survey/blueprint aesthetic) and has zero dependency risk.
- **Fonts:** load Barlow Condensed / Archivo Expanded, Inter, IBM Plex Mono from Google Fonts or a CDN (`fonts.googleapis.com` — confirm reachable; fall back to system font stacks with matching character if not).
- **Responsive floor:** filter rail collapses to a top drawer under ~900px; map and queue stack vertically under ~700px. Docket cards remain single-column on mobile.
- **Accessibility floor:** visible keyboard focus ring in `--hazard-yellow`, all filter controls keyboard-operable, color is never the only signal (class also shown as text label, status also shown as stamp text, not color alone), contrast-checked chalk-on-asphalt text meets AA.
- **CSS specificity:** use a single flat class-naming convention (BEM-lite: `.docket`, `.docket__stamp`, `.docket__data`) — avoid mixing type selectors with class selectors for the same elements to prevent the padding/margin cancellation issue called out in the design skill.

---

## 6. Deliverable checklist for the building instance

- [ ] Status strip: city selector, live pending count
- [ ] Filter rail: class checkboxes, status radio, ward dropdown, date range
- [ ] Map pane: stylized abstract map, class-colored pins, cluster on zoom-out
- [ ] Docket queue: scrollable list of docket cards per spec above, mock data populated
- [ ] Docket card: photo evidence strip, perforation divider, mono data strip, rotated stamp badge, Verify/Reject/Merge actions
- [ ] Filed log (secondary view/tab): flat audit table
- [ ] Empty state, error state per copy voice above
- [ ] Responsive breakpoints per §5
- [ ] Reduced-motion handling
- [ ] Self-review: take a screenshot, check against §2 critique before calling it done
