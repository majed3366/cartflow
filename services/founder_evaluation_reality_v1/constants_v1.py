# -*- coding: utf-8 -*-
"""Founder Evaluation Reality Coverage V1 — isolated tenant constants."""
from __future__ import annotations

# Fixed zid / store_slug values — never collide with demo or production merchants.
EVAL_PREFIX = "cf_fe_v1_"

STORE_ACTIONABLE = "cf_fe_v1_actionable"
STORE_MEASURING = "cf_fe_v1_measuring"
STORE_INSUFFICIENT = "cf_fe_v1_insufficient"
STORE_PRICE = "cf_fe_v1_price"
STORE_QUALITY = "cf_fe_v1_quality"
STORE_FOCUS = "cf_fe_v1_focus"

# Display names (merchant-visible evaluation identity)
NAME_ACTIONABLE = "Founder Evaluation — Actionable"
NAME_MEASURING = "Founder Evaluation — Measuring"
NAME_INSUFFICIENT = "Founder Evaluation — Insufficient"
NAME_PRICE = "Founder Evaluation — Price Hesitation"
NAME_QUALITY = "Founder Evaluation — Product Confidence"
NAME_FOCUS = "Founder Evaluation — Product Focus"

EMAIL_ACTIONABLE = "founder.eval.actionable@cartflow.local"
EMAIL_MEASURING = "founder.eval.measuring@cartflow.local"
EMAIL_INSUFFICIENT = "founder.eval.insufficient@cartflow.local"
EMAIL_PRICE = "founder.eval.price@cartflow.local"
EMAIL_QUALITY = "founder.eval.quality@cartflow.local"
EMAIL_FOCUS = "founder.eval.focus@cartflow.local"

# Shared eval password (local evaluation only; never production)
EVAL_PASSWORD = "FounderEval-V1-Local!"

ALL_EVAL_STORE_SLUGS = frozenset(
    {
        STORE_ACTIONABLE,
        STORE_MEASURING,
        STORE_INSUFFICIENT,
        STORE_PRICE,
        STORE_QUALITY,
        STORE_FOCUS,
    }
)

# Minimum production-shaped hesitation seeds (reason → count)
# READY: total 20, shipping 12 (≥8 total, ≥5 top, share 0.60)
SEED_ACTIONABLE_REASONS = {"shipping": 12, "price": 5, "thinking": 3}
# PARTIAL: total 5, shipping 3 (≥3 total, ≥2 top; below READY)
SEED_MEASURING_REASONS = {"shipping": 3, "price": 2}
# INSUFFICIENT: no rows
SEED_INSUFFICIENT_REASONS: dict[str, int] = {}
# READY price primary: total 20, price 12 (share 0.60) — Commercial Mission V2
SEED_PRICE_REASONS = {"price": 12, "shipping": 5, "thinking": 3}
# READY product_confidence primary (Merchandising Slice V1)
SEED_QUALITY_REASONS = {"quality": 20, "shipping": 3, "thinking": 2}
# Shipping primary + quality+warranty pool READY → product_opportunity_focus secondary
SEED_FOCUS_REASONS = {"shipping": 12, "quality": 6, "warranty": 6}
# Dual trust → product_opportunity_focus primary (both quality & warranty ≥3)
SEED_FOCUS_PRIMARY_REASONS = {"quality": 8, "warranty": 8, "shipping": 3}
# Price active + quality secondary for portfolio conflict shots
SEED_PRICE_QUALITY_REASONS = {"price": 12, "quality": 8, "shipping": 3}
