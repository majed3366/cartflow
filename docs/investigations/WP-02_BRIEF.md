# Work Package Brief — WP-2

| Field | Value |
|-------|-------|
| Investigation ID | INV-001 |
| Work Package ID | WP-2 |
| Title | Query Time Context |
| Branch | `feature/inv001-wp2` |
| Depends on | WP-1 approved (`4ebb43f`) |
| Date opened (UTC) | 2026-07-16 |

## Objective

Governed Query Time Context model + safe propagation (request/worker/test/replay/simulation) without migrating merchant consumers.

## Out of scope

Filtering (WP-3), consumer migration, Simulation Engine bind (WP-10), significant `main.py` logic.

## Rollback

Revert WP-2 commits; preserve WP-1 package. Remove middleware registration line if present.
