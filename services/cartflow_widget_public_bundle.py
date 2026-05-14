# -*- coding: utf-8 -*-
"""حقول القوالب/الاسترجاع المندمجة لاستجابات الودجيت العامة (‎ready‎ / ‎public-config‎)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from services.cartflow_widget_recovery_gate import (
    cartflow_widget_recovery_gate_fields_for_api,
)
from services.cartflow_widget_trigger_settings import widget_trigger_config_for_api
from services.store_reason_templates import reason_templates_fields_for_api
from services.store_template_control import (
    exit_intent_template_fields_for_api,
    template_control_fields_for_api,
)
from services.store_widget_customization import widget_customization_fields_for_api
from services.vip_cart import vip_cart_threshold_fields_for_api


def merge_widget_template_bundle_from_store_row(
    row: Optional[Any],
) -> Dict[str, Any]:
    tpl: Dict[str, Any] = {}
    tpl.update(template_control_fields_for_api(row))
    tpl.update(exit_intent_template_fields_for_api(row))
    tpl.update(widget_customization_fields_for_api(row))
    tpl.update(vip_cart_threshold_fields_for_api(row))
    tpl.update(cartflow_widget_recovery_gate_fields_for_api(row))
    tpl.update(widget_trigger_config_for_api(row))
    tpl.update(reason_templates_fields_for_api(row))
    return tpl
