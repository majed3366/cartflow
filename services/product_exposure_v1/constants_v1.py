# -*- coding: utf-8 -*-
"""Product Exposure V1 constants — platform-neutral contract."""
from __future__ import annotations

import re

TRUTH_VERSION_EXPOSURE_V1 = "exposure_v1"
SOURCE_STOREFRONT_WIDGET_V1 = "storefront_widget_v1"
PAGE_CONTEXT_PDP = "pdp"
EVENT_SOURCE_CARTFLOW_STOREFRONT = "cartflow_storefront"
IDENTITY_SOURCE_STOREFRONT_RUNTIME = "storefront_runtime"

PAYLOAD_MAX_BYTES = 2048
COMMERCIAL_WINDOW_SECONDS = 1800
CLOCK_PAST_SECONDS = 15 * 60
CLOCK_FUTURE_SECONDS = 120

RAW_RETENTION_DAYS = 30
FACT_RETENTION_DAYS = 400

SEAL_BATCH_MAX = 20
RAW_DELETE_MAX = 200
FACT_DELETE_MAX = 50

RATE_ORIGIN_PER_MIN = 120
RATE_SESSION_PER_MIN = 20
RATE_STORE_PER_MIN = 600

EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
SESSION_ID_RE = re.compile(r"^s_[A-Za-z0-9-]{8,64}$")
STORE_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
PRODUCT_ID_RE = re.compile(r"^[^\s]{1,128}$")

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "event_id",
        "store_slug",
        "product_id",
        "session_id",
        "occurred_at",
        "source",
        "page_context",
        "truth_version",
        "referrer_domain",
        "claimed_utm_source",
        "claimed_utm_medium",
        "claimed_utm_campaign",
    }
)

REQUIRED_PAYLOAD_KEYS = frozenset(
    {
        "event_id",
        "store_slug",
        "product_id",
        "session_id",
        "occurred_at",
        "source",
        "page_context",
        "truth_version",
    }
)

REASON_PERSISTED = "persisted"
REASON_IDEMPOTENT_REPLAY = "idempotent_replay"
REASON_COMMERCIAL_DEDUPE = "commercial_dedupe"
