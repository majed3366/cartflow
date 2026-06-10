# -*- coding: utf-8 -*-
"""
Targeted operational control v1 — additive gates (no lifecycle/queue/recovery logic changes).

Isolate failing components: pause WA, scheduling, store, reason, continuation, provider.
Everything disabled by default; durable singleton DB snapshot shared across workers
(operational_control_store_v1) with in-process cache reloaded before gate reads.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Optional

log = logging.getLogger(__name__)

_CONTROL_LOCK = threading.RLock()
_MAX_EVENTS = 200

# Control type keys (admin API + gates)
CONTROL_PAUSE_WA = "pause_wa"
CONTROL_PAUSE_SCHEDULING = "pause_scheduling"
CONTROL_PAUSE_STORE = "pause_store"
CONTROL_PAUSE_REASON = "pause_reason"
CONTROL_PAUSE_CONTINUATION = "pause_continuation"
CONTROL_PAUSE_PROVIDER = "pause_provider"

VALID_CONTROLS = frozenset(
    {
        CONTROL_PAUSE_WA,
        CONTROL_PAUSE_SCHEDULING,
        CONTROL_PAUSE_STORE,
        CONTROL_PAUSE_REASON,
        CONTROL_PAUSE_CONTINUATION,
        CONTROL_PAUSE_PROVIDER,
    }
)

KNOWN_PROVIDERS = frozenset({"twilio", "meta", "all"})


@dataclass
class OperationalControlState:
    """All controls off by default."""

    platform_wa_paused: bool = False
    platform_schedule_paused: bool = False
    platform_continuation_paused: bool = False
    provider_paused: bool = False
    provider_id: Optional[str] = None
    paused_stores: set[str] = field(default_factory=set)
    paused_reasons: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class GateEvaluation:
    allowed: bool
    flag_name: str
    block_reason: Optional[str] = None
    scope: Optional[str] = None


_state = OperationalControlState()
_events: Deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
_db_cache_updated_at: Optional[datetime] = None
_oc_availability: dict[str, Any] = {
    "available": True,
    "reason": None,
    "since_utc": None,
}

BLOCK_REASON_OC_UNAVAILABLE = "operational_control_unavailable"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_slug(slug: Optional[str]) -> str:
    return (slug or "").strip().lower()[:255]


def _norm_reason(reason: Optional[str]) -> str:
    return (reason or "").strip().lower()[:128]


def _norm_provider(provider: Optional[str]) -> str:
    p = (provider or "twilio").strip().lower()[:32]
    return p if p in KNOWN_PROVIDERS else "twilio"


def _hydrate_state_from_dict(data: dict[str, Any]) -> OperationalControlState:
    return OperationalControlState(
        platform_wa_paused=bool(data.get("platform_wa_paused")),
        platform_schedule_paused=bool(data.get("platform_schedule_paused")),
        platform_continuation_paused=bool(data.get("platform_continuation_paused")),
        provider_paused=bool(data.get("provider_paused")),
        provider_id=data.get("provider_id"),
        paused_stores=set(data.get("paused_stores") or []),
        paused_reasons=set(data.get("paused_reasons") or []),
    )


def _mark_operational_control_available() -> None:
    with _CONTROL_LOCK:
        _oc_availability["available"] = True
        _oc_availability["reason"] = None
        _oc_availability["since_utc"] = None


def _mark_operational_control_unavailable(reason: str) -> None:
    with _CONTROL_LOCK:
        _oc_availability["available"] = False
        _oc_availability["reason"] = (reason or "unknown")[:200]
        _oc_availability["since_utc"] = _utc_now_iso()


def get_operational_control_availability() -> dict[str, Any]:
    """Whether durable operational-control state was loaded successfully."""
    with _CONTROL_LOCK:
        return {
            "available": bool(_oc_availability.get("available", True)),
            "reason": _oc_availability.get("reason"),
            "since_utc": _oc_availability.get("since_utc"),
        }


def _gate_blocked_if_unavailable(flag_name: str) -> Optional[GateEvaluation]:
    if not get_operational_control_availability().get("available", True):
        return GateEvaluation(
            allowed=False,
            flag_name=flag_name,
            block_reason=BLOCK_REASON_OC_UNAVAILABLE,
            scope="platform",
        )
    return None


def _unavailable_whatsapp_block_dict() -> dict[str, Any]:
    avail = get_operational_control_availability()
    return {
        "ok": False,
        "error": BLOCK_REASON_OC_UNAVAILABLE,
        "operational_control": True,
        "wa_send_allowed": False,
        "scope": "platform",
        "operational_control_unavailable": True,
        "unavailable_reason": avail.get("reason"),
    }


def _ensure_state_fresh_from_db() -> None:
    """Reload in-process cache when durable snapshot is newer (shared across workers)."""
    global _state, _db_cache_updated_at
    try:
        from services.operational_control_store_v1 import load_durable_operational_control

        data, db_updated = load_durable_operational_control()
        if data is None:
            _mark_operational_control_available()
            return
        if db_updated is not None and _db_cache_updated_at == db_updated:
            _mark_operational_control_available()
            return
        with _CONTROL_LOCK:
            if db_updated is not None and _db_cache_updated_at == db_updated:
                _mark_operational_control_available()
                return
            _state = _hydrate_state_from_dict(data)
            _db_cache_updated_at = db_updated
        _mark_operational_control_available()
    except Exception as exc:  # noqa: BLE001
        _mark_operational_control_unavailable(str(exc))
        log.warning("operational control db refresh failed: %s", exc)


def _persist_state_to_db() -> None:
    global _db_cache_updated_at
    try:
        from services.operational_control_store_v1 import persist_durable_operational_control

        with _CONTROL_LOCK:
            updated = persist_durable_operational_control(_state)
        if updated is not None:
            _db_cache_updated_at = updated
    except Exception as exc:  # noqa: BLE001
        log.warning("operational control db persist failed: %s", exc)


def get_operational_control_state() -> dict[str, Any]:
    _ensure_state_fresh_from_db()
    availability = get_operational_control_availability()
    with _CONTROL_LOCK:
        st = _state
        return {
            "version": "operational_control_v1",
            "generated_at_utc": _utc_now_iso(),
            "availability": availability,
            "healthy": bool(availability.get("available", True)),
            "platform_wa_paused": st.platform_wa_paused,
            "platform_schedule_paused": st.platform_schedule_paused,
            "platform_continuation_paused": st.platform_continuation_paused,
            "provider_paused": st.provider_paused,
            "provider_id": st.provider_id,
            "schedule_creation_allowed": not st.platform_schedule_paused,
            "paused_stores": sorted(st.paused_stores),
            "paused_reasons": sorted(st.paused_reasons),
            "flags": {
                "wa_send_allowed": evaluate_wa_send_allowed().allowed,
                "schedule_creation_allowed": evaluate_schedule_creation_allowed().allowed,
                "continuation_allowed": evaluate_continuation_allowed().allowed,
                "provider_paused": st.provider_paused,
            },
            "recent_events": list(_events)[-50:],
        }


def clear_operational_control_state_for_tests() -> None:
    global _state, _db_cache_updated_at
    with _CONTROL_LOCK:
        _state = OperationalControlState()
        _events.clear()
        _db_cache_updated_at = None
        _mark_operational_control_available()
    try:
        from schema_operational_control import reset_operational_control_schema_guard_for_tests
        from services.operational_control_store_v1 import (
            reset_durable_operational_control_for_tests,
        )

        reset_operational_control_schema_guard_for_tests()
        reset_durable_operational_control_for_tests()
    except Exception:  # noqa: BLE001
        pass


def simulate_operational_control_process_restart_for_tests() -> None:
    """Drop in-process cache only — mimics worker restart; durable row must survive."""
    global _state, _db_cache_updated_at
    with _CONTROL_LOCK:
        _state = OperationalControlState()
        _events.clear()
        _db_cache_updated_at = None
        _mark_operational_control_available()


def _emit_control_event(
    *,
    operator: str,
    reason: str,
    scope: str,
    duration: str,
    effect: str,
    control: str,
    dry_run: bool,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    entry = {
        "at_utc": _utc_now_iso(),
        "operator": (operator or "admin")[:128],
        "reason": (reason or "")[:512],
        "scope": (scope or "")[:256],
        "duration": (duration or "until_resume")[:128],
        "effect": (effect or "")[:512],
        "control": control,
        "dry_run": bool(dry_run),
        "detail": detail or {},
    }
    with _CONTROL_LOCK:
        _events.append(entry)
    prefix = "[CONTROL DRY RUN]" if dry_run else "[OPERATIONAL CONTROL EVENT]"
    log.info(
        "%s operator=%s reason=%s scope=%s duration=%s effect=%s control=%s",
        prefix,
        entry["operator"],
        entry["reason"],
        entry["scope"],
        entry["duration"],
        entry["effect"],
        control,
    )
    print(
        f"{prefix} operator={entry['operator']} reason={entry['reason']} "
        f"scope={entry['scope']} duration={entry['duration']} effect={entry['effect']}",
        flush=True,
    )


def _store_paused(store_slug: Optional[str]) -> bool:
    ss = _norm_slug(store_slug)
    if not ss:
        return False
    with _CONTROL_LOCK:
        return ss in _state.paused_stores


def _reason_paused(reason_tag: Optional[str]) -> bool:
    rt = _norm_reason(reason_tag)
    if not rt:
        return False
    with _CONTROL_LOCK:
        paused = _state.paused_reasons
        if rt in paused:
            return True
        for p in paused:
            if rt.startswith(p) or p.startswith(rt):
                return True
    return False


def evaluate_wa_send_allowed(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
) -> GateEvaluation:
    blocked = _gate_blocked_if_unavailable("wa_send_allowed")
    if blocked is not None:
        return blocked
    _ensure_state_fresh_from_db()
    blocked = _gate_blocked_if_unavailable("wa_send_allowed")
    if blocked is not None:
        return blocked
    with _CONTROL_LOCK:
        if _state.platform_wa_paused:
            return GateEvaluation(
                allowed=False,
                flag_name="wa_send_allowed",
                block_reason="platform_wa_paused",
                scope="platform",
            )
        if _store_paused(store_slug):
            return GateEvaluation(
                allowed=False,
                flag_name="wa_send_allowed",
                block_reason="store_paused",
                scope=_norm_slug(store_slug),
            )
        if _reason_paused(reason_tag):
            return GateEvaluation(
                allowed=False,
                flag_name="wa_send_allowed",
                block_reason="reason_paused",
                scope=_norm_reason(reason_tag),
            )
        if _state.provider_paused:
            pid = (_state.provider_id or "twilio").lower()
            if pid in ("twilio", "all", "meta"):
                return GateEvaluation(
                    allowed=False,
                    flag_name="wa_send_allowed",
                    block_reason="provider_paused",
                    scope=pid,
                )
    return GateEvaluation(allowed=True, flag_name="wa_send_allowed")


def evaluate_schedule_creation_allowed(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    is_new_row: bool = True,
) -> GateEvaluation:
    if not is_new_row:
        return GateEvaluation(allowed=True, flag_name="schedule_creation_allowed")
    blocked = _gate_blocked_if_unavailable("schedule_creation_allowed")
    if blocked is not None:
        return blocked
    _ensure_state_fresh_from_db()
    blocked = _gate_blocked_if_unavailable("schedule_creation_allowed")
    if blocked is not None:
        return blocked
    with _CONTROL_LOCK:
        if _state.platform_schedule_paused:
            return GateEvaluation(
                allowed=False,
                flag_name="schedule_creation_allowed",
                block_reason="platform_schedule_paused",
                scope="platform",
            )
    if _store_paused(store_slug):
        return GateEvaluation(
            allowed=False,
            flag_name="schedule_creation_allowed",
            block_reason="store_paused",
            scope=_norm_slug(store_slug),
        )
    if _reason_paused(reason_tag):
        return GateEvaluation(
            allowed=False,
            flag_name="schedule_creation_allowed",
            block_reason="reason_paused",
            scope=_norm_reason(reason_tag),
        )
    return GateEvaluation(allowed=True, flag_name="schedule_creation_allowed")


def evaluate_continuation_allowed(*, store_slug: Optional[str] = None) -> GateEvaluation:
    blocked = _gate_blocked_if_unavailable("continuation_allowed")
    if blocked is not None:
        return blocked
    _ensure_state_fresh_from_db()
    blocked = _gate_blocked_if_unavailable("continuation_allowed")
    if blocked is not None:
        return blocked
    with _CONTROL_LOCK:
        if _state.platform_continuation_paused:
            return GateEvaluation(
                allowed=False,
                flag_name="continuation_allowed",
                block_reason="platform_continuation_paused",
                scope="platform",
            )
    if _store_paused(store_slug):
        return GateEvaluation(
            allowed=False,
            flag_name="continuation_allowed",
            block_reason="store_paused",
            scope=_norm_slug(store_slug),
        )
    return GateEvaluation(allowed=True, flag_name="continuation_allowed")


def evaluate_provider_send(
    *,
    provider: Optional[str] = None,
) -> GateEvaluation:
    """Provider pause blocks real provider path; mock/fallback remains visible in response."""
    prov = _norm_provider(provider)
    blocked = _gate_blocked_if_unavailable("provider_send_allowed")
    if blocked is not None:
        return blocked
    _ensure_state_fresh_from_db()
    blocked = _gate_blocked_if_unavailable("provider_send_allowed")
    if blocked is not None:
        return blocked
    with _CONTROL_LOCK:
        if not _state.provider_paused:
            return GateEvaluation(allowed=True, flag_name="provider_send_allowed")
        pid = (_state.provider_id or "twilio").lower()
        if pid == "all" or pid == prov or (pid == "twilio" and prov == "twilio"):
            return GateEvaluation(
                allowed=False,
                flag_name="provider_paused",
                block_reason="provider_paused",
                scope=pid,
            )
    return GateEvaluation(allowed=True, flag_name="provider_send_allowed")


def apply_operational_control(
    *,
    control: str,
    enabled: bool,
    operator: str = "admin",
    reason: str = "",
    duration: str = "until_resume",
    dry_run: bool = False,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict[str, Any]:
    ctrl = (control or "").strip().lower()
    if ctrl not in VALID_CONTROLS:
        return {"ok": False, "error": "invalid_control", "control": ctrl}

    scope = "platform"
    effect = ""
    detail: dict[str, Any] = {"enabled": bool(enabled)}

    if ctrl == CONTROL_PAUSE_STORE:
        ss = _norm_slug(store_slug)
        if not ss:
            return {"ok": False, "error": "store_slug_required"}
        scope = f"store:{ss}"
        effect = f"store_pause={'on' if enabled else 'off'} store={ss}"
        detail["store_slug"] = ss
    elif ctrl == CONTROL_PAUSE_REASON:
        rt = _norm_reason(reason_tag)
        if not rt:
            return {"ok": False, "error": "reason_tag_required"}
        scope = f"reason:{rt}"
        effect = f"reason_pause={'on' if enabled else 'off'} reason={rt}"
        detail["reason_tag"] = rt
    elif ctrl == CONTROL_PAUSE_PROVIDER:
        prov = _norm_provider(provider)
        scope = f"provider:{prov}"
        effect = f"provider_paused={'true' if enabled else 'false'} provider={prov}"
        detail["provider"] = prov
    elif ctrl == CONTROL_PAUSE_WA:
        scope = "platform:wa"
        effect = f"wa_send_allowed={str(not enabled).lower()}" if enabled else "wa_send_allowed=true"
        effect = f"platform_wa_paused={enabled}"
    elif ctrl == CONTROL_PAUSE_SCHEDULING:
        scope = "platform:scheduling"
        effect = f"schedule_creation_allowed={str(not enabled).lower()}" if enabled else "schedule_creation_allowed=true"
        effect = f"platform_schedule_paused={enabled}"
    elif ctrl == CONTROL_PAUSE_CONTINUATION:
        scope = "platform:continuation"
        effect = f"continuation_allowed={str(not enabled).lower()}" if enabled else "continuation_allowed=true"
        effect = f"platform_continuation_paused={enabled}"

    if dry_run:
        verification = build_operational_control_verification(preview_apply=preview_state_after(
            ctrl, enabled, store_slug=store_slug, reason_tag=reason_tag, provider=provider
        ))
        _emit_control_event(
            operator=operator,
            reason=reason,
            scope=scope,
            duration=duration,
            effect=f"dry_run_preview: {effect}",
            control=ctrl,
            dry_run=True,
            detail=detail,
        )
        return {
            "ok": True,
            "dry_run": True,
            "control": ctrl,
            "would_enable": enabled,
            "verification": verification,
            "state": get_operational_control_state(),
        }

    with _CONTROL_LOCK:
        global _state
        st = _state
        if ctrl == CONTROL_PAUSE_WA:
            st.platform_wa_paused = bool(enabled)
        elif ctrl == CONTROL_PAUSE_SCHEDULING:
            st.platform_schedule_paused = bool(enabled)
        elif ctrl == CONTROL_PAUSE_CONTINUATION:
            st.platform_continuation_paused = bool(enabled)
        elif ctrl == CONTROL_PAUSE_STORE:
            ss = _norm_slug(store_slug)
            if enabled:
                st.paused_stores.add(ss)
            else:
                st.paused_stores.discard(ss)
        elif ctrl == CONTROL_PAUSE_REASON:
            rt = _norm_reason(reason_tag)
            if enabled:
                st.paused_reasons.add(rt)
            else:
                st.paused_reasons.discard(rt)
        elif ctrl == CONTROL_PAUSE_PROVIDER:
            st.provider_paused = bool(enabled)
            st.provider_id = _norm_provider(provider) if enabled else None

    _persist_state_to_db()
    _emit_control_event(
        operator=operator,
        reason=reason,
        scope=scope,
        duration=duration,
        effect=effect,
        control=ctrl,
        dry_run=False,
        detail=detail,
    )
    verification = build_operational_control_verification()
    return {
        "ok": True,
        "dry_run": False,
        "control": ctrl,
        "enabled": enabled,
        "verification": verification,
        "state": get_operational_control_state(),
    }


def resume_operational_control(
    *,
    target: str = "all",
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    provider: Optional[str] = None,
    operator: str = "admin",
    reason: str = "resume",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Resume clears pauses (target=all|wa|scheduling|store|reason|continuation|provider)."""
    tgt = (target or "all").strip().lower()
    if dry_run:
        _emit_control_event(
            operator=operator,
            reason=reason,
            scope=f"resume:{tgt}",
            duration="n/a",
            effect="dry_run_resume_preview",
            control="resume",
            dry_run=True,
        )
        return {"ok": True, "dry_run": True, "target": tgt, "state": get_operational_control_state()}

    with _CONTROL_LOCK:
        global _state
        st = _state
        if tgt in ("all", "wa"):
            st.platform_wa_paused = False
        if tgt in ("all", "scheduling", "schedule"):
            st.platform_schedule_paused = False
        if tgt in ("all", "continuation"):
            st.platform_continuation_paused = False
        if tgt in ("all", "provider"):
            st.provider_paused = False
            st.provider_id = None
        if tgt in ("all", "store"):
            ss = _norm_slug(store_slug)
            if ss:
                st.paused_stores.discard(ss)
            elif tgt == "all":
                st.paused_stores.clear()
        if tgt in ("all", "reason"):
            rt = _norm_reason(reason_tag)
            if rt:
                st.paused_reasons.discard(rt)
            elif tgt == "all":
                st.paused_reasons.clear()

    _persist_state_to_db()
    _emit_control_event(
        operator=operator,
        reason=reason,
        scope=f"resume:{tgt}",
        duration="n/a",
        effect=f"resumed:{tgt}",
        control="resume",
        dry_run=False,
    )
    return {
        "ok": True,
        "target": tgt,
        "verification": build_operational_control_verification(),
        "state": get_operational_control_state(),
    }


def preview_state_after(
    control: str,
    enabled: bool,
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    provider: Optional[str] = None,
) -> OperationalControlState:
    import copy

    _ensure_state_fresh_from_db()
    with _CONTROL_LOCK:
        st = copy.deepcopy(_state)
    if control == CONTROL_PAUSE_WA:
        st.platform_wa_paused = enabled
    elif control == CONTROL_PAUSE_SCHEDULING:
        st.platform_schedule_paused = enabled
    elif control == CONTROL_PAUSE_CONTINUATION:
        st.platform_continuation_paused = enabled
    elif control == CONTROL_PAUSE_STORE:
        ss = _norm_slug(store_slug)
        if enabled:
            st.paused_stores.add(ss)
        else:
            st.paused_stores.discard(ss)
    elif control == CONTROL_PAUSE_REASON:
        rt = _norm_reason(reason_tag)
        if enabled:
            st.paused_reasons.add(rt)
        else:
            st.paused_reasons.discard(rt)
    elif control == CONTROL_PAUSE_PROVIDER:
        st.provider_paused = enabled
        st.provider_id = _norm_provider(provider) if enabled else None
    return st


def build_operational_control_verification(
    *,
    preview_apply: Optional[OperationalControlState] = None,
) -> dict[str, Any]:
    """Post-control impact: stores, in-flight schedules, runtime flags."""
    if preview_apply is None:
        _ensure_state_fresh_from_db()
        with _CONTROL_LOCK:
            import copy

            st = copy.deepcopy(_state)
    else:
        st = preview_apply

    affected_stores: list[str] = sorted(st.paused_stores)
    if st.platform_wa_paused or st.platform_schedule_paused or st.platform_continuation_paused:
        affected_stores = affected_stores or ["*platform*"]

    scheduled_count = 0
    running_count = 0
    store_rows: list[dict[str, Any]] = []
    try:
        from extensions import db
        from models import RecoverySchedule
        from services.recovery_restart_survival import STATUS_RUNNING, STATUS_SCHEDULED

        db.create_all()
        q_sched = db.session.query(RecoverySchedule).filter(
            RecoverySchedule.status == STATUS_SCHEDULED
        )
        q_run = db.session.query(RecoverySchedule).filter(
            RecoverySchedule.status == STATUS_RUNNING
        )
        if st.paused_stores:
            q_sched = q_sched.filter(RecoverySchedule.store_slug.in_(list(st.paused_stores)))
            q_run = q_run.filter(RecoverySchedule.store_slug.in_(list(st.paused_stores)))
        scheduled_count = q_sched.count()
        running_count = q_run.count()
        if st.paused_reasons:
            for rt in st.paused_reasons:
                scheduled_count += (
                    db.session.query(RecoverySchedule)
                    .filter(
                        RecoverySchedule.status == STATUS_SCHEDULED,
                        RecoverySchedule.reason_tag.ilike(f"%{rt}%"),
                    )
                    .count()
                )
        for slug in list(st.paused_stores)[:20]:
            sc = (
                db.session.query(RecoverySchedule)
                .filter(
                    RecoverySchedule.store_slug == slug,
                    RecoverySchedule.status.in_([STATUS_SCHEDULED, STATUS_RUNNING]),
                )
                .count()
            )
            store_rows.append({"store_slug": slug, "active_schedules": sc})
    except Exception as exc:  # noqa: BLE001
        log.warning("operational control verification db: %s", exc)
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass

    runtime_impact = {
        "wa_send_allowed": not st.platform_wa_paused
        and not (st.provider_paused and (st.provider_id or "twilio") in ("twilio", "all", "meta")),
        "schedule_creation_allowed": not st.platform_schedule_paused,
        "continuation_allowed": not st.platform_continuation_paused,
        "provider_paused": st.provider_paused,
        "provider_id": st.provider_id,
        "paused_store_count": len(st.paused_stores),
        "paused_reason_count": len(st.paused_reasons),
        "note_ar": "الاسترجاع الجاري يستمر؛ الإيقاف يمنع إرسال واتساب جديد أو جداول جديدة حسب النطاق.",
    }

    return {
        "affected_stores": affected_stores,
        "affected_recoveries": {
            "scheduled_count": scheduled_count,
            "running_count": running_count,
            "store_breakdown": store_rows,
        },
        "runtime_impact": runtime_impact,
        "paused_reasons": sorted(st.paused_reasons),
    }


def operational_control_blocks_whatsapp_send(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Return error dict if blocked; None if allowed."""
    if not get_operational_control_availability().get("available", True):
        return _unavailable_whatsapp_block_dict()
    wa = evaluate_wa_send_allowed(store_slug=store_slug, reason_tag=reason_tag)
    if not wa.allowed and wa.block_reason == BLOCK_REASON_OC_UNAVAILABLE:
        return _unavailable_whatsapp_block_dict()
    if not wa.allowed:
        prov = evaluate_provider_send(provider="twilio")
        fallback = "mock_or_degraded_path_available" if not prov.allowed else None
        return {
            "ok": False,
            "error": wa.block_reason or "operational_control_blocked",
            "operational_control": True,
            "wa_send_allowed": False,
            "scope": wa.scope,
            "provider_paused": not prov.allowed,
            "fallback_hint": fallback,
        }
    prov = evaluate_provider_send(provider="twilio")
    if not prov.allowed:
        return {
            "ok": False,
            "error": "provider_paused",
            "operational_control": True,
            "wa_send_allowed": False,
            "provider_paused": True,
            "fallback_hint": "mock_or_degraded_path_available",
        }
    return None


def operational_control_blocks_schedule_creation(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    is_new_row: bool,
) -> bool:
    return operational_control_blocks_schedule_creation_safe(
        store_slug=store_slug,
        reason_tag=reason_tag,
        is_new_row=is_new_row,
    )


def operational_control_blocks_whatsapp_send_safe(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Fail-closed wrapper — never raises; blocks when OC state is unavailable."""
    try:
        return operational_control_blocks_whatsapp_send(
            store_slug=store_slug,
            reason_tag=reason_tag,
        )
    except Exception as exc:  # noqa: BLE001
        _mark_operational_control_unavailable(str(exc))
        log.warning("operational control wa gate failed closed: %s", exc)
        return _unavailable_whatsapp_block_dict()


def operational_control_blocks_schedule_creation_safe(
    *,
    store_slug: Optional[str] = None,
    reason_tag: Optional[str] = None,
    is_new_row: bool,
) -> bool:
    """Fail-closed wrapper — returns True (blocked) when OC state is unavailable."""
    try:
        if not get_operational_control_availability().get("available", True):
            _log_schedule_block(BLOCK_REASON_OC_UNAVAILABLE, "platform")
            return True
        ev = evaluate_schedule_creation_allowed(
            store_slug=store_slug,
            reason_tag=reason_tag,
            is_new_row=is_new_row,
        )
        if not ev.allowed:
            _log_schedule_block(ev.block_reason or "operational_control_blocked", ev.scope)
            return True
        return False
    except Exception as exc:  # noqa: BLE001
        _mark_operational_control_unavailable(str(exc))
        log.warning("operational control schedule gate failed closed: %s", exc)
        _log_schedule_block(BLOCK_REASON_OC_UNAVAILABLE, "platform")
        return True


def evaluate_continuation_allowed_safe(*, store_slug: Optional[str] = None) -> GateEvaluation:
    """Fail-closed wrapper — never raises."""
    try:
        return evaluate_continuation_allowed(store_slug=store_slug)
    except Exception as exc:  # noqa: BLE001
        _mark_operational_control_unavailable(str(exc))
        log.warning("operational control continuation gate failed closed: %s", exc)
        return GateEvaluation(
            allowed=False,
            flag_name="continuation_allowed",
            block_reason=BLOCK_REASON_OC_UNAVAILABLE,
            scope="platform",
        )


def _log_schedule_block(reason: Optional[str], scope: Optional[str]) -> None:
    log.info(
        "[OPERATIONAL CONTROL] schedule_creation_blocked reason=%s scope=%s",
        reason,
        scope,
    )
    print(
        f"[OPERATIONAL CONTROL] schedule_creation_allowed=false "
        f"reason={reason} scope={scope}",
        flush=True,
    )
