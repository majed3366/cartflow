# -*- coding: utf-8 -*-
from __future__ import annotations

from services.store_widget_customization import (
    apply_widget_customization_from_body,
    canonical_widget_name_on_row,
    normalize_widget_primary_hex,
    reconcile_widget_name_columns,
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


def test_canonical_prefers_display_name_when_widget_name_is_default() -> None:
    class _Row:
        widget_name = "مساعد المتجر"
        widget_display_name = "CARTFLOW"
        widget_primary_color = "#6C5CE7"
        widget_style = "modern"

    r = _Row()
    assert canonical_widget_name_on_row(r) == "CARTFLOW"
    d = widget_customization_fields_for_api(r)
    assert d["widget_name"] == "CARTFLOW"
    reconcile_widget_name_columns(r)
    assert r.widget_name == "CARTFLOW"


def test_invalid_style_in_body_ignored() -> None:
    class _Row:
        widget_name = "مساعد المتجر"
        widget_primary_color = "#6C5CE7"
        widget_style = "minimal"

    r = _Row()
    apply_widget_customization_from_body(r, {"widget_style": "fancy"})
    assert r.widget_style == "minimal"
