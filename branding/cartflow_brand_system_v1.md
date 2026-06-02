# CartFlow Brand System v1

**Status:** Official visual identity foundation  
**Version:** 1.0  
**Date:** 2026-06-01  
**Scope:** Foundation for all future visual assets. Does not replace product UI until explicitly applied in a redesign phase.

---

## 0. Purpose

This document is the single source of truth for CartFlow’s visual identity. It applies to:

- Landing page
- Merchant dashboard
- Admin dashboard
- Storefront widget
- Zid marketplace listing
- Documentation
- Marketing assets

**CartFlow is not branded as:** a WhatsApp tool, cart reminder, chatbot, or message sender.

**CartFlow is branded as:** an operational system for **Understand → Decide → Act → Recover**.

---

## 1. Brand Philosophy

CartFlow exists at the moment between intent and outcome — when a customer hesitates, a merchant must **understand** what happened, **decide** what to do, **act** with precision, and **recover** value without noise.

The brand reflects **operational clarity**, not promotional urgency. We do not shout; we orient. We do not decorate; we structure. We do not mimic messaging apps or shopping carts; we represent **flow through decision**.

**Core belief:** Recovery is a disciplined operation, not a blast campaign.

**Design school:** Geometric abstraction — meaning expressed through nodes, paths, junctions, and resolved forms.

---

## 2. Brand Meaning

| Layer | Meaning | Brand expression |
|-------|---------|------------------|
| **Understand** | Signal becomes context | Nodes, observation states, quiet emphasis |
| **Decide** | Context becomes choice | Junctions, branching geometry, focused accent |
| **Act** | Choice becomes motion | Directed paths, purposeful alignment |
| **Recover** | Motion becomes outcome | Closed loops, resolved shapes, stable anchors |

**Visual metaphor chain:** **Node → Path → Decision → Outcome**

- **Node:** A cart, customer, or moment of hesitation (never drawn as a cart icon).
- **Path:** The operational route from signal to action.
- **Decision:** The merchant or system choosing the right recovery move.
- **Outcome:** Completed recovery, archived state, or clear next step.

**Personality:** Calm · Clear · Intelligent · Trustworthy · Operational

**Anti-personality:** Loud · Chatty · Robotic · Growth-hack · Decorative

---

## 3. Visual Principles

1. **Structure before decoration** — Layout and geometry carry meaning; ornament is earned, not default.
2. **Calm density** — Information-rich surfaces use rhythm and whitespace, not color chaos.
3. **One accent, one action** — Primary emphasis per view; secondary states stay muted.
4. **Geometric honesty** — Straight edges, consistent radii, grid-aligned forms. No faux 3D or glossy marketing gradients.
5. **Operational legibility** — Text, numbers, and status always win over brand flourish.
6. **Abstract symbol language** — The mark represents flow and decision, never a channel (WhatsApp) or object (cart).
7. **Bilingual parity** — Arabic RTL and Latin LTR receive equal typographic care; neither is an afterthought.
8. **Scalable silence** — Marks and icons must read at 16px and hold authority at billboard scale.

**Avoid:**

- Shopping cart symbols
- WhatsApp / chat bubble symbols
- Robots, sparkles, “AI brain” clichés
- Up-and-right growth arrows
- Stock chart / funnel graphics as brand decoration
- 3D renders, glassmorphism-as-brand, gradient overload

---

## 4. Shape Language

### 4.1 Primary forms

| Form | Role | Usage |
|------|------|--------|
| **Node** | Point of signal | Dots, small squares, anchor circles (4–8px at UI scale) |
| **Path** | Connection, progression | 1.5–2px strokes, 45° or 90° bends only in brand marks |
| **Junction** | Decision point | Y-fork, chamfered corner, or notch where path splits |
| **Frame** | Container, focus | Rounded rectangle, 8px radius (UI), 12px (marketing cards) |
| **Resolution** | Outcome | Closed path, filled cap, or square node at path terminus |

### 4.2 Corner radii

| Token | Value | Use |
|-------|-------|-----|
| `radius-sm` | 4px | Chips, badges |
| `radius-md` | 8px | Inputs, buttons, cards |
| `radius-lg` | 12px | Modals, feature panels |
| `radius-full` | 9999px | Avatars, pills only |

### 4.3 Stroke & spacing

- **Brand stroke:** 1.5px (icons), 2px (marks at ≥32px)
- **Grid unit:** 4px base; components snap to 4/8/16/24/32
- **Mark clear space:** Minimum padding = height of the mark’s smallest node on all sides

### 4.4 Motion shapes

- Paths **draw on** (stroke-dashoffset), nodes **settle** (opacity + 2px max translate), outcomes **resolve** (fill, no bounce).

---

## 5. Color System

### 5.1 Philosophy

Palette is **slate + flow blue** — trustworthy, operational, distinct from WhatsApp green and generic SaaS purple. Success green exists for **status**, not as the primary brand hue.

### 5.2 Core palette

| Token | Hex | Role |
|-------|-----|------|
| `cf-ink` | `#0F172A` | Primary text, mark on light |
| `cf-ink-muted` | `#475569` | Secondary text |
| `cf-ink-subtle` | `#94A3B8` | Labels, placeholders |
| `cf-surface` | `#FFFFFF` | Cards, panels |
| `cf-surface-muted` | `#F8FAFC` | Page background |
| `cf-surface-raised` | `#F1F5F9` | Hover, striped rows |
| `cf-border` | `#E2E8F0` | Dividers, inputs |
| `cf-border-strong` | `#CBD5E1` | Focus rings (with primary) |

### 5.3 Brand accents

| Token | Hex | Role |
|-------|-----|------|
| `cf-primary` | `#2563EB` | Primary actions, brand emphasis |
| `cf-primary-hover` | `#1D4ED8` | Hover |
| `cf-primary-muted` | `#DBEAFE` | Tinted backgrounds |
| `cf-path` | `#3B82F6` | Links, path accents in illustrations |
| `cf-decision` | `#6366F1` | Decision states, junction highlights |
| `cf-node` | `#1E293B` | Mark nodes, icon anchors |

### 5.4 Semantic (UI — not logo colors)

| Token | Hex | Role |
|-------|-----|------|
| `cf-success` | `#059669` | Recovered, complete, positive signal |
| `cf-success-muted` | `#D1FAE5` | Success background |
| `cf-warning` | `#D97706` | Attention, pending |
| `cf-warning-muted` | `#FEF3C7` | Warning background |
| `cf-danger` | `#DC2626` | Error, blocked |
| `cf-danger-muted` | `#FEE2E2` | Error background |
| `cf-info` | `#0284C7` | Informational |

### 5.5 Dark surfaces (admin, dense ops)

| Token | Hex | Role |
|-------|-----|------|
| `cf-dark-bg` | `#0B1220` | Admin shell background |
| `cf-dark-surface` | `#111827` | Cards on dark |
| `cf-dark-border` | `#1F2937` | Dividers |
| `cf-dark-text` | `#F1F5F9` | Primary on dark |
| `cf-dark-muted` | `#94A3B8` | Secondary on dark |

### 5.6 Usage rules

- **One primary blue** per screen region; do not combine legacy landing green and widget purple in new work.
- **WhatsApp green is never a brand color** — channel icons may appear in integration UI only, not in logo or hero brand moments.
- **Contrast:** Body text on `cf-surface` ≥ 4.5:1; primary buttons white on `cf-primary` ≥ 4.5:1.
- **Marketplace hero:** Prefer `cf-surface-muted` background + `cf-ink` type + single `cf-primary` CTA.

### 5.7 CSS custom properties (reference)

```css
:root {
  --cf-ink: #0F172A;
  --cf-ink-muted: #475569;
  --cf-ink-subtle: #94A3B8;
  --cf-surface: #FFFFFF;
  --cf-surface-muted: #F8FAFC;
  --cf-border: #E2E8F0;
  --cf-primary: #2563EB;
  --cf-primary-hover: #1D4ED8;
  --cf-primary-muted: #DBEAFE;
  --cf-path: #3B82F6;
  --cf-decision: #6366F1;
  --cf-node: #1E293B;
  --cf-success: #059669;
  --cf-warning: #D97706;
  --cf-danger: #DC2626;
  --cf-radius-md: 8px;
  --cf-radius-lg: 12px;
}
```

---

## 6. Typography System

### 6.1 Typefaces

| Role | Latin | Arabic | Fallback |
|------|-------|--------|----------|
| **Display / marketing** | IBM Plex Sans | IBM Plex Sans Arabic | system-ui, sans-serif |
| **UI / dashboard** | Inter | Noto Sans Arabic | system-ui, sans-serif |
| **Data / codes** | JetBrains Mono | JetBrains Mono | monospace |

**Rationale:** IBM Plex conveys operational precision for brand moments; Inter optimizes dashboard density; shared Arabic pairing preserves RTL clarity.

### 6.2 Scale (rem / px at 16px root)

| Token | Size | Line | Weight | Use |
|-------|------|------|--------|-----|
| `text-display` | 2.25rem / 36px | 1.2 | 600 | Landing hero |
| `text-h1` | 1.875rem / 30px | 1.25 | 600 | Page titles |
| `text-h2` | 1.5rem / 24px | 1.3 | 600 | Sections |
| `text-h3` | 1.125rem / 18px | 1.4 | 600 | Cards |
| `text-body` | 1rem / 16px | 1.5 | 400 | Body |
| `text-body-sm` | 0.875rem / 14px | 1.5 | 400 | Tables, meta |
| `text-caption` | 0.75rem / 12px | 1.4 | 500 | Labels, badges |
| `text-mono` | 0.8125rem / 13px | 1.45 | 400 | IDs, timestamps |

### 6.3 Rules

- **Sentence case** for English UI labels; **Arabic** follows standard formal product Arabic.
- **Max line length:** 65ch marketing, 80ch docs, fluid in dashboards.
- **Numbers:** Tabular figures (`font-variant-numeric: tabular-nums`) in all operational tables.
- **Do not** use display type in dense admin tables or widget chrome.

---

## 7. Icon System

### 7.1 Style

- **24×24** default canvas; **20×20** in compact tables; **16×16** in widget inline.
- **1.5px stroke**, round caps and joins (Lucide/Feather-compatible construction).
- **Geometric** — prefer simple shapes over illustrative detail.
- **Filled** icons only for active/selected nav; otherwise outline.

### 7.2 Semantic mapping (abstract, not channel-literal)

| Concept | Icon approach | Avoid |
|---------|---------------|-------|
| Understand | Eye, scan frame, node grid | Magnifying cart |
| Decide | Junction, split path, toggle | Fork with chat bubble |
| Act | Play/run, directed path | Send/paper plane as brand icon |
| Recover | Loop closure, check in frame | Shopping cart return arrow |
| Cart lifecycle | Timeline nodes | Cart silhouette |
| Settings | Sliders in frame | Gear overload on every row |

### 7.3 Brand mark vs UI icons

The **logo mark** is never reused as a 16px utility icon. Extract **node** and **path** motifs for icon consistency without shrinking the full logomark.

---

## 8. Motion Principles

### 8.1 Personality

Motion is **informative**, not celebratory. It confirms state change — it does not perform marketing delight.

### 8.2 Timing

| Token | Duration | Easing |
|-------|----------|--------|
| `motion-instant` | 100ms | ease-out |
| `motion-fast` | 150ms | cubic-bezier(0.2, 0, 0, 1) |
| `motion-standard` | 250ms | cubic-bezier(0.2, 0, 0, 1) |
| `motion-emphasis` | 400ms | cubic-bezier(0.2, 0, 0, 1) |

### 8.3 Allowed patterns

- **Path draw:** Stroke reveals left-to-right (LTR) or right-to-left (RTL) for “flow” illustrations.
- **Node settle:** 2px translate + fade for new signal appearance.
- **Panel slide:** 8–16px max for drawers and widget sheets.
- **Reduced motion:** Respect `prefers-reduced-motion`; replace with instant opacity change.

### 8.4 Forbidden patterns

- Bouncing logos
- Confetti, pulses on every click
- Parallax hero overload
- Infinite spinning except true loading states

---

## 9. Marketplace Guidelines (Zid)

### 9.1 Listing intent

Communicate **cart lifecycle operations** and **merchant control** — not “send WhatsApp messages.”

### 9.2 Required assets

| Asset | Spec | Notes |
|-------|------|-------|
| App icon | 512×512 PNG | Direction chosen from logo exploration; see `/branding/logo_exploration_v2/` |
| Cover / banner | 1200×630 or platform spec | Muted surface, one mark, one headline |
| Screenshots | Real product UI | Frame with `cf-border`; no fake metrics |
| Short description | ≤ 160 chars | Lead with Understand → Decide → Act → Recover |

### 9.3 Copy tone

- **Lead:** Operational outcome (“Clarity from hesitation to recovery”)
- **Support:** Features as verbs: understand reasons, decide recovery, act on schedule, recover revenue
- **Never lead with:** WhatsApp, reminders, chatbot, AI

### 9.4 Visual layout

- Background: `cf-surface-muted`
- Logo: top-left or centered; clear space enforced
- Screenshot borders: 1px `cf-border`, `radius-lg`
- CTA color: `cf-primary` only

---

## 10. Dashboard Guidelines

### 10.1 Merchant dashboard

- **Chrome:** White / `cf-surface-muted` shell; sidebar `cf-surface` with `cf-border` divider.
- **Hierarchy:** Page title `text-h1` → section `text-h2` → card `text-h3`.
- **Status:** Semantic colors only for state — not for navigation branding.
- **Data first:** KPI cards use left stripe (4px) in semantic color, not full gradient cards.
- **Lifecycle visualization:** Node timeline motif — dots connected by 1px path, labels in `text-body-sm`.

### 10.2 Admin dashboard

- May use **dark shell** (`cf-dark-*`) for extended ops sessions.
- Higher information density allowed; **no** decorative illustration in tables.
- Destructive actions: `cf-danger` outline, confirm modals with plain language.

### 10.3 Shared rules

- One primary button per panel.
- Tables: zebra optional via `cf-surface-raised`; sticky headers on long lists.
- Empty states: single line illustration using path/node motif — not cartoon scenes.

---

## 11. Widget Guidelines

### 11.1 Constraints

The widget lives on **merchant storefronts** — it must be quiet, trustworthy, and subordinate to the store brand.

### 11.2 Defaults (when merchant does not customize)

| Property | Value |
|----------|-------|
| Primary | `cf-primary` (`#2563EB`) |
| Surface | `#FFFFFF` |
| Text | `cf-ink` |
| Radius | `radius-md` (8px) |
| Shadow | `0 4px 24px rgba(15, 23, 42, 0.08)` |

### 11.3 Behavior

- **No** CartFlow logo lockup in widget header — optional 16px mark only.
- **No** WhatsApp green as default widget color.
- **No** pulsing chat bubble aesthetic.
- Motion: `motion-fast` panel open; respect reduced motion.

### 11.4 Copy placement

Reason capture → decision → optional handoff. Language mirrors **Understand / Decide / Act**, not “message us on WhatsApp” as headline.

---

## 12. Landing Page Guidelines

### 12.1 Structure (story order)

1. **Hero:** Operational promise + abstract flow illustration (node → path → outcome)
2. **Understand:** Reason capture, signal clarity
3. **Decide:** Merchant control, templates, rules
4. **Act:** Scheduling, automation boundaries
5. **Recover:** Outcomes, lifecycle — honest screenshots
6. **Trust:** Integrations shown as logos in neutral row, not hero gimmicks

### 12.2 Visual tone

- Light mode default; dark hero band allowed (`cf-dark-bg`) with white type.
- Photography: real product screenshots only; device frames minimal.
- Illustration: geometric path diagrams only — no 3D characters.

### 12.3 CTAs

- Primary: “Start with CartFlow” / Arabic equivalent — `cf-btn` filled `cf-primary`
- Secondary: outline `cf-border-strong`

### 12.4 What changes in redesign (not in v1)

Current landing uses legacy green (`--cf-green`). **Future redesign** adopts this document’s `cf-primary` blue and IBM Plex display type. Until then, this file is spec-only.

---

## 13. Logo System (summary)

Full exploration: [`logo_exploration_v2/`](logo_exploration_v2/)

| Direction | Concept | Status |
|-----------|---------|--------|
| **1 — Flow Decision** | Flow pauses; solid form resolves | **Recommended winner** (v2) |
| **2 — Path Outcome** | Path stops; outcome block | Exploration only |
| **3 — Abstract Journey** | Layered depth → resolution | Exploration only |

*v1 exploration (architecture-style diagrams) removed in v2 reset.*

**Wordmark:** `CartFlow` — IBM Plex Sans SemiBold; `Cart` in `cf-ink`, `Flow` in `cf-primary` (optional) or unified `cf-ink` for formal contexts.

**Clear space:** ≥ cap height of “C” on all sides of the mark.

---

## 14. File index

```
branding/
├── cartflow_brand_system_v1.md          ← this document
└── logo_exploration_v2/
    ├── direction_a_geometric_abstraction/
    ├── direction_b_flow_symbol/
    └── direction_c_journey_mark/
```

---

## 15. Governance

- **Changes** to core tokens require bump to v1.1+ and changelog entry in `docs/SYSTEM_SUMMARY.md`.
- **Product UI** must not partially adopt colors without adopting typography and shape rules in the same release slice.
- **Marketplace** assets must be regenerated when a logo direction is selected and finalized.

---

*CartFlow Brand System v1 — foundation only. No product screens were redesigned in this release.*
