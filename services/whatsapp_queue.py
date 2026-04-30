# -*- coding: utf-8 -*-
"""
طابور إرسال واتساب للاسترجاع: إدراج + عامل يناوب كل ‎X‎ ثوانٍ (أو مباشرة عند وصول وظيفة) مع
إعادة المحاولة حتى ‎3‎ محاولات. السجلات: ‎queued، sent_real / mock_sent، failed_retry، failed_final‎.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from services.whatsapp_send import (
    WA_TRACE_DELAY_UNSPECIFIED,
    send_whatsapp_mock,
    send_whatsapp_real,
)

logger = logging.getLogger("cartflow.whatsapp_queue")

MAX_WA_SEND_ATTEMPTS = 3


@dataclass(frozen=True)
class RecoveryWhatsappJob:
    """وظيفة سطر في طابور إرسال خطوة استرجاع واحدة."""

    store_slug: str
    session_id: str
    cart_id: Optional[str]
    phone: str
    message: str
    step: int
    recovery_key: str
    use_real: bool
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def _queue_interval() -> float:
    try:
        v = float((os.getenv("WHATSAPP_QUEUE_INTERVAL_SECONDS") or "2.0").strip())
    except (TypeError, ValueError):
        v = 2.0
    return max(0.1, v)


def _retry_backoff() -> float:
    try:
        v = float((os.getenv("WHATSAPP_QUEUE_RETRY_BACKOFF_SECONDS") or "1.0").strip())
    except (TypeError, ValueError):
        v = 1.0
    return max(0.0, v)


# طابور لكل ‎event loop‎ (Queue مرتبطة بالحلقة).
_worker_start_lock = threading.Lock()
_queue_by_loop: dict[asyncio.AbstractEventLoop, "asyncio.Queue[Tuple[RecoveryWhatsappJob, asyncio.Future[str]]]"] = {}
_worker_task_by_loop: dict[asyncio.AbstractEventLoop, asyncio.Task[None]] = {}
# (recovery_key, step, message) -> future لدمج الاستدعاءات المكرّرة لنفس الخطوة
_inflight_lock = threading.Lock()
_inflight: dict[Tuple[str, int, str], "asyncio.Future[str]"] = {}


def _inflight_dedup_key(
    recovery_key: str, step: int, message: str
) -> Tuple[str, int, str]:
    """نفس ‎(store:session) + step + message‎ — وظيفة منطقية واحدة في الطابور."""
    return (recovery_key, step, message)


def _q() -> "asyncio.Queue[Tuple[RecoveryWhatsappJob, asyncio.Future[str]]]":
    loop = asyncio.get_running_loop()
    with _worker_start_lock:
        q = _queue_by_loop.get(loop)
        if q is None:
            q = asyncio.Queue()
            _queue_by_loop[loop] = q
        return q


def _persist() -> Any:
    from main import _persist_cart_recovery_log

    return _persist_cart_recovery_log


def _is_converted(key: str) -> bool:
    from main import _is_user_converted

    return _is_user_converted(key)


def _one_send(
    use_real: bool,
    phone: str,
    message: str,
    *,
    trace_session_id: Optional[str] = None,
    trace_store_slug: Optional[str] = None,
) -> Dict[str, Any]:
    trace_kw: Dict[str, Any] = {
        "wa_trace_path": os.path.abspath(__file__),
        "wa_trace_session_id": trace_session_id,
        "wa_trace_store_slug": trace_store_slug,
        "wa_trace_delay_passed": WA_TRACE_DELAY_UNSPECIFIED,
    }
    if use_real:
        return send_whatsapp_real(phone, message, **trace_kw)
    out = send_whatsapp_mock(phone, message, **trace_kw)
    if isinstance(out, dict):
        return out
    return {"ok": bool(out)}


def _is_send_ok(res: Any) -> bool:
    if isinstance(res, Exception):
        return False
    if not isinstance(res, dict):
        return bool(res)
    if res.get("ok") is True:
        return True
    return False


async def _process_one_job(
    job: RecoveryWhatsappJob, fut: "asyncio.Future[str]"
) -> None:
    dedup_key = _inflight_dedup_key(
        job.recovery_key, job.step, (job.message or "")
    )
    try:
        await _do_process_one_job_body(job, fut)
    finally:
        with _inflight_lock:
            if _inflight.get(dedup_key) is fut:
                _inflight.pop(dedup_key, None)


async def _do_process_one_job_body(
    job: RecoveryWhatsappJob, fut: "asyncio.Future[str]"
) -> None:
    persist = _persist()
    from main import _recovery_should_skip_whatsapp_for_session

    if not fut.cancelled() and not fut.done() and _is_converted(job.recovery_key):
        persist(
            store_slug=job.store_slug,
            session_id=job.session_id,
            cart_id=job.cart_id,
            phone=job.phone,
            message=job.message,
            status="stopped_converted",
            step=job.step,
        )
        fut.set_result("stopped")
        return

    for attempt in range(1, MAX_WA_SEND_ATTEMPTS + 1):
        if not fut.cancelled() and not fut.done() and _is_converted(job.recovery_key):
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=job.phone,
                message=job.message,
                status="stopped_converted",
                step=job.step,
            )
            fut.set_result("stopped")
            return

        # يفسح للمورد الحلقات الأخرى (مثل ‎POST /api/conversion‎) أن تُنفّذ قبل الإرسال.
        await asyncio.sleep(0)
        if not fut.cancelled() and not fut.done() and _is_converted(job.recovery_key):
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=job.phone,
                message=job.message,
                status="stopped_converted",
                step=job.step,
            )
            fut.set_result("stopped")
            return

        if _recovery_should_skip_whatsapp_for_session(
            job.store_slug, job.session_id
        ):
            print("[SKIP WA - USER REJECTED HELP]")
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=None,
                message=job.message,
                status="skipped_user_rejected_help",
                step=job.step,
            )
            fut.set_result("skipped")
            return

        try:
            r = _one_send(
                job.use_real,
                job.phone,
                job.message,
                trace_session_id=job.session_id,
                trace_store_slug=job.store_slug,
            )
            ok = _is_send_ok(r)
        except Exception as e:  # noqa: BLE001
            logger.warning("wa queue send: %s", e, exc_info=True)
            ok = False
            r = e

        if (
            not ok
            and isinstance(r, dict)
            and r.get("error") == "user_rejected_help"
        ):
            print("skipped_user_rejected_help = True")
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=None,
                message=job.message,
                status="skipped_user_rejected_help",
                step=job.step,
            )
            fut.set_result("skipped")
            return

        if ok:
            now = datetime.now(timezone.utc)
            st = "sent_real" if job.use_real else "mock_sent"
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=job.phone,
                message=job.message,
                status=st,
                sent_at=now,
                step=job.step,
            )
            fut.set_result("success")
            return

        if attempt < MAX_WA_SEND_ATTEMPTS:
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=job.phone,
                message=job.message,
                status="failed_retry",
                step=job.step,
            )
            await asyncio.sleep(_retry_backoff())
        else:
            if _is_converted(job.recovery_key):
                persist(
                    store_slug=job.store_slug,
                    session_id=job.session_id,
                    cart_id=job.cart_id,
                    phone=job.phone,
                    message=job.message,
                    status="stopped_converted",
                    step=job.step,
                )
                if not fut.done() and not fut.cancelled():
                    fut.set_result("stopped")
                return
            persist(
                store_slug=job.store_slug,
                session_id=job.session_id,
                cart_id=job.cart_id,
                phone=job.phone,
                message=job.message,
                status="failed_final",
                step=job.step,
            )
            if not fut.done() and not fut.cancelled():
                fut.set_result("failed_final")
            return

    if not fut.done() and not fut.cancelled():
        fut.set_result("failed_final")


async def _worker_main() -> None:
    inv = _queue_interval()
    q = _q()
    while True:
        try:
            try:
                job, fut = await asyncio.wait_for(q.get(), timeout=inv)
            except asyncio.TimeoutError:
                continue
            try:
                await _process_one_job(job, fut)
            except Exception as e:  # noqa: BLE001
                logger.exception("wa queue worker: %s", e)
                if not fut.cancelled() and not fut.done():
                    fut.set_exception(e)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("wa queue loop")


async def start_whatsapp_queue_worker() -> None:
    """يبدأ عامل الطابور (مرة واحدة لكل ‎event loop‎)."""
    loop = asyncio.get_running_loop()
    with _worker_start_lock:
        t = _worker_task_by_loop.get(loop)
        if t is not None and not t.done():
            return
        _worker_task_by_loop[loop] = loop.create_task(
            _worker_main(), name="cartflow-whatsapp-queue"
        )


async def enqueue_recovery_and_wait(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    phone: str,
    message: str,
    step: int,
    recovery_key: str,
    use_real: bool,
) -> str:
    """
    يدفع وظيفة وينتظر: ‎success، failed_final، stopped‎.
    يسجّل ‎main‎ ‎status=«queued»‎ عادةً قبل النداء.
    وظيفتان بنفس (recovery_key + step + message) وفي انتظار غير مُنهٍ: الانتظار
    لنفس المستقبل دون إدخال ثانٍ.
    """
    job = RecoveryWhatsappJob(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        phone=phone,
        message=message,
        step=step,
        recovery_key=recovery_key,
        use_real=use_real,
    )
    key = _inflight_dedup_key(job.recovery_key, job.step, (message or ""))
    await start_whatsapp_queue_worker()
    loop = asyncio.get_running_loop()
    await_dup: Optional["asyncio.Future[str]"] = None
    fut: Optional["asyncio.Future[str]"] = None
    with _inflight_lock:
        ex = _inflight.get(key)
        if ex is not None and not ex.done():
            await_dup = ex
        else:
            if ex is not None and ex.done():
                _inflight.pop(key, None)
            nxt: "asyncio.Future[str]" = loop.create_future()
            _inflight[key] = nxt
            fut = nxt
    if await_dup is not None:
        return await await_dup
    assert fut is not None
    await _q().put((job, fut))
    return await fut


def _queue_diagnostics_for_tests() -> Tuple[int, int]:
    """(حجم طابور الحلقة الحالية, عدد مفاتيح inflight) — للاختبارات فقط."""
    with _inflight_lock:
        infl = len(_inflight)
    try:
        n = _q().qsize()
    except Exception:  # noqa: BLE001
        n = -1
    return n, infl
