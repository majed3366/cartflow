# -*- coding: utf-8 -*-
"""
Reality Validation Identity Audit V1.

Proves Living Store simulation, merchant session, and every merchant surface
read the same store dataset — or reports exactly where divergence begins.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from services.living_store_reality_prod_v1 import (
    REVIEW_EMAIL,
    living_store_prod_job_status_v1,
)
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG

REALITY_VALIDATION_CONTEXT_VERSION_V1 = "reality_validation_identity_certification_v1"
LIVING_STORE_PROFILE = "living_store"
MERCHANT_SURFACES_V1 = (
    "home",
    "decision_workspace",
    "products",
    "carts",
    "communication",
)

IDENTITY_FIELDS_V1 = (
    "store_slug",
    "merchant_id",
    "simulation_run_id",
    "living_store_profile",
    "database_environment",
    "last_simulation_timestamp",
    "observation_count",
    "situation_count",
    "business_fact_count",
)

_RECOMMENDATIONS_V1 = {
    "missing_canonical_identity": (
        "Run Living Store on production demo and issue the review session "
        "(/dev/living-store-reality-run then /dev/living-store-home-review) "
        "before any CEO Product Review."
    ),
    "missing_on_surface": (
        "Surface identity stamp missing — rebuild dashboard summary after "
        "Living Store seed; do not review UI until stamp is present."
    ),
    "value_mismatch": (
        "Stop the review. Re-bind the browser via /dev/living-store-home-review "
        "and confirm store_slug=demo on every surface before continuing."
    ),
    "projection_ids_not_subset_of_dataset": (
        "Surface projections invent situation_ids outside the Living Store "
        "dataset — block review until Situations recompose from demo facts."
    ),
    "package_store_slug_mismatch": (
        "ORV / Facts / Situations packages resolve a different store_slug — "
        "fix auth binding; do not review."
    ),
    "not_production": (
        "CEO review is only valid on Production environment + Production database."
    ),
    "browser_session_not_demo": (
        "Open /dev/living-store-home-review so the browser cookie resolves to demo."
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(v: Any) -> str:
    return str(v or "").strip()


def detect_database_environment_v1(
    *, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    app_env = _norm(env.get("ENV") or env.get("CARTFLOW_ENV") or "development").lower()
    db_url = _norm(env.get("DATABASE_URL") or env.get("SQLALCHEMY_DATABASE_URI") or "")
    dialect = "unknown"
    host = ""
    if db_url.startswith("sqlite"):
        dialect = "sqlite"
        host = "local"
    elif db_url:
        try:
            parsed = urlparse(db_url)
            dialect = (parsed.scheme or "unknown").split("+")[0]
            host = parsed.hostname or ""
        except Exception:  # noqa: BLE001
            dialect = "unknown"
    productionish = app_env in {"production", "prod", "railway"} or bool(
        env.get("RAILWAY_ENVIRONMENT") or env.get("RAILWAY_PROJECT_ID")
    )
    label = "production" if productionish else ("development" if app_env == "development" else app_env)
    return {
        "environment": label,
        "database_environment": f"{label}:{dialect}",
        "app_env": app_env,
        "db_dialect": dialect,
        "db_host": host,
        "productionish": productionish,
    }


def latest_living_store_run_v1(store_slug: str) -> dict[str, Any]:
    """Public: latest Living Store simulation identity for store_slug."""
    return _latest_living_store_run(store_slug)


def _latest_living_store_run(store_slug: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "simulation_run_id": None,
        "living_store_profile": None,
        "last_simulation_timestamp": None,
        "store_slug": None,
        "status": None,
        "source": None,
    }
    job = living_store_prod_job_status_v1()
    sim = job.get("simulation") if isinstance(job.get("simulation"), Mapping) else {}
    if sim.get("simulation_run_id"):
        out.update(
            {
                "simulation_run_id": _norm(sim.get("simulation_run_id")),
                "living_store_profile": LIVING_STORE_PROFILE,
                "last_simulation_timestamp": _norm(
                    job.get("finished_at_utc") or job.get("started_at_utc")
                )
                or None,
                "store_slug": _norm(sim.get("store_slug")) or store_slug,
                "status": _norm(job.get("status")) or None,
                "source": "in_memory_job",
            }
        )
        return out
    try:
        from extensions import db  # noqa: PLC0415
        from models import SimulationRun  # noqa: PLC0415

        row = (
            db.session.query(SimulationRun)
            .filter(SimulationRun.store_slug == store_slug)
            .filter(SimulationRun.scale_profile == LIVING_STORE_PROFILE)
            .filter(SimulationRun.simulation_run_id != "lsr_prod_job_control_v1")
            .order_by(SimulationRun.created_at.desc())
            .first()
        )
        if row is None:
            row = (
                db.session.query(SimulationRun)
                .filter(SimulationRun.store_slug == store_slug)
                .order_by(SimulationRun.created_at.desc())
                .first()
            )
        if row is not None:
            ts = getattr(row, "updated_at", None) or getattr(row, "created_at", None)
            out.update(
                {
                    "simulation_run_id": _norm(row.simulation_run_id),
                    "living_store_profile": _norm(row.scale_profile)
                    or LIVING_STORE_PROFILE,
                    "last_simulation_timestamp": ts.isoformat()
                    if hasattr(ts, "isoformat")
                    else _norm(ts) or None,
                    "store_slug": _norm(row.store_slug) or store_slug,
                    "status": _norm(row.status) or None,
                    "source": "simulation_runs_table",
                }
            )
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}:{exc}"[:240]
    return out


def _merchant_session_identity(
    store_slug: str,
    *,
    cookies: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "store_slug": None,
        "merchant_id": None,
        "email": None,
        "primary_store_id": None,
        "session_resolves_to": None,
        "source": None,
    }
    try:
        from extensions import db  # noqa: PLC0415
        from models import MerchantUser, Store  # noqa: PLC0415

        demo = (
            db.session.query(Store)
            .filter(Store.zid_store_id == store_slug)
            .first()
        )
        review = (
            db.session.query(MerchantUser).filter_by(email=REVIEW_EMAIL).first()
        )
        if review is not None:
            out["merchant_id"] = str(int(review.id))
            out["email"] = REVIEW_EMAIL
            out["primary_store_id"] = (
                str(int(review.primary_store_id))
                if review.primary_store_id is not None
                else None
            )
            out["source"] = "living_store_review_user"
            if demo is not None and int(review.primary_store_id or 0) == int(demo.id):
                out["store_slug"] = store_slug
            elif demo is not None:
                out["store_slug"] = _norm(getattr(demo, "zid_store_id", None))
                # primary points elsewhere — capture mismatch via store_slug of primary
                primary = (
                    db.session.query(Store)
                    .filter(Store.id == int(review.primary_store_id or 0))
                    .first()
                )
                if primary is not None:
                    out["store_slug"] = _norm(primary.zid_store_id)
        elif demo is not None and getattr(demo, "merchant_user_id", None):
            out["merchant_id"] = str(int(demo.merchant_user_id))
            out["store_slug"] = store_slug
            out["source"] = "demo_store.merchant_user_id"
        else:
            out["store_slug"] = store_slug
            out["source"] = "store_slug_only"

        if cookies:
            from services.merchant_auth_v1 import (  # noqa: PLC0415
                resolve_authenticated_store_slug,
            )

            resolved = resolve_authenticated_store_slug(dict(cookies))
            out["session_resolves_to"] = _norm(resolved) or None
            if out["session_resolves_to"]:
                # Cookie session is the merchant-visible identity when present.
                out["store_slug"] = out["session_resolves_to"]
                out["source"] = (out.get("source") or "") + "+cookie_session"
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}:{exc}"[:240]
        out["store_slug"] = out.get("store_slug") or store_slug
    return out


def _dataset_counts(store_slug: str) -> dict[str, Any]:
    from services.business_facts_v1 import (  # noqa: PLC0415
        build_business_facts_package_v1,
    )
    from services.commerce_situations_v1 import (  # noqa: PLC0415
        build_commerce_situations_package_v1,
        surface_projection_v1,
    )
    from services.observation_foundation_v1.assemble_v1 import (  # noqa: PLC0415
        assemble_observation_foundation_v1,
    )
    from services.observation_foundation_v1.merchant_findings_v1 import (  # noqa: PLC0415
        build_observation_reality_validation_v1,
    )

    orv = build_observation_reality_validation_v1(store_slug)
    foundation = assemble_observation_foundation_v1(store_slug)
    facts_pkg = build_business_facts_package_v1(store_slug, orv_package=orv)
    sits_pkg = build_commerce_situations_package_v1(
        store_slug, facts_package=facts_pkg
    )
    findings = [
        f for f in list((orv or {}).get("findings") or []) if isinstance(f, Mapping)
    ]
    facts = [
        f for f in list((facts_pkg or {}).get("facts") or []) if isinstance(f, Mapping)
    ]
    published = [
        s
        for s in list((sits_pkg or {}).get("published_situations") or [])
        if isinstance(s, Mapping) and s.get("admitted")
    ]
    situation_ids = [_norm(s.get("situation_id")) for s in published if _norm(s.get("situation_id"))]
    home = surface_projection_v1(sits_pkg, "home")
    workspace = surface_projection_v1(sits_pkg, "decision_workspace")
    products = surface_projection_v1(sits_pkg, "products")
    carts = surface_projection_v1(sits_pkg, "carts")
    communication = surface_projection_v1(sits_pkg, "communication")

    ready = list((foundation or {}).get("statement_capabilities_ready") or [])
    return {
        "observation_count": len(findings),
        "foundation_ready_count": len(ready),
        "business_fact_count": len(facts),
        "situation_count": len(published),
        "situation_ids": situation_ids,
        "home_projection": int(home.get("count") or 0),
        "workspace_projection": int(workspace.get("count") or 0),
        "products_projection": int(products.get("count") or 0),
        "carts_projection": int(carts.get("count") or 0),
        "communication_projection": int(communication.get("count") or 0),
        "home_situation_ids": list(home.get("situation_ids") or []),
        "workspace_situation_ids": list(workspace.get("situation_ids") or []),
        "products_situation_ids": list(products.get("situation_ids") or []),
        "carts_situation_ids": list(carts.get("situation_ids") or []),
        "communication_situation_ids": list(communication.get("situation_ids") or []),
        "orv_store_slug": _norm((orv or {}).get("store_slug")) or store_slug,
        "facts_store_slug": _norm((facts_pkg or {}).get("store_slug")) or store_slug,
        "situations_store_slug": _norm((sits_pkg or {}).get("store_slug"))
        or store_slug,
    }


def _surface_block(
    *,
    name: str,
    store_slug: Optional[str],
    merchant_id: Optional[str],
    simulation_run_id: Optional[str],
    living_store_profile: Optional[str],
    database_environment: str,
    last_simulation_timestamp: Optional[str],
    observation_count: Optional[int],
    situation_count: Optional[int],
    business_fact_count: Optional[int],
    projection_count: Optional[int] = None,
    situation_ids: Optional[list[str]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    block = {
        "surface": name,
        "store_slug": store_slug,
        "merchant_id": merchant_id,
        "simulation_run_id": simulation_run_id,
        "living_store_profile": living_store_profile,
        "database_environment": database_environment,
        "last_simulation_timestamp": last_simulation_timestamp,
        "observation_count": observation_count,
        "situation_count": situation_count,
        "business_fact_count": business_fact_count,
        "projection_count": projection_count,
        "situation_ids": list(situation_ids or []),
    }
    if extra:
        block.update(extra)
    return block


def _compare_surfaces(
    expected: Mapping[str, Any],
    surfaces: Mapping[str, Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]], Optional[str]]:
    divergences: list[dict[str, Any]] = []
    order = (
        "living_store_simulation",
        "authenticated_merchant_session",
        "home",
        "decision_workspace",
        "products",
        "carts",
        "communication",
    )
    # Identity fields that must match across all surfaces (when present).
    required_identity = {
        "store_slug",
        "merchant_id",
        "simulation_run_id",
        "living_store_profile",
        "database_environment",
    }
    for field in (
        "store_slug",
        "merchant_id",
        "simulation_run_id",
        "living_store_profile",
        "database_environment",
        "observation_count",
        "situation_count",
        "business_fact_count",
    ):
        expected_val = expected.get(field)
        if expected_val in (None, "", []):
            if field in required_identity:
                divergences.append(
                    {
                        "field": field,
                        "surface": "canonical",
                        "expected": expected_val,
                        "actual": expected_val,
                        "begins_at": f"canonical.{field}",
                        "reason": "missing_canonical_identity",
                        "severity": "error",
                    }
                )
            continue
        for name in order:
            surf = surfaces.get(name) or {}
            actual = surf.get(field)
            if actual in (None, "", []):
                divergences.append(
                    {
                        "field": field,
                        "surface": name,
                        "expected": expected_val,
                        "actual": actual,
                        "begins_at": f"{name}.{field}",
                        "reason": "missing_on_surface",
                        "severity": "error",
                    }
                )
                continue
            if actual != expected_val:
                divergences.append(
                    {
                        "field": field,
                        "surface": name,
                        "expected": expected_val,
                        "actual": actual,
                        "begins_at": f"{name}.{field}",
                        "reason": "value_mismatch",
                        "severity": "error",
                    }
                )

    # Projection counts must not invent a different situation universe.
    sit_ids = set(expected.get("situation_ids") or [])
    for name, key in (
        ("home", "home_situation_ids"),
        ("decision_workspace", "workspace_situation_ids"),
        ("products", "products_situation_ids"),
        ("carts", "carts_situation_ids"),
        ("communication", "communication_situation_ids"),
    ):
        surf_ids = set((surfaces.get(name) or {}).get("situation_ids") or [])
        if surf_ids - sit_ids:
            divergences.append(
                {
                    "field": "situation_ids",
                    "surface": name,
                    "expected": sorted(sit_ids),
                    "actual": sorted(surf_ids),
                    "begins_at": f"{name}.situation_ids",
                    "reason": "projection_ids_not_subset_of_dataset",
                    "severity": "error",
                }
            )

    # Package store_slug drift (ORV/facts/situations).
    for label, val in (
        ("orv", expected.get("orv_store_slug")),
        ("facts", expected.get("facts_store_slug")),
        ("situations", expected.get("situations_store_slug")),
    ):
        if val and val != expected.get("store_slug"):
            divergences.append(
                {
                    "field": "store_slug",
                    "surface": f"dataset.{label}",
                    "expected": expected.get("store_slug"),
                    "actual": val,
                    "begins_at": f"dataset.{label}.store_slug",
                    "reason": "package_store_slug_mismatch",
                    "severity": "error",
                }
            )

    errors = [d for d in divergences if d.get("severity") == "error"]
    if errors:
        # Earliest pipeline surface wins for "begins_at".
        rank = {name: i for i, name in enumerate(order)}
        rank["canonical"] = -1
        for ds in ("dataset.orv", "dataset.facts", "dataset.situations"):
            rank[ds] = -1

        def _rank(d: Mapping[str, Any]) -> tuple[int, str]:
            begins = str(d.get("begins_at") or "")
            surface = str(d.get("surface") or begins.split(".")[0])
            return (rank.get(surface, 99), begins)

        first = sorted(errors, key=_rank)[0]
        return "INCONSISTENT", divergences, str(first.get("begins_at") or "")
    return "CONSISTENT", [], None


def _matrix_row(label: str, ok: bool, value: Any) -> dict[str, Any]:
    return {
        "row": label,
        "ok": bool(ok),
        "mark": "✔" if ok else "✘",
        "value": value,
    }


def build_identity_matrix_v1(
    *,
    db_env: Mapping[str, Any],
    slug: str,
    merchant: Mapping[str, Any],
    sim: Mapping[str, Any],
    counts: Mapping[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    env_ok = _norm(db_env.get("environment")) == "production"
    db_ok = bool(db_env.get("productionish")) and _norm(
        db_env.get("db_dialect")
    ) not in {"", "sqlite", "unknown"}
    store_ok = slug == DEMO_STORE_SLUG
    session_slug = _norm(
        merchant.get("session_resolves_to") or merchant.get("store_slug")
    )
    session_ok = session_slug == DEMO_STORE_SLUG and bool(merchant.get("merchant_id"))
    run_id = _norm(sim.get("simulation_run_id"))
    run_ok = bool(run_id) and _norm(sim.get("store_slug") or slug) == DEMO_STORE_SLUG
    profile_ok = _norm(sim.get("living_store_profile") or "") == LIVING_STORE_PROFILE
    ts_ok = bool(sim.get("last_simulation_timestamp"))
    obs_ok = int(counts.get("observation_count") or 0) > 0
    facts_ok = int(counts.get("business_fact_count") or 0) > 0
    sits_ok = int(counts.get("situation_count") or 0) > 0
    same_sim = status == "CONSISTENT" and run_ok

    return [
        _matrix_row("Environment", env_ok, db_env.get("environment")),
        _matrix_row("Database", db_ok, db_env.get("database_environment")),
        _matrix_row("Store Slug", store_ok, slug),
        _matrix_row("Merchant Session", session_ok, session_slug or None),
        _matrix_row("Simulation Run", run_ok, run_id or None),
        _matrix_row(
            "Living Store Profile",
            profile_ok,
            sim.get("living_store_profile") or LIVING_STORE_PROFILE,
        ),
        _matrix_row(
            "Living Store Timestamp",
            ts_ok,
            sim.get("last_simulation_timestamp"),
        ),
        _matrix_row(
            "Observation Count", obs_ok, counts.get("observation_count")
        ),
        _matrix_row(
            "Business Facts Count", facts_ok, counts.get("business_fact_count")
        ),
        _matrix_row(
            "Commerce Situation Count", sits_ok, counts.get("situation_count")
        ),
        _matrix_row("Home", same_sim, "same simulation" if same_sim else "divergent"),
        _matrix_row(
            "Workspace", same_sim, "same simulation" if same_sim else "divergent"
        ),
        _matrix_row(
            "Products", same_sim, "same simulation" if same_sim else "divergent"
        ),
        _matrix_row("Carts", same_sim, "same simulation" if same_sim else "divergent"),
        _matrix_row(
            "Communication",
            same_sim,
            "same simulation" if same_sim else "divergent",
        ),
        _matrix_row("Status", status == "CONSISTENT", status),
    ]


def compute_ceo_review_safe_v1(
    *,
    status: str,
    db_env: Mapping[str, Any],
    slug: str,
    merchant: Mapping[str, Any],
    sim: Mapping[str, Any],
    counts: Mapping[str, Any],
    cookies: Mapping[str, str] | None,
) -> dict[str, Any]:
    """
    CEO_REVIEW_SAFE = TRUE only on Production + Production DB + demo identity
    + Living Store run + aligned Facts/Situations + browser session → demo.
    """
    reasons: list[str] = []
    env_ok = _norm(db_env.get("environment")) == "production"
    db_ok = bool(db_env.get("productionish")) and _norm(
        db_env.get("db_dialect")
    ) not in {"", "sqlite", "unknown"}
    if not env_ok:
        reasons.append("environment_not_production")
    if not db_ok:
        reasons.append("database_not_production")
    if slug != DEMO_STORE_SLUG:
        reasons.append("store_slug_not_demo")
    session_resolved = _norm(merchant.get("session_resolves_to"))
    if not cookies:
        reasons.append("browser_session_missing")
    elif session_resolved != DEMO_STORE_SLUG:
        reasons.append("browser_session_not_demo")
    merchant_slug = _norm(merchant.get("store_slug"))
    if merchant_slug and merchant_slug != DEMO_STORE_SLUG:
        reasons.append("merchant_primary_not_demo")
    if not merchant.get("merchant_id"):
        reasons.append("merchant_id_missing")
    if not sim.get("simulation_run_id"):
        reasons.append("simulation_run_missing")
    if _norm(sim.get("living_store_profile") or "") != LIVING_STORE_PROFILE:
        reasons.append("living_store_profile_mismatch")
    if not sim.get("last_simulation_timestamp"):
        reasons.append("living_store_timestamp_missing")
    if int(counts.get("observation_count") or 0) <= 0:
        reasons.append("observations_empty")
    if int(counts.get("business_fact_count") or 0) <= 0:
        reasons.append("business_facts_empty")
    if int(counts.get("situation_count") or 0) <= 0:
        reasons.append("commerce_situations_empty")
    if status != "CONSISTENT":
        reasons.append("identity_status_inconsistent")
    # Surfaces must project from the same situation universe (non-empty home).
    if int(counts.get("home_projection") or 0) <= 0:
        reasons.append("home_projection_empty")

    safe = len(reasons) == 0
    return {
        "CEO_REVIEW_SAFE": bool(safe),
        "CEO_REVIEW_SAFE_reasons": reasons,
        "constitutional_rule": (
            "No screenshot, UX review, Product Review, Product decision, "
            "or Gate closure may proceed while CEO_REVIEW_SAFE = FALSE."
        ),
    }


def enrich_divergence_report_v1(
    divergences: list[dict[str, Any]],
    begins_at: Optional[str],
) -> dict[str, Any]:
    if not divergences:
        return {
            "divergence_begins_at": None,
            "expected_value": None,
            "actual_value": None,
            "affected_surfaces": [],
            "recommendation": None,
            "items": [],
        }
    primary = next(
        (d for d in divergences if d.get("begins_at") == begins_at),
        divergences[0],
    )
    field = str(primary.get("field") or "")
    affected = sorted(
        {
            str(d.get("surface") or "")
            for d in divergences
            if d.get("severity") == "error"
            and (
                d.get("field") == field
                or d.get("begins_at") == begins_at
                or str(d.get("surface") or "") in MERCHANT_SURFACES_V1
            )
        }
    )
    # Prefer merchant-facing surface names in affected list.
    reason = str(primary.get("reason") or "value_mismatch")
    return {
        "divergence_begins_at": begins_at or primary.get("begins_at"),
        "expected_value": primary.get("expected"),
        "actual_value": primary.get("actual"),
        "affected_surfaces": affected,
        "recommendation": _RECOMMENDATIONS_V1.get(
            reason, _RECOMMENDATIONS_V1["value_mismatch"]
        ),
        "items": divergences,
    }


def render_certification_html_v1(payload: Mapping[str, Any]) -> str:
    """Minimal certification page for CEO screenshot (diagnostics only)."""
    safe = bool(payload.get("CEO_REVIEW_SAFE"))
    status = _norm(payload.get("status"))
    color = "#1f3d2f" if safe else "#8b1e1e"
    bg = "#f3faf6" if safe else "#fff5f5"
    rows = list(payload.get("identity_matrix") or [])
    matrix_html = ""
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        matrix_html += (
            f"<tr><td>{r.get('mark')} {r.get('row')}</td>"
            f"<td><code>{r.get('value')}</code></td>"
            f"<td>{'OK' if r.get('ok') else 'FAIL'}</td></tr>"
        )
    div = payload.get("divergence") if isinstance(payload.get("divergence"), Mapping) else {}
    div_html = ""
    if status != "CONSISTENT":
        div_html = (
            "<h2>Divergence</h2>"
            f"<p><strong>divergence_begins_at:</strong> "
            f"<code>{div.get('divergence_begins_at')}</code></p>"
            f"<p><strong>expected_value:</strong> "
            f"<code>{div.get('expected_value')}</code></p>"
            f"<p><strong>actual_value:</strong> "
            f"<code>{div.get('actual_value')}</code></p>"
            f"<p><strong>affected_surfaces:</strong> "
            f"{', '.join(div.get('affected_surfaces') or [])}</p>"
            f"<p><strong>recommendation:</strong> {div.get('recommendation')}</p>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Reality Validation Identity Certification</title>
<style>
body{{font-family:ui-monospace,Consolas,monospace;margin:24px;background:{bg};color:#111}}
h1{{color:{color}}}
table{{border-collapse:collapse;width:100%;max-width:720px;background:#fff}}
td,th{{border:1px solid #ccc;padding:8px;text-align:left;font-size:13px}}
.banner{{font-size:28px;font-weight:800;margin:12px 0}}
code{{word-break:break-all}}
</style></head><body>
<h1>Reality Validation Identity Certification V1</h1>
<div class="banner">Status = {status}</div>
<div class="banner">CEO_REVIEW_SAFE = {str(safe).upper()}</div>
<p>store_slug=<code>{payload.get('store_slug')}</code> ·
merchant_id=<code>{payload.get('merchant_id')}</code> ·
simulation_run_id=<code>{payload.get('simulation_run_id')}</code></p>
<p>observations={payload.get('observations')} ·
facts={payload.get('facts')} ·
situations={payload.get('situations')}</p>
<h2>Identity Matrix</h2>
<table><thead><tr><th>Check</th><th>Value</th><th>Result</th></tr></thead>
<tbody>{matrix_html}</tbody></table>
{div_html}
<p style="margin-top:24px;opacity:.75">{payload.get('constitutional_rule')}</p>
<p style="opacity:.6">composed_at_utc={payload.get('composed_at_utc')}</p>
</body></html>"""


def build_reality_validation_context_v1(
    *,
    store_slug: str = DEMO_STORE_SLUG,
    cookies: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    slug = _norm(store_slug) or DEMO_STORE_SLUG
    db_env = detect_database_environment_v1(environ=environ)
    sim = _latest_living_store_run(slug)
    merchant = _merchant_session_identity(slug, cookies=cookies)
    counts = _dataset_counts(slug)

    merchant_id = merchant.get("merchant_id")
    run_id = sim.get("simulation_run_id")
    profile = sim.get("living_store_profile") or LIVING_STORE_PROFILE
    last_ts = sim.get("last_simulation_timestamp")
    db_label = db_env["database_environment"]

    shared = {
        "store_slug": slug,
        "merchant_id": merchant_id,
        "simulation_run_id": run_id,
        "living_store_profile": profile,
        "database_environment": db_label,
        "last_simulation_timestamp": last_ts,
        "observation_count": counts["observation_count"],
        "situation_count": counts["situation_count"],
        "business_fact_count": counts["business_fact_count"],
        "situation_ids": counts["situation_ids"],
        "orv_store_slug": counts["orv_store_slug"],
        "facts_store_slug": counts["facts_store_slug"],
        "situations_store_slug": counts["situations_store_slug"],
    }

    surfaces = {
        "living_store_simulation": _surface_block(
            name="living_store_simulation",
            store_slug=sim.get("store_slug") or slug,
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=sim.get("living_store_profile") or profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            extra={"sim_source": sim.get("source"), "sim_status": sim.get("status")},
        ),
        "authenticated_merchant_session": _surface_block(
            name="authenticated_merchant_session",
            store_slug=merchant.get("store_slug"),
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            extra={
                "email": merchant.get("email"),
                "session_resolves_to": merchant.get("session_resolves_to"),
                "primary_store_id": merchant.get("primary_store_id"),
                "source": merchant.get("source"),
            },
        ),
        "home": _surface_block(
            name="home",
            store_slug=counts["situations_store_slug"],
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            projection_count=counts["home_projection"],
            situation_ids=counts["home_situation_ids"],
        ),
        "decision_workspace": _surface_block(
            name="decision_workspace",
            store_slug=counts["situations_store_slug"],
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            projection_count=counts["workspace_projection"],
            situation_ids=counts["workspace_situation_ids"],
        ),
        "products": _surface_block(
            name="products",
            store_slug=counts["situations_store_slug"],
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            projection_count=counts["products_projection"],
            situation_ids=counts["products_situation_ids"],
        ),
        "carts": _surface_block(
            name="carts",
            store_slug=counts["situations_store_slug"],
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            projection_count=counts["carts_projection"],
            situation_ids=counts["carts_situation_ids"],
        ),
        "communication": _surface_block(
            name="communication",
            store_slug=counts["situations_store_slug"],
            merchant_id=merchant_id,
            simulation_run_id=run_id,
            living_store_profile=profile,
            database_environment=db_label,
            last_simulation_timestamp=last_ts,
            observation_count=counts["observation_count"],
            situation_count=counts["situation_count"],
            business_fact_count=counts["business_fact_count"],
            projection_count=counts["communication_projection"],
            situation_ids=counts["communication_situation_ids"],
        ),
    }

    status, divergences, begins = _compare_surfaces(shared, surfaces)
    divergence = enrich_divergence_report_v1(divergences, begins)
    matrix = build_identity_matrix_v1(
        db_env=db_env,
        slug=slug,
        merchant=merchant,
        sim=sim,
        counts=counts,
        status=status,
    )
    ceo = compute_ceo_review_safe_v1(
        status=status,
        db_env=db_env,
        slug=slug,
        merchant=merchant,
        sim=sim,
        counts=counts,
        cookies=cookies,
    )

    # CEO 30-second summary fields (flat) + certification matrix.
    return {
        "ok": status == "CONSISTENT" and bool(ceo.get("CEO_REVIEW_SAFE")),
        "status": status,
        "CEO_REVIEW_SAFE": bool(ceo.get("CEO_REVIEW_SAFE")),
        "CEO_REVIEW_SAFE_reasons": list(ceo.get("CEO_REVIEW_SAFE_reasons") or []),
        "constitutional_rule": ceo.get("constitutional_rule"),
        "schema": REALITY_VALIDATION_CONTEXT_VERSION_V1,
        "certification": "reality_validation_identity_certification_v1",
        "store_slug": slug,
        "merchant_id": merchant_id,
        "simulation_run_id": run_id,
        "environment": db_env["environment"],
        "database_environment": db_label,
        "living_store_profile": profile if run_id else None,
        "last_simulation_timestamp": last_ts,
        "living_store_timestamp": last_ts,
        "facts": counts["business_fact_count"],
        "business_facts_count": counts["business_fact_count"],
        "situations": counts["situation_count"],
        "commerce_situation_count": counts["situation_count"],
        "observations": counts["observation_count"],
        "observation_count": counts["observation_count"],
        "workspace_projection": counts["workspace_projection"],
        "home_projection": counts["home_projection"],
        "products_projection": counts["products_projection"],
        "communication_projection": counts["communication_projection"],
        "carts_projection": counts["carts_projection"],
        "situation_ids": counts["situation_ids"],
        "identity_matrix": matrix,
        "surfaces": surfaces,
        "divergences": divergences,
        "divergence": divergence,
        "divergence_begins_at": divergence.get("divergence_begins_at"),
        "expected_value": divergence.get("expected_value"),
        "actual_value": divergence.get("actual_value"),
        "affected_surfaces": divergence.get("affected_surfaces"),
        "recommendation": divergence.get("recommendation"),
        "browser_session": {
            "resolves_to": merchant.get("session_resolves_to"),
            "cookie_present": bool(cookies),
            "merchant_id": merchant_id,
            "email": merchant.get("email"),
        },
        "identity_fields": list(IDENTITY_FIELDS_V1),
        "composed_at_utc": _utc_now(),
        "product_intelligence": False,
        "note": (
            "CEO_REVIEW_SAFE=TRUE only on Production + Production DB + demo "
            "browser session + Living Store run + CONSISTENT surface identity. "
            "Without certification, every CEO review is invalid."
        ),
    }


def stamp_reality_validation_identity_from_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str,
    cookies: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Hot-path stamp: reuse packages already on summary + sim/merchant identity.
    Does not recompose Facts/Situations (full audit is /dev/reality-validation-context).
    """
    if not isinstance(summary, dict):
        return summary
    slug = _norm(store_slug) or DEMO_STORE_SLUG
    db_env = detect_database_environment_v1(environ=environ)
    sim = _latest_living_store_run(slug)
    merchant = _merchant_session_identity(slug, cookies=cookies)
    orv = summary.get("observation_reality_validation_v1")
    bf = summary.get("business_facts_v1")
    cs = summary.get("commerce_situations_v1")
    obs_n = 0
    if isinstance(orv, Mapping):
        obs_n = len([f for f in list(orv.get("findings") or []) if isinstance(f, Mapping)])
    fact_n = 0
    if isinstance(bf, Mapping):
        if isinstance(bf.get("counts"), Mapping):
            try:
                fact_n = int((bf.get("counts") or {}).get("total") or 0)
            except (TypeError, ValueError):
                fact_n = 0
        if not fact_n:
            fact_n = len([f for f in list(bf.get("facts") or []) if isinstance(f, Mapping)])
    sit_n = 0
    home_n = ws_n = prod_n = carts_n = comm_n = 0
    if isinstance(cs, Mapping):
        if isinstance(cs.get("counts"), Mapping):
            try:
                sit_n = int((cs.get("counts") or {}).get("published") or 0)
            except (TypeError, ValueError):
                sit_n = 0
        routing = cs.get("routing") if isinstance(cs.get("routing"), Mapping) else {}
        teaser = (
            routing.get("home_teaser") if isinstance(routing, Mapping) else None
        )
        if isinstance(teaser, Mapping):
            home_n = int(teaser.get("count") or len(teaser.get("situations") or []) or 0)
        consumers = cs.get("consumers") if isinstance(cs.get("consumers"), Mapping) else {}
        for key, attr in (
            ("decision_workspace", "ws_n"),
            ("products", "prod_n"),
            ("carts", "carts_n"),
            ("communication", "comm_n"),
        ):
            proj = consumers.get(key) if isinstance(consumers, Mapping) else None
            if isinstance(proj, Mapping):
                try:
                    n = int(proj.get("count") or 0)
                except (TypeError, ValueError):
                    n = 0
                if attr == "ws_n":
                    ws_n = n
                elif attr == "prod_n":
                    prod_n = n
                elif attr == "carts_n":
                    carts_n = n
                else:
                    comm_n = n
        if not sit_n:
            sit_n = len(
                [
                    s
                    for s in list(cs.get("published_situations") or [])
                    if isinstance(s, Mapping)
                ]
            )
    status = "CONSISTENT"
    begins = None
    if not sim.get("simulation_run_id"):
        status = "INCONSISTENT"
        begins = "canonical.simulation_run_id"
    elif not merchant.get("merchant_id"):
        status = "INCONSISTENT"
        begins = "canonical.merchant_id"
    elif _norm(merchant.get("store_slug")) not in {"", slug}:
        status = "INCONSISTENT"
        begins = "authenticated_merchant_session.store_slug"
    ceo_safe = (
        status == "CONSISTENT"
        and _norm(db_env.get("environment")) == "production"
        and bool(db_env.get("productionish"))
        and _norm(db_env.get("db_dialect")) not in {"", "sqlite", "unknown"}
        and slug == DEMO_STORE_SLUG
        and bool(sim.get("simulation_run_id"))
        and bool(merchant.get("merchant_id"))
        and (
            not cookies
            or _norm(merchant.get("session_resolves_to")) == DEMO_STORE_SLUG
        )
        and obs_n > 0
        and fact_n > 0
        and sit_n > 0
    )
    # Hot-path never claims CEO_REVIEW_SAFE without cookie (browser uncertified).
    if not cookies:
        ceo_safe = False
    summary["reality_validation_identity_v1"] = {
        "ok": status == "CONSISTENT",
        "status": status,
        "CEO_REVIEW_SAFE": bool(ceo_safe),
        "store_slug": slug,
        "merchant_id": merchant.get("merchant_id"),
        "simulation_run_id": sim.get("simulation_run_id"),
        "living_store_profile": sim.get("living_store_profile") or LIVING_STORE_PROFILE,
        "database_environment": db_env["database_environment"],
        "last_simulation_timestamp": sim.get("last_simulation_timestamp"),
        "observation_count": obs_n,
        "situation_count": sit_n,
        "business_fact_count": fact_n,
        "home_projection": home_n,
        "workspace_projection": ws_n,
        "products_projection": prod_n,
        "carts_projection": carts_n,
        "communication_projection": comm_n,
        "divergence_begins_at": begins,
        "stamp": "summary_hot_path",
    }
    return summary


def attach_reality_validation_identity_v1(
    summary: dict[str, Any],
    *,
    store_slug: str,
    cookies: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Stamp identity onto summary (hot-path; full audit via probe)."""
    return stamp_reality_validation_identity_from_summary_v1(
        summary, store_slug=store_slug, cookies=cookies
    )


__all__ = [
    "IDENTITY_FIELDS_V1",
    "REALITY_VALIDATION_CONTEXT_VERSION_V1",
    "attach_reality_validation_identity_v1",
    "build_identity_matrix_v1",
    "build_reality_validation_context_v1",
    "compute_ceo_review_safe_v1",
    "detect_database_environment_v1",
    "latest_living_store_run_v1",
    "render_certification_html_v1",
    "stamp_reality_validation_identity_from_summary_v1",
]
