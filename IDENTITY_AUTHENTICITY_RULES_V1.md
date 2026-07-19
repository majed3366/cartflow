# Identity Authenticity Rules V1

**Status:** Proposed — companion to Identity Foundation Architecture V1  
**Date (UTC):** 2026-07-19  
**Authority:** [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](IDENTITY_FOUNDATION_ARCHITECTURE_V1.md)  
**Contract refs:** IF-P8, IF-10, IF-14 in [`IDENTITY_FOUNDATION_CONTRACT_V1.md`](IDENTITY_FOUNDATION_CONTRACT_V1.md)  
**Trust alignment:** Merchant Trust Constitution — unknown remains unknown; no fabricated merchant facts

---

## Prime directive

> **No merchant-facing surface may fabricate identity.**

Merchant-facing includes: Home, Carts, Knowledge cards, Daily Brief, WhatsApp merchant views, notifications, marketplace copy driven by product data, and any API response consumed by merchant UI.

`/dev` Product review labs with explicit `source=fixture` are **not** merchant-facing production — but must be labeled as review-only and must never be the default for logged-in merchant composition.

---

## AR rules

### AR-1 — Allowed identity speech

| Allowed | Meaning |
|---------|---------|
| **Real identity** | Stable id + human-readable name from Foundation SoT / immutable snapshot |
| **Explicitly unresolved identity** | Merchant-clear language that identity is unavailable / incomplete |

Examples of honest unresolved (illustrative — final Arabic copy owned by Product Language):

- «اسم المنتج غير متوفر بعد»
- «تعذّر التحقق من هوية المنتج»
- Section suppressed / not admitted (silence) when authenticity cannot be met

### AR-2 — Forbidden identity speech

| Forbidden | Examples |
|-----------|----------|
| Placeholder identities | Product X, Product A, منتج X, منتج A, منتج B used as if real |
| Fake examples on production knowledge | Demo-rich fixture names admitted as store truth |
| Synthetic production labels | Invented SKUs/names to “fill the card” |
| Hidden identity degradation | Showing a key (`hp_air`) or hash as if it were the merchant’s product title without disclosure |
| Silent fixture substitution | DB load fails → fixture «منتج X» on Home |

### AR-3 — Counts without identity

Behavioral counts (adds, carts, purchases) **may not** be attached to a fabricated product name.

| Situation | Lawful outcome |
|-----------|----------------|
| Counts exist; identity missing | Do not name a product; say evidence incomplete **or** suppress product finding |
| Identity exists; counts missing | May show identity without conversion claims |
| Neither | Silence / insufficient evidence |

### AR-4 — Fixtures

| Context | Allowed? |
|---------|----------|
| Unit tests | Yes — isolated |
| `/dev` review labs with `source=fixture` | Yes — labeled review-only |
| Merchant Home / Carts / Knowledge production path | **Never** |
| Engine default when `load_db` false | **Forbidden for merchant composition** |

### AR-5 — Simulator and demo

| Rule | Requirement |
|------|-------------|
| **AR-5a** | Simulator must use catalog **display names** (or unresolved), not internal keys, for any field that may reach merchant speech |
| **AR-5b** | Simulator must use the same snapshot ingest path (`lines[]` or equivalent) as production when claiming product identity exists |
| **AR-5c** | Demo catalog real names do not authorize fixture placeholders in Findings |

### AR-6 — Degradation must be observable

Identity loss must leave a signal:

- Health / coverage metrics  
- Loader error logs (not swallowed into empty success + fixture)  
- Admission metadata (`evidence_loaded_from`, confidence, unresolved flags)

Hidden catch-and-replace is an authenticity defect.

### AR-7 — Projection honesty

If identity is not projected to a surface, the surface must not imply the entity is unnamed-but-known.

Omitting product name on Carts while Home names «منتج X» is a **cross-surface authenticity failure**.

### AR-8 — No “better fake” patches

Replacing «Product X» with another invented label (Product A, “Popular item”, random catalog pick) is **still fabrication**.

Fix path: real snapshot/catalog name **or** unresolved/silence.

---

## Enforcement checklist (consumers)

Before admitting a domain entity into merchant speech, verify:

1. [ ] Identity came from Foundation SoT or immutable snapshot  
2. [ ] `evidence_loaded_from` / provenance is not a demo fixture (merchant path)  
3. [ ] Human-readable field is real or explicitly unresolved  
4. [ ] No forbidden placeholder strings in merchant package  
5. [ ] Confidence / admission reflects capture tier (e.g. name-only = low)

---

## Proven violation (baseline)

| Incident | Evidence |
|----------|----------|
| Home Commercial Intelligence showed «منتج X» with 34/22/2 | `demo_rich_fixture_v1`; `HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json` |
| Classification | AR-2 + AR-4 + AR-6 breach |

This baseline is why Identity Foundation is mandatory before further Commercial Knowledge Expansion.
