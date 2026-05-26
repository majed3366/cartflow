# -*- coding: utf-8 -*-
"""
Merchant Activation v1 — funnel, scoped demo test path, milestones (read-only).

Does not change recovery scheduling, sends, delays, purchase truth, or queue workers.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional
from urllib.parse import quote

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness
from services.recovery_store_lookup import is_widget_recovery_zid

log = logging.getLogger("cartflow")

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,127}$")


@dataclass
class ActivationDemoResolution:
    widget_store_slug: str = "demo"
    demo_cart_key: str = "demo_cart"
    is_merchant_activation: bool = False
    merchant_store_slug: str = ""
    banner_ar: str = ""
    denied: bool = False
    deny_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivationMilestone:
    milestone_id: str
    title_ar: str
    done: bool
    hint_ar: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivationSummaryState:
    state_id: str
    label_ar: str
    reached: bool
    current: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MerchantActivationPayload:
    milestones: list[ActivationMilestone] = field(default_factory=list)
    summary_states: list[ActivationSummaryState] = field(default_factory=list)
    current_state_id: str = "no_carts"
    current_state_label_ar: str = "لم تُسجَّل سلال بعد"
    next_step_ar: str = ""
    test_store_url: str = ""
    test_widget_path: str = "/dashboard/test-widget"
    delay_hint_ar: str = ""
    activation_working: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestones": [m.to_dict() for m in self.milestones],
            "summary_states": [s.to_dict() for s in self.summary_states],
            "current_state_id": self.current_state_id,
            "current_state_label_ar": self.current_state_label_ar,
            "next_step_ar": self.next_step_ar,
            "test_store_url": self.test_store_url,
            "test_widget_path": self.test_widget_path,
            "delay_hint_ar": self.delay_hint_ar,
            "activation_working": self.activation_working,
        }


def sanitize_activation_store_slug(raw: str | None) -> str:
    s = (raw or "").strip()
    if not s or not _SLUG_RE.match(s):
        return ""
    return s[:128]


def _public_demo_slug(slug: str) -> bool:
    return slug.casefold() in ("demo", "demo2")


def _activation_demo_resolution_for_owner(
    owner_slug: str,
    *,
    ma_flag: bool,
    requested: str = "",
) -> ActivationDemoResolution:
    out = ActivationDemoResolution()
    out.widget_store_slug = owner_slug
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", owner_slug)[:64]
    out.demo_cart_key = f"ma_{safe}_cart"
    out.is_merchant_activation = bool(ma_flag)
    out.merchant_store_slug = owner_slug
    out.banner_ar = (
        f"أنت تختبر متجرك ({owner_slug}) — الأحداث تظهر في لوحة التحكم الخاصة بك."
    )
    if requested and requested != owner_slug and not _public_demo_slug(requested):
        out.denied = True
        out.deny_reason = "store_slug_redirected_to_owner"
    return out


def resolve_activation_demo_for_request(
    request: Any,
    *,
    cookies: Optional[dict[str, str]] = None,
) -> ActivationDemoResolution:
    """
  Resolve widget ``data-store`` for ``/demo/store``.

  - ``demo`` / ``demo2``: public sandbox (unchanged) when not merchant activation.
  - Merchant activation: always authenticated merchant ``zid_store_id`` — never ``demo``.
  """
    out = ActivationDemoResolution()
    try:
        qp = getattr(request, "query_params", None)
    except Exception:  # noqa: BLE001
        qp = None
    requested = ""
    if qp is not None:
        requested = sanitize_activation_store_slug(
            qp.get("store_slug") or qp.get("store")
        )
    ma_flag = False
    if qp is not None:
        ma_flag = str(qp.get("merchant_activation") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    ck = cookies if cookies is not None else {}
    if not ck:
        try:
            ck = dict(getattr(request, "cookies", {}) or {})
        except Exception:  # noqa: BLE001
            ck = {}
    from services.merchant_onboarding_store import resolve_merchant_onboarding_store
    from services.merchant_test_widget_store_v1 import (  # noqa: PLC0415
        merchant_authenticated_store_slug,
    )

    owner_slug = merchant_authenticated_store_slug(cookies=ck) or ""

    if ma_flag:
        if not owner_slug:
            out.denied = True
            out.deny_reason = "auth_required"
            return out
        return _activation_demo_resolution_for_owner(
            owner_slug, ma_flag=True, requested=requested
        )

    if not requested:
        out.widget_store_slug = "demo"
        out.demo_cart_key = "demo_cart"
        return out

    if _public_demo_slug(requested):
        out.widget_store_slug = requested
        out.demo_cart_key = "demo2_cart" if requested == "demo2" else "demo_cart"
        return out

    store, meta = resolve_merchant_onboarding_store(cookies=ck)
    owner_slug = (
        (getattr(store, "zid_store_id", None) or "").strip() if store is not None else ""
    )
    if store is None or not owner_slug or owner_slug != requested:
        out.denied = True
        out.deny_reason = "store_slug_not_owned"
        out.widget_store_slug = "demo"
        out.demo_cart_key = "demo_cart"
        return out

    if is_widget_recovery_zid(owner_slug):
        out.denied = True
        out.deny_reason = "system_slug"
        out.widget_store_slug = "demo"
        out.demo_cart_key = "demo_cart"
        return out

    return _activation_demo_resolution_for_owner(
        owner_slug, ma_flag=False, requested=requested
    )


def merchant_activation_demo_nav_base(resolution: ActivationDemoResolution) -> str:
    if resolution.is_merchant_activation and resolution.merchant_store_slug:
        q = quote(resolution.merchant_store_slug, safe="")
        return f"/demo/store?store_slug={q}&merchant_activation=1"
    return "/demo/store"


def merchant_activation_test_store_url(store_slug: str) -> str:
    slug = sanitize_activation_store_slug(store_slug)
    if not slug:
        return "/demo/store"
    q = quote(slug, safe="")
    return f"/demo/store?store_slug={q}&merchant_activation=1&reset_demo=1"


def _first_reason_captured_readonly(store: Any) -> bool:
    slug = (getattr(store, "zid_store_id", None) or "").strip()[:255]
    if not slug:
        return False
    try:
        from extensions import db  # noqa: PLC0415
        from models import CartRecoveryReason  # noqa: PLC0415
        from sqlalchemy import exists  # noqa: PLC0415

        return bool(
            db.session.query(
                exists().where(CartRecoveryReason.store_slug == slug)
            ).scalar()
        )
    except Exception:  # noqa: BLE001
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return False


def _recovery_delay_hint_ar(store: Optional[Any]) -> str:
    if store is None:
        return ""
    try:
        delay = int(getattr(store, "recovery_delay", 2) or 2)
    except (TypeError, ValueError):
        delay = 2
    unit = (getattr(store, "recovery_delay_unit", None) or "minutes").strip().lower()
    if unit.startswith("hour") or unit in ("h", "hours"):
        return f"الإرسال متوقع خلال نحو {delay} ساعة حسب مهلة الاسترجاع."
    if unit.startswith("sec"):
        return f"الإرسال متوقع خلال نحو {delay} ثانية حسب مهلة الاسترجاع."
    return f"الإرسال متوقع خلال نحو {delay} دقيقة حسب مهلة الاسترجاع."


def _activation_milestone_flags_for_layout(
    store: Optional[Any],
    activation_out: Mapping[str, Any],
) -> tuple[bool, bool, bool, bool]:
    """Milestone booleans for home layout (readiness dict), not the API list shape."""
    ev = evaluate_onboarding_readiness(store) if store is not None else {}
    ms = dict(ev.get("milestones") or {})
    first_cart = bool(ms.get("first_cart_detected"))
    first_scheduled = bool(ms.get("first_recovery_scheduled"))
    first_sent = bool(ms.get("first_whatsapp_sent"))
    first_recovered = bool(ms.get("first_recovered_cart"))

    raw = activation_out.get("milestones")
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            mid = str(item.get("milestone_id") or "")
            done = bool(item.get("done"))
            if mid == "first_cart":
                first_cart = first_cart or done
            elif mid == "first_scheduled":
                first_scheduled = first_scheduled or done
            elif mid == "first_message":
                first_sent = first_sent or done
    return first_cart, first_scheduled, first_sent, first_recovered


def build_merchant_activation_payload(
    store: Optional[Any] = None,
    *,
    cookies: Optional[dict[str, str]] = None,
) -> MerchantActivationPayload:
    ev = evaluate_onboarding_readiness(store) if store is not None else {}
    ms = dict(ev.get("milestones") or {})
    slug = (getattr(store, "zid_store_id", None) or "").strip() if store else ""

    first_cart = bool(ms.get("first_cart_detected"))
    first_reason = _first_reason_captured_readonly(store) if store is not None else False
    first_scheduled = bool(ms.get("first_recovery_scheduled"))
    first_sent = bool(ms.get("first_whatsapp_sent"))
    first_recovered = bool(ms.get("first_recovered_cart"))

    milestones = [
        ActivationMilestone(
            "first_cart",
            "أول سلة مُسجَّلة",
            first_cart,
            "تظهر في قائمة السلال بعد تجربة المتجر.",
        ),
        ActivationMilestone(
            "first_reason",
            "سبب التردد",
            first_reason,
            "اختر سبباً من نافذة الودجت أثناء التجربة.",
        ),
        ActivationMilestone(
            "first_scheduled",
            "جدولة الاسترجاع",
            first_scheduled,
            "يعني أن النظام استلم السلة وخطط للمتابعة.",
        ),
        ActivationMilestone(
            "first_message",
            "أول رسالة استرجاع",
            first_sent,
            "في وضع التجربة قد تكون رسالة تجريبية (Sandbox).",
        ),
    ]

    summary_defs = [
        ("no_carts", "بانتظار أول سلة"),
        ("first_cart", "أول سلة"),
        ("recovery_active", "الاسترجاع نشط"),
        ("first_message", "أول رسالة"),
        ("recovery_success", "نجاح استرداد"),
    ]

    if first_recovered:
        current_id = "recovery_success"
    elif first_sent:
        current_id = "first_message"
    elif first_scheduled or (first_cart and first_reason):
        current_id = "recovery_active"
    elif first_cart:
        current_id = "first_cart"
    else:
        current_id = "no_carts"

    order = [x[0] for x in summary_defs]
    cur_idx = order.index(current_id) if current_id in order else 0

    summary_states: list[ActivationSummaryState] = []
    for i, (sid, label) in enumerate(summary_defs):
        summary_states.append(
            ActivationSummaryState(
                state_id=sid,
                label_ar=label,
                reached=i <= cur_idx,
                current=(sid == current_id),
            )
        )

    current_label = summary_defs[cur_idx][1] if cur_idx < len(summary_defs) else ""

    if not slug:
        next_step = "أكمل إنشاء الحساب ثم جرّب متجر الاختبار."
        test_url = "/demo/store"
    elif not first_cart:
        next_step = "افتح متجر الاختبار، أضف منتجاً، وأدخل رقم جوال عند طلب الودجت."
        test_url = merchant_activation_test_store_url(slug)
    elif not first_reason:
        next_step = "أكمل اختيار سبب التردد في نافذة الودجت ثم راقب لوحة السلال."
        test_url = merchant_activation_test_store_url(slug)
    elif not first_sent and not first_scheduled:
        next_step = "انتظر اكتمال مهلة الاسترجاع ثم حدّث قائمة السلال."
        test_url = merchant_activation_test_store_url(slug)
    elif not first_sent:
        next_step = "راجع قائمة السلال للتأكد من حالة الإرسال."
        test_url = "/dashboard#carts"
    elif not first_recovered:
        next_step = "النظام يعمل — الاسترداد المالي يظهر عند اكتمال شراء حقيقي."
        test_url = "/dashboard#carts"
    else:
        next_step = "تابع السلال والرسائل من لوحة التحكم."
        test_url = "/dashboard#carts"

    delay_hint = ""
    if first_cart and not first_sent:
        delay_hint = _recovery_delay_hint_ar(store)

    activation_working = bool(first_cart and (first_scheduled or first_sent))

    return MerchantActivationPayload(
        milestones=milestones,
        summary_states=summary_states,
        current_state_id=current_id,
        current_state_label_ar=current_label,
        next_step_ar=next_step,
        test_store_url=test_url,
        delay_hint_ar=delay_hint,
        activation_working=activation_working,
    )


def build_merchant_activation_api_payload(
    store: Optional[Any] = None,
    *,
    cookies: Optional[dict[str, str]] = None,
    month_abandoned: int = 0,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> dict[str, Any]:
    from services.merchant_dashboard_home_stage_v1 import resolve_merchant_home_layout
    from services.merchant_onboarding_store import resolve_merchant_onboarding_store
    from services.merchant_onboarding_v1 import build_merchant_onboarding_flow

    owned, resolution = resolve_merchant_onboarding_store(cookies=cookies or {})
    mid = resolution.merchant_id
    if owned is not None:
        store = owned
    payload = build_merchant_activation_payload(store, cookies=cookies)
    out = payload.to_dict()
    out["store_slug"] = (
        (getattr(store, "zid_store_id", None) or "").strip() if store else ""
    )

    flow = build_merchant_onboarding_flow(
        store, merchant_user_id=mid, emit_logs=False
    )
    first_reason = _first_reason_captured_readonly(store) if store else False
    onboarding_complete = bool(flow.onboarding_complete)
    first_cart, first_scheduled, first_sent, first_recovered = (
        _activation_milestone_flags_for_layout(store, out)
    )
    activation_working = bool(out.get("activation_working"))
    layout = resolve_merchant_home_layout(
        store,
        onboarding_complete=onboarding_complete,
        first_cart=first_cart,
        first_reason=first_reason,
        first_scheduled=first_scheduled,
        first_sent=first_sent,
        first_recovered=first_recovered,
        activation_working=activation_working,
        current_state_label_ar=str(out.get("current_state_label_ar") or ""),
        month_abandoned=int(month_abandoned),
        month_recovered=int(month_recovered),
        month_revenue=float(month_revenue or 0.0),
    )
    out.update(layout.to_dict())
    from services.merchant_dashboard_home_stage_v1 import (  # noqa: PLC0415
        production_signal_reasons,
    )
    from services.merchant_activation_visibility_debug_v1 import (  # noqa: PLC0415
        build_activation_visibility_debug,
    )

    out["production_signal_reasons"] = production_signal_reasons(
        first_recovered=first_recovered,
        month_recovered=int(month_recovered),
        month_revenue=float(month_revenue or 0.0),
    )

    dbg = build_activation_visibility_debug(
        layout,
        store_slug=str(out.get("store_slug") or ""),
        onboarding_complete=onboarding_complete,
        first_cart=first_cart,
        first_reason=first_reason,
        first_scheduled=first_scheduled,
        first_sent=first_sent,
        first_recovered=first_recovered,
        activation_working=activation_working,
        month_abandoned=int(month_abandoned),
        month_recovered=int(month_recovered),
        month_revenue=float(month_revenue or 0.0),
    )
    out["activation_visibility_debug"] = dbg
    from services.merchant_activation_live_inspect_v1 import (  # noqa: PLC0415
        log_activation_state_from_summary,
    )

    log_activation_state_from_summary(
        {
            "merchant_activation": out,
            "merchant_activation_visibility_debug": dbg,
        }
    )
    return out


__all__ = [
    "ActivationDemoResolution",
    "MerchantActivationPayload",
    "build_merchant_activation_api_payload",
    "build_merchant_activation_payload",
    "merchant_activation_demo_nav_base",
    "merchant_activation_test_store_url",
    "resolve_activation_demo_for_request",
    "sanitize_activation_store_slug",
]
