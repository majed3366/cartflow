# Request concurrency governance

Rules now in force:

- Inactive V2 surfaces perform no startup work.
- Same-surface init is one-shot unless forced (`SURFACE_PRODUCT_INIT`).
- Settings first-load remains sequential and QueuePool-remediated.
- Heavy merchant reads share a global semaphore (4) and per-route cap (2).
- Optional work must lose to health/auth (health probe refuses checkout when pool is HIGH/CRITICAL).
- Communication `Promise.all` of three is allowed only because Communication is the sole active surface.

Not implemented (not required by measured findings): retry jitter rewrite, frontend request coalescing beyond existing lazy init.
