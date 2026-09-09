# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1 — SQL shape

Dialect: SQLite (tests) uses `GROUP_CONCAT`; PostgreSQL uses `string_agg`. Lab vs normal is **two SQL bodies**, one execute each. Normal body must not contain `product_signal_events`.

Binds: `:slug`, `:store_id`, `:max_products` (40), `:max_cart_pairs` (400), `:lab_source`, `:lab_signal` (lab body only).

```sql
WITH catalog AS (
  -- store_slug = :slug
  -- pid = COALESCE(NULLIF(TRIM(product_id),''), TRIM(stable_identity_key))
  -- ORDER BY last_synced_at DESC LIMIT :max_products
),
cart_pairs AS (
  -- unique (product_id, cart_id) from cart_line_snapshots
  -- LIMIT :max_cart_pairs
),
carts AS (
  -- COUNT(*) cart_count, SUM(abandoned_carts.cart_value)
  -- JOIN on zid_cart_id; store_id gated when :store_id != 0
  -- GROUP BY product_id
),
universe AS (
  SELECT product_id FROM catalog
  UNION
  SELECT product_id FROM cart_pairs
),
purchases AS (
  -- COUNT(*), SUM(unit_price * quantity) GROUP BY product_id
  -- product_id IN universe
),
hes_counts AS (
  -- COUNT(*) GROUP BY product_id, LOWER(TRIM(reason))
  -- product_id IN universe
),
hesitation AS (
  -- GROUP_CONCAT / string_agg reason + count per product
)
-- LAB ONLY:
-- visits AS (COUNT(*) FROM product_signal_events
--   source = lab synthetic, signal_type = product_viewed
--   product_id IN universe GROUP BY product_id)
,
joined AS (
  catalog rows
  UNION ALL
  cart-only product_ids not in catalog
)
SELECT catalog fields,
       COALESCE(cart_count,0), COALESCE(cart_value,0),
       COALESCE(purchase_count,0), COALESCE(revenue,0),
       reasons_blob,
       visit_count  -- NULL on normal SQL
FROM joined
LEFT JOIN carts / purchases / hesitation [/ visits]
ORDER BY cart_only, last_synced_at DESC, product_id
LIMIT :max_products
```

Row-multiplication proof: fact tables never join each other as raw rows. Each is grouped to one row per `product_id` first.
