# Mobile Composition

Breakpoint: `max-width: 1023px`.

Sequence:

1. Queue (with compact orientation + filters)
2. Select cart → detail replaces queue
3. Back → queue, same filter and selected key

Rules:

- no side-by-side master-detail
- no compressed desktop table
- no horizontal page overflow (`overflow-wrap`, `min-width: 0`, document `overflow-x` probe)
- primary action sticky and full-width on detail
- timeline behind `<details>` so it does not bury the action

Desktop (`min-width: 1024px`) keeps master-detail for speed.
