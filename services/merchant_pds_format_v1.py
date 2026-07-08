# -*- coding: utf-8 -*-
"""Merchant PDS format helpers — certified compact currency (presentation only)."""
from __future__ import annotations

from markupsafe import Markup, escape


def _merchant_sar_number(amount) -> int | None:
    if amount is None:
        return None
    if isinstance(amount, str):
        cleaned = amount.replace(",", "").replace("٬", "").strip()
        if not cleaned or cleaned in {"—", "-"}:
            return None
        if cleaned in {"…", "..."}:
            return None
        try:
            return round(float(cleaned))
        except ValueError:
            return None
    try:
        return round(float(amount))
    except (TypeError, ValueError):
        return None


def format_merchant_sar(amount) -> str:
    """Certified compact dashboard currency: ``SR 449``."""
    if isinstance(amount, str) and amount.strip() in {"…", "..."}:
        return amount.strip()
    n = _merchant_sar_number(amount)
    if n is None:
        return ""
    return f"SR {n:,}"


def format_merchant_sar_html(amount) -> Markup:
    text = format_merchant_sar(amount)
    if not text:
        return Markup("")
    return Markup(
        '<span class="cf-currency-atom cftyp-currency" data-cf-currency="1" dir="ltr">'
        f"{escape(text)}"
        "</span>"
    )
