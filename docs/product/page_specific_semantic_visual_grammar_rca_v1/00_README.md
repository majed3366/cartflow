# Page-Specific Semantic Visual Grammar RCA V1

**Status:** CLOSED (audit) — implementation authorized separately  
**Production SHA audited:** `b8c1318a06e99fe75eccefecf7e4492db489ab4d`  
**Protected model:** `semantic-visual-model-v1` (unchanged)  
**Implementation:** see `docs/product/page_specific_semantic_composition_v1/`

## Verdict

`semantic-visual-model-v1` made primitives **truth-driven**. It did **not** make them **page-specific**.

Root composition gap: **PROVEN**.

Intended chain:

```
PRODUCT TRUTH → PAGE SEMANTICS → PAGE-SPECIFIC COMPOSITION → SHARED GRAMMAR → RENDERED VISUAL
```

Runtime at audit still executed shared clause / shared chrome as page identity.

## Five approved organisms

| Page | Organism |
|------|----------|
| Home | Gravity well + satellites |
| Workspace | Formation body (evidence → void → mass → terminus) |
| Carts | Weighted queue of cart-objects |
| Communication | Lifecycle continuum |
| Settings | Quiet configuration ledger |

## Forbidden reintroductions

- Repeated attention glyph as page identity
- Shared Home/Workspace three-icon clause
- Fake density / fake momentum
- Generic white-card SaaS collapse

## Safe to implement

**YES** — without changing `semantic-visual-model-v1` and without inventing new truth fields.
