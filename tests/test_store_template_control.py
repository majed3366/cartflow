# -*- coding: utf-8 -*-
from __future__ import annotations

from services.store_template_control import (
    apply_exit_intent_template_control_from_body,
    apply_template_control_from_body,
    exit_intent_template_fields_for_api,
    template_control_fields_for_api,
)


class _RowExit:
    exit_intent_template_mode = "preset"
    exit_intent_template_tone = "friendly"
    exit_intent_custom_text = None


def test_exit_intent_fields_defaults() -> None:
    d = exit_intent_template_fields_for_api(None)
    assert d["exit_intent_template_mode"] == "preset"
    assert d["exit_intent_custom_text"] == ""


def test_exit_intent_apply_partial() -> None:
    r = _RowExit()
    apply_exit_intent_template_control_from_body(r, {"exit_intent_template_tone": "sales"})
    assert r.exit_intent_template_tone == "sales"
    assert r.exit_intent_template_mode == "preset"


def test_exit_intent_fields_invalid_normalized() -> None:
    class Bad:
        exit_intent_template_mode = "x"
        exit_intent_template_tone = "y"
        exit_intent_custom_text = None

    d = exit_intent_template_fields_for_api(Bad())
    assert d["exit_intent_template_mode"] == "preset"


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
