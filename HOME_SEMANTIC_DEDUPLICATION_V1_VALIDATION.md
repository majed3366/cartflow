# Home Semantic Deduplication V1 — Production Validation

**Date (UTC):** 2026-07-18  

## Production URL

https://smartreplyai.net/dashboard#home

### Fixture URLs (logged-in)

| Path | URL |
|------|-----|
| Healthy | https://smartreplyai.net/dashboard?acf_fixture=healthy#home |
| VIP | https://smartreplyai.net/dashboard?acf_fixture=vip#home |
| Operational | https://smartreplyai.net/dashboard?acf_fixture=operational#home |
| Attention | https://smartreplyai.net/dashboard?acf_fixture=attention#home |
| Pending | https://smartreplyai.net/dashboard?acf_fixture=pending#home |
| Insufficient | https://smartreplyai.net/dashboard?acf_fixture=insufficient#home |

## Contact-scenario expected composition

| Section | Role | Survive? |
|---------|------|----------|
| Business Health | condition | Yes (no contact evidence line) |
| Today’s Priority | action | Yes |
| Business Understanding | explain | Yes (evidence) |
| Biggest Revenue Risk | risk | **Suppressed** — same problem as Priority |
| Biggest Opportunity | opportunity | **Suppressed** — inverse of contact problem |
| Learning Progress | learning | **Suppressed** — paraphrase |
| Timeline contact echoes | event | **Suppressed** |

## Screenshots

Merchant session required for authenticated Home capture. Composition evidence (all six paths): `HOME_SEMANTIC_DEDUPLICATION_V1_EVIDENCE.json`.

Verify in DevTools:

- `home_semantic_composition_v1.suppressed` lists risk/opp/learning
- `adaptive_cognition_v1.section_order` omits suppressed keys
- No second card restating “missing contact blocks recovery”

## STOP

Await Product Experience Review. No Wireframe.
