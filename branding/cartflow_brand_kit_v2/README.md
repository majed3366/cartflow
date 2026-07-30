# CartFlow Brand Kit V2

**Status:** Official — source of truth for visual identity  
**Source logo:** `logo/cartflow_logo_source.png` (do not redraw or recolor)

## Palette (from logo)

| Token | Hex | Role |
|-------|-----|------|
| `cf-navy` | `#082048` | Brand navy — Cart, icon navy, ink |
| `cf-navy-deep` | `#001838` | Deep chrome / dark bands |
| `cf-teal` | `#18B0A8` | Accent — Flow, CTAs, highlights |
| `cf-teal-deep` | `#0E8E88` | Teal hover |
| `cf-silver` | `#D0D8D8` | Logo glass layers only |
| `cf-bg` | `#F4F7FA` | Page background |
| `cf-surface` | `#FFFFFF` | Cards |
| `cf-ink` | `#082048` | Primary text |

Semantic success/warning/error remain separate and must not replace brand colors.

## Logo variants

| File | Use |
|------|-----|
| `static/img/brand/cartflow_logo.png` | Full lockup (mark + wordmark + tagline) |
| `static/img/brand/cartflow_mark.png` | Icon / mark only |
| `static/img/brand/favicon-32.png` / `favicon-64.png` | Favicon |
| `static/img/brand/og_cartflow.png` | Open Graph / social |

Support contexts: **light**, **dark** (use mark on navy), **monochrome** (navy or white only — never stretch/recolor the official lockup arbitrarily).

## Rules

1. Keep clear space ≥ half mark height around the logo.
2. Never stretch, distort, or recolor the official asset.
3. Minimum mark size: 24px digital; full lockup min width ~120px.
4. Prefer mark in dense UI chrome; full lockup on marketing / auth / loading.
5. Teal is for attention (CTA, active, links) — not full-page fills.
6. White space remains dominant; calm executive feel.

## Typography

- Marketing Arabic: **Tajawal** (400–800)
- Product UI: certified app font via `--cfvi-font-certified` (do not hardcode elsewhere)
- Tagline style (optional labels): uppercase, wide tracking, navy

## Spacing & radius

- Card radius: 16px  
- Soft shadow: `0 4px 24px rgba(8, 32, 72, 0.08)`  
- Rhythm: 6 / 12 / 20 / 28 / 40  

## Files

- `colors/tokens.css` / `tokens.json` — machine tokens  
- `logo/` — official source  
- Production mirrors under `static/img/brand/`
