# CEO Reality Validation Walkthrough (Production)

**Host:** `https://smartreplyai.net`  
**Store:** `demo` only  
**Account:** Living Store Review (issued by the review URL — not a normal signup login)

**Constitutional rule:** Do not review Home / Workspace / take product decisions until Identity Certification shows:

```text
Status = CONSISTENT
CEO_REVIEW_SAFE = TRUE
```

---

## What you need

- A normal browser (Chrome / Edge / Safari).
- Access to `https://smartreplyai.net`.
- **No SSH. No terminal. No Python.**

If any URL below returns **404**, the Identity Certification / console deploy is not live yet — stop and ask for deploy of Reality Validation Identity Certification V1. Do not review UI without certification.

---

## Exact URLs

| Step | Method | URL |
|------|--------|-----|
| CEO console (recommended start) | GET | https://smartreplyai.net/dev/reality-validation-console |
| Trigger Living Store | POST (via console button) | https://smartreplyai.net/dev/living-store-reality-run |
| Poll Living Store status | GET | https://smartreplyai.net/dev/living-store-reality-status |
| Bind browser to `demo` | GET | https://smartreplyai.net/dev/living-store-home-review |
| Identity Certification (HTML) | GET | https://smartreplyai.net/dev/reality-validation-context?store=demo&format=html |
| Identity Certification (JSON) | GET | https://smartreplyai.net/dev/reality-validation-context?store=demo |
| Home | after review bind | https://smartreplyai.net/dashboard#home |
| Decision Workspace | after review bind | https://smartreplyai.net/dashboard#workspace |
| Products | after review bind | https://smartreplyai.net/dashboard#products |
| Carts | after review bind | https://smartreplyai.net/dashboard#carts |
| Communication | after review bind | https://smartreplyai.net/dashboard#communication |

---

## Login / store identity

| Item | Value |
|------|--------|
| How you “log in” | Open **GET** `/dev/living-store-home-review` — it sets the merchant cookie and redirects to Home |
| Account email (system) | `cf.living.store.review@smartreplyai.net` |
| Password | **Do not use `/login`.** Password is rotated each session issue. The review URL is the login. |
| `store_slug` | **`demo`** (must appear on certification page) |

---

## Execution order (do this exact sequence)

### Step 1 — Open the CEO console

Open:

https://smartreplyai.net/dev/reality-validation-console

You should see a page titled **Reality Validation Console** with a **Run Living Store** button.

### Step 2 — Run Living Store on Production

Click:

**Run Living Store**

What happens:

- Browser sends `POST /dev/living-store-reality-run`
- Production database store `demo` is seeded (wall-clock Living Store profile)
- Job runs in the background (often several minutes)

### Step 3 — Wait until completion

On the same console page, wait until status shows:

- `status: completed`
- `ok: true`
- A non-empty `simulation_run_id` like `srs_…`

You may also open:

https://smartreplyai.net/dev/living-store-reality-status

Refresh until `job.status` is `completed` (not `running` / `observing` / `failed`).

If `failed` — stop. Do not review. Share the JSON error with engineering.

### Step 4 — Bind this browser to Living Store `demo`

Open:

https://smartreplyai.net/dev/living-store-home-review

Expected:

- Cookie set for Living Store Review merchant
- Redirect to `https://smartreplyai.net/dashboard#home`
- Session reads **`store_slug=demo`**

Keep this browser tab/window. Do not switch to another merchant account in the same browser profile.

### Step 5 — Open Identity Certification (mandatory)

In the **same browser** (same cookies), open:

https://smartreplyai.net/dev/reality-validation-context?store=demo&format=html

### Step 6 — Verify certification (hard gate)

On that page you must see:

```text
Status = CONSISTENT
CEO_REVIEW_SAFE = TRUE
```

Also confirm matrix rows show:

- Environment ✔ Production  
- Database ✔ Production  
- Store Slug ✔ demo  
- Merchant Session ✔ demo  
- Simulation Run ✔ srs_…  
- Home / Workspace / Products / Carts / Communication ✔ same simulation  

**Take a screenshot of this page now.**  
If `CEO_REVIEW_SAFE = FALSE` — **stop**. Do not open Home for product review. Fix reasons listed on the page (or re-run Steps 2–5).

### Step 7 — Open Home

https://smartreplyai.net/dashboard#home

Capture screenshots only after Step 6 passed.

### Step 8 — Open Decision Workspace

https://smartreplyai.net/dashboard#workspace

Capture screenshots.

### Step 9 (optional) — Other surfaces (same session)

- Products: https://smartreplyai.net/dashboard#products  
- Carts: https://smartreplyai.net/dashboard#carts  
- Communication: https://smartreplyai.net/dashboard#communication  

---

## Usability gaps (honest)

| Gap | Today | CEO impact | Production-accessible alternative |
|-----|--------|------------|-----------------------------------|
| Living Store trigger is **POST**, not a normal link | `POST /dev/living-store-reality-run` | Opening the URL alone does nothing / may 405 | **Use the console** (`/dev/reality-validation-console`) — one click. Do **not** use SSH/curl. |
| No password login for review account | Password rotates; primary bind is via cookie URL | `/login` with a remembered password will fail or bind wrong store | Always use `/dev/living-store-home-review` |
| Certification / console must be **deployed** | Code may be on a feature branch | 404 → cannot certify | Deploy Identity Certification V1 before any CEO review |
| In-memory job status resets on process restart | Status endpoint may show idle after deploy/restart even if DB has data | Confusing “is it done?” | Prefer `simulation_run_id` on certification page + DB-backed run; re-run Living Store if unsure |
| SSH / Railway / Python | **Not required** for this workflow | — | If someone asks you to SSH, refuse — use the console |

---

## Forbidden (invalidates the review)

- Reviewing Home without `CEO_REVIEW_SAFE = TRUE`
- Logging into a signup merchant instead of Living Store Review
- Using Local / SQLite / developer laptop as “Living Store”
- Running Python scripts or Railway shell as the CEO path

---

## One-page cheat sheet

1. https://smartreplyai.net/dev/reality-validation-console → **Run Living Store** → wait `completed`  
2. https://smartreplyai.net/dev/living-store-home-review  
3. https://smartreplyai.net/dev/reality-validation-context?store=demo&format=html → screenshot **CONSISTENT + CEO_REVIEW_SAFE = TRUE**  
4. https://smartreplyai.net/dashboard#home  
5. https://smartreplyai.net/dashboard#workspace  
