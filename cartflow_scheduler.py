# -*- coding: utf-8 -*-
"""
CartFlow Scheduler process entry.

Never starts the FastAPI / uvicorn web API. Expensive jobs stay OFF unless
explicitly enabled via environment.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

log = logging.getLogger("cartflow")


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


async def _run() -> None:
    from services.process_entry_v1 import (  # noqa: PLC0415
        assert_entry_matches_role,
        configure_scheduler_entry,
    )
    from services.runtime_role_verification_v1 import verify_runtime_role_at_startup  # noqa: PLC0415
    from services.runtime_startup_v1 import (  # noqa: PLC0415
        log_runtime_startup_banner,
        run_scheduler_drivers_at_startup,
    )
    from services.scheduler_cycle_guard_v1 import (  # noqa: PLC0415
        release_scheduler_instance_lock,
        try_acquire_scheduler_instance_lock,
    )
    from services.scheduler_runtime_state_v1 import mark_scheduler_live  # noqa: PLC0415

    configure_scheduler_entry()
    assert_entry_matches_role()

    import models  # noqa: F401, PLC0415
    from extensions import init_database  # noqa: PLC0415

    init_database()
    verify_runtime_role_at_startup()
    try_acquire_scheduler_instance_lock()

    log_runtime_startup_banner()
    out = await run_scheduler_drivers_at_startup()
    enabled = [
        name
        for name, flag in (
            ("scanner", out.get("scanner_loop_started")),
            ("resume", out.get("resume_scan_ran")),
            ("snapshot", out.get("snapshot_loop_started")),
            ("archive", out.get("archive_loop_started")),
        )
        if flag
    ]
    mark_scheduler_live(
        role="scheduler",
        enabled_jobs=enabled,
        ready=True,
    )
    _emit(
        f"[SCHEDULER ENTRY] started jobs={','.join(enabled) or 'none'} "
        f"explicit_enablement_required=true"
    )
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        release_scheduler_instance_lock()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    if (os.getenv("CARTFLOW_PROCESS_ROLE") or "").strip().lower() not in ("", "scheduler"):
        _emit("[SCHEDULER ENTRY] refused: CARTFLOW_PROCESS_ROLE must be scheduler")
        return 2
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001
        _emit(f"[SCHEDULER ENTRY] failed: {type(exc).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
