# Future migration law

Frozen by V2.1. Tests: `tests/test_migration_history_reconstruction_v2_1.py` (`FutureMigrationLawTests`).

1. **Alembic is the sole production schema authority.**
2. **Production `create_all` is disabled.**
3. **Every schema mutation requires a revision.**
4. **Every revision must attach to a real present parent.**
5. **Fresh PostgreSQL replay is required** before treating a history change as proven. SQLite is a helper only.
6. **Upgrade-from-current-production-state verification is required** before any production reconciliation (this task does not run it).
7. **Schema drift must be classified** (`MATCH` / `EXPECTED_DEPRECATED_DRIFT` / `UNRESOLVED_DRIFT`) before deploy.
8. **No runtime helper may silently manufacture missing schema.** `schema_mutation_permitted()` aliases `create_all_permitted()`.
9. **Deprecated objects require explicit disposition.** `commercial_decision_commitments` = DEPRECATE.
10. **Authoritative migration proof uses PostgreSQL.**

Do not execute production stamp or upgrade from this document.
