# -*- coding: utf-8 -*-
from __future__ import annotations

from services.store_widget_customization import (
    apply_widget_customization_from_body,
    normalize_widget_primary_hex,
    widget_customization_fields_for_api,
)


def test_normalize_hex_three_digit_expands() -> None:
    assert normalize_widget_primary_hex("#abc") == "#AABBCC"


def test_normalize_hex_invalid_fallback() -> None:
    assert normalize_widget_primary_hex("not-a-color") == "#6C5CE7"


def test_widget_customization_defaults_when_row_none() -> None:
    d = widget_customization_fields_for_api(None)
    assert d["widget_name"] == "مساعد المتجر"
    assert d["widget_primary_color"] == "#6C5CE7"
    assert d["widget_style"] == "modern"


def test_apply_partial_keeps_other_widget_fields() -> None:
    class _Row:
        widget_name = "مساعد المتجر"
        widget_primary_color = "#6C5CE7"
        widget_style = "modern"

    r = _Row()
    apply_widget_customization_from_body(r, {"widget_style": "bold"})
    assert r.widget_style == "bold"
    assert r.widget_name == "مساعد المتجر"


def test_apply_widget_name_empty_resets_default() -> None:
    class _Row:
        widget_name = "قديم"
        widget_primary_color = "#6C5CE7"
        widget_style = "modern"

    r = _Row()
    apply_widget_customization_from_body(r, {"widget_name": "   "})
    assert r.widget_name == "مساعد المتجر"


def test_invalid_style_in_body_ignored() -> None:
    class _Row:
        widget_name = "مساعد المتجر"
        widget_primary_color = "#6C5CE7"
        widget_style = "minimal"

    r = _Row()
    apply_widget_customization_from_body(r, {"widget_style": "fancy"})
    assert r.widget_style == "minimal"
