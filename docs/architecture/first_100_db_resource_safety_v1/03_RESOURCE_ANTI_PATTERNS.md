# Platform-wide anti-patterns

Common architectural causes (not isolated bugs):

**A.** Request-scoped session held from first checkout until middleware `finally`. This is the dominant HTTP pattern.

**B.** External HTTP (Meta, Zid, Resend) while the scoped connection remains checked out. Highest-impact: `send_whatsapp_message` and `zid_client`.

**C.** Enrich/compose CPU on workspace fallback while the session stays open.

**D/E.** Unbounded or over-fetched bulk reads on live carts/messages (`RecoverySchedule.all()`, `MessageLog` all phones, followup reply history `.all()`, messages over-fetch 200 for a 40-row page).

**F/G.** Nested/background scoped sessions exist; `isolated_db_session` unused.

**J.** Inactive V2 surfaces already gated at `58a82f3` (must remain).

**K.** Admin/dev/review share the same API pool.

**L.** Auth middleware checks out early on every cookied request.

The shared cause: **checkout is cheap to start and expensive to keep.** The pool is 5+5. Two merchant tabs plus Communication `Promise.all` of three live reads can consume most of the budget.
