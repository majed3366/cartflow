# CartFlow Brand Governance v1

**Effective:** 2026-06-01  
**Authority:** Approved Visual Identity board → `cartflow_brand_foundation_v1/`

---

## 1. Purpose

Ensure **one official visual identity** across CartFlow. All designers, developers, and agents must reference this foundation before making visual changes.

---

## 2. Frozen assets

The following are **approved and locked**:

- CF monogram logo geometry (`logo/`)
- Six-color palette (`colors/`)
- Tajawal typography pairing
- Process + dashboard icon family (`icons/`)
- Motion and UI principles (`brand_guidelines.md`)

---

## 3. Rules

### 3.1 Logo

- **No new logo exploration** without explicit written approval from product owner
- **No geometry changes** to C arc, node, or F bars
- **No alternative marks** in production (archived explorations under `_archive/logo_explorations/`)
- **No** cart, WhatsApp, chat bubble, or robot symbols as brand marks

### 3.2 Color

- **No random color changes** — use `colors/tokens.css` only
- **No** reintroduction of legacy widget purple (`#6C5CE7`) or exploration blue (`#2563EB`) as brand primaries
- **No** WhatsApp green as brand color
- Semantic UI colors (error/warning) allowed for data states only

### 3.3 Icons

- **No alternative icon systems** in product chrome (no unapproved icon font swaps)
- **No** emoji as navigation icons in merchant/admin dashboards
- Process icons must use approved SVGs or exact stroke reproduction

### 3.4 Independent branding

- **No independent branding decisions** outside this foundation
- Marketing, docs, marketplace, and UI PRs that change visual identity must cite `brand_guidelines.md`
- Contractors and AI agents: read foundation first; if spec is silent, ask — do not invent

---

## 4. Historical material (read-only)

| Path | Status |
|------|--------|
| `branding/cartflow_brand_system_v1.md` | Superseded by this foundation |
| `branding/_archive/logo_explorations/` | Archived — do not use |

---

## 5. Change process

1. Propose change in writing with rationale and mockups  
2. Explicit product owner approval required  
3. Update `cartflow_brand_foundation_v1/` with version bump (v1.1+)  
4. Add row to `docs/SYSTEM_SUMMARY.md` §10  
5. Migrate product surfaces in planned releases — no partial orphan adoption  

---

## 6. Implementation phases

| Phase | Scope | Status |
|-------|-------|--------|
| Foundation v1 | This repository folder | **Complete** |
| Logo finalization | Already on board — assets exported in `logo/` | **Complete** |
| Product UI migration | Landing, dashboard, widget, Zid | **Not started** — requires separate tasks |

---

## 7. Enforcement

- PRs that introduce new brand colors, logos, or icon sets should be **rejected** unless linked to an approved governance change
- When in doubt: use `primary_logo.svg` + `tokens.css` + approved icons

---

*Violations of governance erode trust in a single CartFlow identity. Freeze exploration; standardize execution.*
