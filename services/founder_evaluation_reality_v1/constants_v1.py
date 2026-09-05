# -*- coding: utf-8 -*-
"""Founder Evaluation Reality Coverage V1 — isolated tenant constants."""
from __future__ import annotations

# Fixed zid / store_slug values — never collide with demo or production merchants.
EVAL_PREFIX = "cf_fe_v1_"

STORE_ACTIONABLE = "cf_fe_v1_actionable"
STORE_MEASURING = "cf_fe_v1_measuring"
STORE_INSUFFICIENT = "cf_fe_v1_insufficient"

# Display names (merchant-visible evaluation identity)
NAME_ACTIONABLE = "Founder Evaluation — Actionable"
NAME_MEASURING = "Founder Evaluation — Measuring"
NAME_INSUFFICIENT = "Founder Evaluation — Insufficient"

EMAIL_ACTIONABLE = "founder.eval.actionable@cartflow.local"
EMAIL_MEASURING = "founder.eval.measuring@cartflow.local"
EMAIL_INSUFFICIENT = "founder.eval.insufficient@cartflow.local"

# Shared eval password (local evaluation only; never production)
EVAL_PASSWORD = "FounderEval-V1-Local!"

ALL_EVAL_STORE_SLUGS = frozenset(
    {STORE_ACTIONABLE, STORE_MEASURING, STORE_INSUFFICIENT}
)

# Minimum production-shaped hesitation seeds (reason → count)
# READY: total 20, shipping 12 (≥8 total, ≥5 top, share 0.60)
SEED_ACTIONABLE_REASONS = {"shipping": 12, "price": 5, "thinking": 3}
# PARTIAL: total 5, shipping 3 (≥3 total, ≥2 top; below READY)
SEED_MEASURING_REASONS = {"shipping": 3, "price": 2}
# INSUFFICIENT: no rows
SEED_INSUFFICIENT_REASONS: dict[str, int] = {}
