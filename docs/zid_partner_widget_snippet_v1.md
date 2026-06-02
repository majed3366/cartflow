# Zid Partner — CartFlow storefront widget snippet (v1)

Official Zid injection for app partners is **Custom Snippets** in the Partner Dashboard (not a per-store REST install API). After a merchant installs CartFlow and completes OAuth, Zid injects the approved snippet on that store’s storefront.

## One-time partner setup

1. Partner Dashboard → your app → **General Settings** → **Add Snippet**.
2. Placement: **header** (global).
3. Paste (replace `LOADER_ORIGIN` with production, e.g. `https://smartreplyai.net`):

```html
<script>
(function (w, d, u) {
  var sid = "";
  try {
    if (w.store && w.store.id) sid = String(w.store.id);
    else if (w.zid && w.zid.store && w.zid.store.id) sid = String(w.zid.store.id);
  } catch (e) {}
  var s = d.createElement("script");
  s.async = true;
  s.src = u;
  if (sid) s.setAttribute("data-store", sid);
  d.head.appendChild(s);
})(window, document, "LOADER_ORIGIN/static/widget_loader.js");
</script>
```

4. Submit for Zid review/approval.

## Server env (CartFlow)

| Variable | Purpose |
|----------|---------|
| `ZID_API_AUTHORIZATION` | Partner project token — `GET https://api.zid.sa/v1/scripts` manifest check |
| `ZID_PARTNER_WIDGET_SNIPPET_APPROVED` | Set `1` after snippet is approved (staging if manifest API empty) |
| `CARTFLOW_PUBLIC_BASE_URL` | Public origin for loader URL in verification |

## Runtime behavior

- On OAuth success: `[ZID WIDGET INSTALL START]` → manifest/storefront verify → `installing` / `installed` / `unsupported`.
- Storefront loader: `[WIDGET STOREFRONT LOAD]` + `POST /api/storefront/widget-seen` updates `widget_last_seen_at`.
- Merchant dashboard **ربط المتجر** card shows widget status (no manual paste as default path).
