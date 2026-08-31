# 05 — Canonical verification law

A Merchant UI visual approval is valid only if every line is proven on the **same** browser session that was photographed.

```
CANONICAL ROUTE proven
+ CANONICAL RENDERER proven
+ EXPECTED FEATURE FLAGS proven
+ EXPECTED SHELL proven
+ EXPECTED DATA CONTRACT proven
+ REAL RENDERED OUTPUT reviewed
```

## How to prove each

| Gate | Proof |
|------|--------|
| Route | URL is `/dashboard` (hash `#home` / `#workspace` / …). Not `/`. Not `/preview/*`. |
| Renderer | `X-CartFlow-Merchant-Renderer: merchant_ui_v2` **or** `CARTFLOW_MERCHANT_RUNTIME.renderer_id === "merchant_ui_v2"` |
| Flags | Identity `selection_source` is `default`, `query` (v2), or `review_bind`. Not `cookie` with v1. Workspace flag ON for Workspace reviews. |
| Shell | `cf2-utility` + `cf2-global` + `cf2-ctx` present. No V1 `cf-rail` as the app chrome. |
| Data | Network: `/api/dashboard/summary` and (for Workspace) `/api/cart-workspace/v1/projection` 200. Record `store_slug`. |
| Rendered output | Screenshot of that session after paint. DOM markers for the page under review. |

## Invalid as sole proof

- Server SHA on landing `/`  
- Static file hashes without the HTML that loaded them  
- CSS existence in the repo  
- Living Store JSON session without opening `/dashboard`  
- Local harness on a different flag set, undeclared  
- V1 rollback session  

## Living Store

Allowed as the **data tenant** after `/dev/living-store-home-review`, which must 302 to `/dashboard#home` and force V2. The review URL itself is not the renderer.
