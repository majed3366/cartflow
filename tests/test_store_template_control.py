# -*- coding: utf-8 -*-
from __future__ import annotations

from services.store_template_control import (
    apply_template_control_from_body,
    template_control_fields_for_api,
)


class _Row:
    template_mode = "preset"
    template_tone = "friendly"
    template_custom_text = None


def test_template_control_api_defaults_when_row_none() -> None:
    d = template_control_fields_for_api(None)
    assert d == {
        "template_mode": "preset",
        "template_tone": "friendly",
        "template_custom_text": "",
    }


def test_template_control_partial_post_keeps_other_fields() -> None:
    r = _Row()
    apply_template_control_from_body(r, {"template_tone": "formal"})
    assert r.template_tone == "formal"
    assert r.template_mode == "preset"


def test_template_control_custom_text_cleared_when_empty_string() -> None:
    r = _Row()
    r.template_custom_text = "old"
    apply_template_control_from_body(r, {"template_custom_text": "   "})
    assert r.template_custom_text is None


def test_template_control_invalid_tone_in_body_ignored() -> None:
    r = _Row()
    apply_template_control_from_body(r, {"template_tone": "lol"})
    assert r.template_tone == "friendly"


def test_template_control_fields_normalize_unknown_columns() -> None:
    class Bad:
        template_mode = "weird"
        template_tone = "x"
        template_custom_text = None

    d = template_control_fields_for_api(Bad())
    assert d["template_mode"] == "preset"
    assert d["template_tone"] == "friendly"
