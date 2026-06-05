# -*- coding: utf-8 -*-
"""
Canonical Store identity layer — one CartFlow Store row for every platform key.

Resolves: CartFlow zid, Zid permalink/numeric/uuid, future Salla ids, recovery_key
prefixes, dashboard slugs, and widget public-config store_slug values.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import Store, StoreIdentityAlias

_log = logging.getLogger("cartflow.store_identity")

WIDGET_SANDBOX_SLUGS = frozenset({"demo", "demo2", "default"})
_link_attempt_mono: dict[str, float] = {}
_link_lock = threading.Lock()
_LINK_ATTEMPT_COOLDOWN_SEC = 90.0

# Alias kinds (stable contract — do not rename without migration)
ALIAS_KIND_CARTFLOW_ZID = "cartflow_zid"
ALIAS_KIND_ZID_PERMALINK = "zid_permalink"
ALIAS_KIND_ZID_NUMERIC_ID = "zid_numeric_id"
ALIAS_KIND_ZID_UUID = "zid_uuid"
ALIAS_KIND_SALLA_STORE_ID = "salla_store_id"

PLATFORM_CARTFLOW = "cartflow"
PLATFORM_ZID = "zid"
PLATFORM_SALLA = "salla"

ResolveMatch = Tuple[Optional[Store], str]


def normalize_identity_value(raw: Any) -> str:
    return (str(raw or "")).strip()[:255]


def canonical_store_slug_on_row(row: Optional[Any]) -> Optional[str]:
    """Primary CartFlow store key stored on ``stores.zid_store_id``."""
    if row is None:
        return None
    zid = getattr(row, "zid_store_id", None)
    if isinstance(zid, str) and zid.strip():
        return zid.strip()[:255]
    return None


def extract_zid_permalink_from_url(url: str) -> Optional[str]:
    """``https://4hz49e.zid.store/`` → ``4hz49e``."""
    u = (url or "").strip()
    if not u:
        return None
    if "://" not in u:
        u = f"https://{u}"
    try:
        host = (urlparse(u).hostname or "").strip().lower()
    except ValueError:
        return None
    suffix = ".zid.store"
    if host.endswith(suffix):
        sub = host[: -len(suffix)]
        if sub and "." not in sub:
            return sub[:255]
    return None


def is_widget_sandbox_slug(slug: str) -> bool:
    return (slug or "").strip().casefold() in WIDGET_SANDBOX_SLUGS


def looks_like_zid_storefront_permalink(slug: str) -> bool:
    """Zid permalink segment from ``{slug}.zid.store`` — not a sandbox slug."""
    ss = normalize_identity_value(slug)
    if not ss or is_widget_sandbox_slug(ss):
        return False
    if len(ss) > 64 or " " in ss or "/" in ss:
        return False
    return all(ch.isalnum() or ch in "-_" for ch in ss)


def warm_widget_config_cache_for_store_row(row: Any) -> None:
    """Push dashboard widget snapshot to every alias cache key for this Store."""
    if row is None:
        return
    try:
        from services.widget_config_cache import update_from_dashboard_store_row

        update_from_dashboard_store_row(row)
    except Exception as exc:  # noqa: BLE001
        _log.warning("widget cache warm after identity sync skipped: %s", exc)


def _permalink_values_from_profile(profile: Any) -> set[str]:
    out: set[str] = set()
    for kind, val, _plat in collect_zid_identities_from_profile(profile):
        if kind == ALIAS_KIND_ZID_PERMALINK and val:
            out.add(normalize_identity_value(val).casefold())
    return out


def _permalink_values_from_zid_sources(
    *,
    profile: Any = None,
    manager_store: Any = None,
    store_url: Optional[str] = None,
) -> set[str]:
    out: set[str] = set()
    for src in (profile, manager_store):
        out.update(_permalink_values_from_profile(src))
    if store_url:
        pl = extract_zid_permalink_from_url(store_url)
        if pl:
            out.add(normalize_identity_value(pl).casefold())
    return out


def _append_zid_permalink_candidate(
    out: List[Tuple[str, str, Optional[str]]],
    raw: Any,
) -> None:
    if raw is None:
        return
    s = normalize_identity_value(raw)
    if not s:
        return
    from_url = extract_zid_permalink_from_url(s)
    if from_url:
        out.append((ALIAS_KIND_ZID_PERMALINK, from_url, PLATFORM_ZID))
        return
    if looks_like_zid_storefront_permalink(s):
        out.append((ALIAS_KIND_ZID_PERMALINK, s, PLATFORM_ZID))


def verify_zid_storefront_permalink_reachable(permalink: str) -> bool:
    """Best-effort: Zid storefront host responds for ``{permalink}.zid.store``."""
    ss = normalize_identity_value(permalink)
    if not looks_like_zid_storefront_permalink(ss):
        return False
    url = f"https://{ss}.zid.store/"
    try:
        import requests

        r = requests.get(
            url,
            timeout=12,
            allow_redirects=True,
            headers={"Accept": "text/html,application/json"},
        )
        return r.status_code // 100 == 2
    except Exception:  # noqa: BLE001
        return False


def log_store_identity_link_attempt(
    *,
    slug: str,
    store_id: Optional[int],
    access_token_present: bool,
    profile_ok: bool,
    manager_store_ok: bool,
    permalink_values: Iterable[str],
    matched: bool,
    reason: str,
) -> None:
    try:
        vals = ",".join(sorted({normalize_identity_value(v) for v in permalink_values if v})[:8])
        print("[STORE IDENTITY LINK]", flush=True)
        print(f"slug={(slug or '-')[:64]}", flush=True)
        print(f"store_id={store_id if store_id is not None else '-'}", flush=True)
        print(f"access_token_present={'true' if access_token_present else 'false'}", flush=True)
        print(f"profile_ok={'true' if profile_ok else 'false'}", flush=True)
        print(f"manager_store_ok={'true' if manager_store_ok else 'false'}", flush=True)
        print(f"permalink_values={vals or '-'}", flush=True)
        print(f"matched={'true' if matched else 'false'}", flush=True)
        print(f"reason={(reason or '-')[:64]}", flush=True)
    except OSError:
        pass


def fetch_zid_identity_sources_for_store(
    store: Any,
) -> Tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], Optional[str]]:
    """Profile JSON, manager/store JSON, and resolved storefront URL."""
    token = (getattr(store, "access_token", None) or "").strip()
    if not token:
        return None, None, None
    profile: Optional[dict[str, Any]] = None
    manager_store: Optional[dict[str, Any]] = None
    store_url: Optional[str] = None
    try:
        from integrations.zid_client import (
            fetch_zid_manager_profile,
            fetch_zid_manager_store_payload,
            fetch_zid_manager_store_url,
        )

        profile = fetch_zid_manager_profile(token)
        manager_store = fetch_zid_manager_store_payload(token)
        store_url = fetch_zid_manager_store_url(token)
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "zid identity source fetch skipped store_id=%s err=%s",
            getattr(store, "id", None),
            type(exc).__name__,
        )
    return profile, manager_store, store_url


def collect_zid_identities_from_manager_store(payload: Any) -> List[Tuple[str, str, Optional[str]]]:
    """Extract ids from GET /managers/account/store response."""
    return collect_zid_identities_from_profile(payload)


def permalink_belongs_to_store(
    store: Any,
    permalink: str,
    *,
    profile: Any = None,
    manager_store: Any = None,
    store_url: Optional[str] = None,
    allow_storefront_probe: bool = False,
) -> Tuple[bool, str]:
    """Decide whether ``permalink`` is this Store's Zid storefront slug."""
    ss = normalize_identity_value(permalink)
    if not ss or not looks_like_zid_storefront_permalink(ss):
        return False, "invalid_slug"
    target = ss.casefold()
    permalinks = _permalink_values_from_zid_sources(
        profile=profile,
        manager_store=manager_store,
        store_url=store_url,
    )
    if target in permalinks:
        return True, "zid_api_permalink"
    if allow_storefront_probe and verify_zid_storefront_permalink_reachable(ss):
        token = (getattr(store, "access_token", None) or "").strip()
        if token:
            return True, "storefront_probe_with_token"
    return False, "permalink_not_in_zid_api"


def register_zid_permalink_alias_for_store(
    store: Any,
    permalink: str,
    *,
    profile: Any = None,
    manager_store: Any = None,
    store_url: Optional[str] = None,
) -> bool:
    """Register ``zid_permalink`` alias and sync all Zid ids for one Store row."""
    ss = normalize_identity_value(permalink)
    sid = getattr(store, "id", None)
    if not ss or sid is None:
        return False
    sync_zid_store_identities_after_oauth(
        store,
        profile=profile,
        store_url=store_url or f"https://{ss}.zid.store/",
        warm_cache=False,
    )
    ok = register_store_identity_alias(
        store_id=int(sid),
        alias_kind=ALIAS_KIND_ZID_PERMALINK,
        alias_value=ss,
        platform=PLATFORM_ZID,
    )
    try:
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return False
    warm_widget_config_cache_for_store_row(store)
    return ok


def ensure_zid_permalink_alias_for_dashboard_store(
    store: Any,
    permalink: str,
) -> ResolveMatch:
    """
    Link a Zid storefront slug to the authenticated merchant Store row.
    Used when global link scan fails but dashboard store has a Zid token.
    """
    ss = normalize_identity_value(permalink)
    if store is None or not ss:
        return None, "not_found"
    row, via = resolve_store_row_by_identifier(ss)
    if row is not None:
        return row, via

    token = (getattr(store, "access_token", None) or "").strip()
    profile, manager_store, store_url = fetch_zid_identity_sources_for_store(store)
    belongs, belong_reason = permalink_belongs_to_store(
        store,
        ss,
        profile=profile,
        manager_store=manager_store,
        store_url=store_url,
        allow_storefront_probe=True,
    )
    log_store_identity_link_attempt(
        slug=ss,
        store_id=getattr(store, "id", None),
        access_token_present=bool(token),
        profile_ok=isinstance(profile, dict),
        manager_store_ok=isinstance(manager_store, dict),
        permalink_values=_permalink_values_from_zid_sources(
            profile=profile,
            manager_store=manager_store,
            store_url=store_url,
        ),
        matched=belongs,
        reason=belong_reason if belongs else "dashboard_link_no_match",
    )
    if not belongs:
        if not token:
            return None, "link_no_token"
        return None, "link_no_match"

    if register_zid_permalink_alias_for_store(
        store,
        ss,
        profile=profile,
        manager_store=manager_store,
        store_url=store_url,
    ):
        return resolve_store_row_by_identifier(ss)
    return None, "link_register_failed"


def attempt_link_zid_storefront_slug(identifier: str) -> ResolveMatch:
    """
    When a Zid permalink slug misses alias resolution, match connected stores
    via live Zid manager profile and register aliases (throttled per slug).
    """
    ss = normalize_identity_value(identifier)
    if not ss or not looks_like_zid_storefront_permalink(ss):
        return None, "not_found"

    mono = time.monotonic()
    with _link_lock:
        last = float(_link_attempt_mono.get(ss) or 0.0)
        if mono - last < _LINK_ATTEMPT_COOLDOWN_SEC:
            return None, "link_throttled"
        _link_attempt_mono[ss] = mono

    try:
        rows = (
            db.session.query(Store)
            .filter(Store.access_token.isnot(None))
            .filter(Store.access_token != "")
            .all()
        )
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None, "not_found"

    target_cf = ss.casefold()
    matched_rows: List[Store] = []
    tokened_rows: List[Store] = []
    last_reason = "link_no_match"
    for row in rows:
        token = (getattr(row, "access_token", None) or "").strip()
        if not token:
            continue
        tokened_rows.append(row)
        profile, manager_store, store_url = fetch_zid_identity_sources_for_store(row)
        permalinks = _permalink_values_from_zid_sources(
            profile=profile,
            manager_store=manager_store,
            store_url=store_url,
        )
        profile_ok = isinstance(profile, dict)
        manager_ok = isinstance(manager_store, dict)
        if not profile_ok and not manager_ok and not store_url:
            last_reason = "link_profile_fetch_failed"
            log_store_identity_link_attempt(
                slug=ss,
                store_id=getattr(row, "id", None),
                access_token_present=True,
                profile_ok=False,
                manager_store_ok=False,
                permalink_values=[],
                matched=False,
                reason=last_reason,
            )
            continue
        if target_cf not in permalinks:
            belongs, belong_reason = permalink_belongs_to_store(
                row,
                ss,
                profile=profile,
                manager_store=manager_store,
                store_url=store_url,
                allow_storefront_probe=False,
            )
            log_store_identity_link_attempt(
                slug=ss,
                store_id=getattr(row, "id", None),
                access_token_present=True,
                profile_ok=profile_ok,
                manager_store_ok=manager_ok,
                permalink_values=permalinks,
                matched=belongs,
                reason=belong_reason,
            )
            if not belongs:
                if not permalinks:
                    last_reason = "link_permalink_missing_in_zid_api"
                continue
            last_reason = belong_reason

        try:
            if register_zid_permalink_alias_for_store(
                row,
                ss,
                profile=profile,
                manager_store=manager_store,
                store_url=store_url or f"https://{ss}.zid.store/",
            ):
                matched_rows.append(row)
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "storefront slug link sync skipped store_id=%s err=%s",
                getattr(row, "id", None),
                type(exc).__name__,
            )

    if len(matched_rows) == 1:
        return resolve_store_row_by_identifier(ss)

    if len(matched_rows) > 1:
        _log.warning(
            "[STORE IDENTITY LINK AMBIGUOUS] slug=%s matches=%s",
            ss[:64],
            [getattr(r, "id", None) for r in matched_rows],
        )
        return None, "link_ambiguous"

    if len(tokened_rows) == 0:
        return None, "link_no_token"

    if len(tokened_rows) == 1:
        only = tokened_rows[0]
        profile, manager_store, store_url = fetch_zid_identity_sources_for_store(only)
        belongs, belong_reason = permalink_belongs_to_store(
            only,
            ss,
            profile=profile,
            manager_store=manager_store,
            store_url=store_url,
            allow_storefront_probe=True,
        )
        if belongs and register_zid_permalink_alias_for_store(
            only,
            ss,
            profile=profile,
            manager_store=manager_store,
            store_url=store_url or f"https://{ss}.zid.store/",
        ):
            return resolve_store_row_by_identifier(ss)
        last_reason = belong_reason if not belongs else "link_register_failed"

    try:
        print(f"[STORE IDENTITY LINK FAIL] slug={ss[:64]} reason={last_reason}", flush=True)
    except OSError:
        pass
    return None, last_reason


def resolve_store_row_for_storefront_api(
    identifier: str,
    *,
    dashboard_store: Any = None,
) -> ResolveMatch:
    """Identity resolve with Zid permalink link attempt for storefront hot paths."""
    row, via = resolve_store_row_by_identifier(identifier)
    if row is not None:
        return row, via
    ss = normalize_identity_value(identifier)
    if dashboard_store is not None and ss and looks_like_zid_storefront_permalink(ss):
        row, via = ensure_zid_permalink_alias_for_dashboard_store(dashboard_store, ss)
        if row is not None:
            return row, via
    return attempt_link_zid_storefront_slug(identifier)


def log_store_identity_resolve(
    *,
    identifier: str,
    matched_store_id: Optional[int],
    matched_zid: Optional[str],
    matched_via: str,
    found: bool,
) -> None:
    try:
        print("[STORE IDENTITY RESOLVE]", flush=True)
        print(f"identifier={(identifier or '-')[:128]}", flush=True)
        print(
            f"matched_store_id={matched_store_id if matched_store_id is not None else '-'}",
            flush=True,
        )
        print(f"matched_zid={(matched_zid or '-')[:128]}", flush=True)
        print(f"matched_via={(matched_via or '-')[:64]}", flush=True)
        print(f"found={'true' if found else 'false'}", flush=True)
    except OSError:
        pass


def _row_from_alias(alias: StoreIdentityAlias) -> Optional[Store]:
    try:
        sid = int(getattr(alias, "store_id", 0) or 0)
    except (TypeError, ValueError):
        return None
    if sid <= 0:
        return None
    try:
        return db.session.get(Store, sid)
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None


def resolve_store_row_by_identifier(
    identifier: str,
    *,
    session: Any = None,
) -> ResolveMatch:
    """
    Resolve any platform/dashboard/widget slug to the canonical Store row.

    Order: alias table → direct ``stores.zid_store_id`` (legacy parity).
    """
    ss = normalize_identity_value(identifier)
    if not ss:
        log_store_identity_resolve(
            identifier="-",
            matched_store_id=None,
            matched_zid=None,
            matched_via="empty_identifier",
            found=False,
        )
        return None, "empty_identifier"

    sess = session or db.session
    try:
        alias = (
            sess.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.alias_value == ss)
            .first()
        )
    except (SQLAlchemyError, OSError):
        sess.rollback()
        alias = None

    if alias is not None:
        row = _row_from_alias(alias) if session is None else sess.get(Store, alias.store_id)
        if row is not None:
            zid = canonical_store_slug_on_row(row)
            log_store_identity_resolve(
                identifier=ss,
                matched_store_id=getattr(row, "id", None),
                matched_zid=zid,
                matched_via=f"alias:{alias.alias_kind}",
                found=True,
            )
            return row, f"alias:{alias.alias_kind}"

    try:
        row = sess.query(Store).filter(Store.zid_store_id == ss).first()
    except (SQLAlchemyError, OSError):
        sess.rollback()
        row = None

    if row is not None:
        zid = canonical_store_slug_on_row(row)
        log_store_identity_resolve(
            identifier=ss,
            matched_store_id=getattr(row, "id", None),
            matched_zid=zid,
            matched_via="cartflow_zid_direct",
            found=True,
        )
        return row, "cartflow_zid_direct"

    log_store_identity_resolve(
        identifier=ss,
        matched_store_id=None,
        matched_zid=None,
        matched_via="not_found",
        found=False,
    )
    return None, "not_found"


def resolve_canonical_store_slug(identifier: str) -> Optional[str]:
    """Map any alias/slug to ``stores.zid_store_id`` for recovery_key normalization."""
    row, _via = resolve_store_row_by_identifier(identifier)
    return canonical_store_slug_on_row(row)


def list_public_cache_keys_for_store_row(row: Any) -> List[str]:
    """All slug strings that should share widget-config cache for this Store."""
    if row is None:
        return []
    keys: List[str] = []
    seen: set[str] = set()
    zid = canonical_store_slug_on_row(row)
    if zid:
        keys.append(zid)
        seen.add(zid.casefold())
    sid = getattr(row, "id", None)
    if sid is not None:
        try:
            aliases = (
                db.session.query(StoreIdentityAlias.alias_value)
                .filter(StoreIdentityAlias.store_id == int(sid))
                .all()
            )
            for (av,) in aliases:
                v = normalize_identity_value(av)
                if v and v.casefold() not in seen:
                    keys.append(v)
                    seen.add(v.casefold())
        except (SQLAlchemyError, OSError):
            db.session.rollback()
    return keys


def register_store_identity_alias(
    *,
    store_id: int,
    alias_kind: str,
    alias_value: str,
    platform: Optional[str] = None,
    session: Any = None,
) -> bool:
    """Register alias; never reassign an existing alias to a different store."""
    val = normalize_identity_value(alias_value)
    kind = (alias_kind or "").strip()[:64]
    if not val or not kind or int(store_id) <= 0:
        return False

    sess = session or db.session
    try:
        existing = (
            sess.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.alias_value == val)
            .first()
        )
    except (SQLAlchemyError, OSError):
        sess.rollback()
        return False

    if existing is not None:
        if int(existing.store_id) == int(store_id):
            return True
        _log.warning(
            "[STORE IDENTITY ALIAS CONFLICT] alias=%s kind=%s owner=%s attempted_store=%s",
            val[:64],
            kind,
            existing.store_id,
            store_id,
        )
        return False

    row = StoreIdentityAlias(
        store_id=int(store_id),
        alias_kind=kind,
        alias_value=val,
        platform=(platform or "").strip()[:32] or None,
    )
    try:
        sess.add(row)
        sess.flush()
        _log.info(
            "[STORE IDENTITY ALIAS REGISTERED] store_id=%s kind=%s value=%s platform=%s",
            store_id,
            kind,
            val[:64],
            platform or "-",
        )
        return True
    except IntegrityError:
        sess.rollback()
        return False
    except (SQLAlchemyError, OSError):
        sess.rollback()
        return False


def ensure_cartflow_zid_alias_for_store(row: Any, *, session: Any = None) -> None:
    """Mirror ``stores.zid_store_id`` into alias table."""
    if row is None:
        return
    zid = canonical_store_slug_on_row(row)
    sid = getattr(row, "id", None)
    if not zid or sid is None:
        return
    register_store_identity_alias(
        store_id=int(sid),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=zid,
        platform=PLATFORM_CARTFLOW,
        session=session,
    )


def register_identity_aliases(
    store_id: int,
    aliases: Iterable[Tuple[str, str, Optional[str]]],
    *,
    session: Any = None,
) -> int:
    """Bulk register ``(alias_kind, alias_value, platform)`` tuples."""
    n = 0
    for kind, value, platform in aliases:
        if register_store_identity_alias(
            store_id=store_id,
            alias_kind=kind,
            alias_value=value,
            platform=platform,
            session=session,
        ):
            n += 1
    return n


def collect_zid_identities_from_profile(profile: Any) -> List[Tuple[str, str, Optional[str]]]:
    """Extract Zid store ids from manager profile JSON."""
    out: List[Tuple[str, str, Optional[str]]] = []
    if not isinstance(profile, dict):
        return out

    def _walk(obj: Any, path: tuple[str, ...]) -> Any:
        cur: Any = obj
        for p in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
        return cur

    store_obj = _walk(profile, ("data", "store"))
    if not isinstance(store_obj, dict):
        store_obj = _walk(profile, ("store",))
    if not isinstance(store_obj, dict):
        store_obj = _walk(profile, ("data",))
    if not isinstance(store_obj, dict):
        store_obj = {}

    numeric = store_obj.get("id")
    if numeric is not None and str(numeric).strip():
        out.append((ALIAS_KIND_ZID_NUMERIC_ID, str(numeric).strip(), PLATFORM_ZID))

    uuid_val = store_obj.get("uuid")
    if uuid_val is not None and str(uuid_val).strip():
        out.append((ALIAS_KIND_ZID_UUID, str(uuid_val).strip(), PLATFORM_ZID))

    for url_key in ("url", "permalink", "domain", "store_url", "link"):
        raw_url = store_obj.get(url_key)
        if isinstance(raw_url, str) and raw_url.strip():
            _append_zid_permalink_candidate(out, raw_url.strip())

    for slug_key in (
        "permalink",
        "username",
        "slug",
        "subdomain",
        "store_username",
        "store_permalink",
    ):
        raw_slug = store_obj.get(slug_key)
        if isinstance(raw_slug, str) and raw_slug.strip():
            _append_zid_permalink_candidate(out, raw_slug.strip())

    return out


def sync_zid_store_identities_after_oauth(
    store: Any,
    *,
    token_response: Optional[dict[str, Any]] = None,
    prior_zid: Optional[str] = None,
    store_url: Optional[str] = None,
    profile: Optional[dict[str, Any]] = None,
    warm_cache: bool = True,
) -> None:
    """
    Register all known Zid identifiers for a Store after OAuth or storefront verify.
    Preserves prior signup slug as alias when ``zid_store_id`` changes.
    """
    if store is None:
        return
    sid = getattr(store, "id", None)
    if sid is None:
        return

    aliases: List[Tuple[str, str, Optional[str]]] = []

    old_zid = normalize_identity_value(prior_zid or "")
    current_zid = canonical_store_slug_on_row(store) or ""
    if old_zid and old_zid.casefold() != current_zid.casefold():
        aliases.append((ALIAS_KIND_CARTFLOW_ZID, old_zid, PLATFORM_CARTFLOW))

    if current_zid:
        aliases.append((ALIAS_KIND_CARTFLOW_ZID, current_zid, PLATFORM_CARTFLOW))

    if isinstance(token_response, dict):
        from integrations.zid_client import parse_zid_store_id_from_token

        for key in ("zid_store_id", "store_id", "merchant_id"):
            v = token_response.get(key)
            if v is not None and str(v).strip():
                aliases.append(
                    (ALIAS_KIND_ZID_NUMERIC_ID, str(v).strip(), PLATFORM_ZID)
                )
        nested = token_response.get("store")
        if isinstance(nested, dict):
            if nested.get("id") is not None:
                aliases.append(
                    (
                        ALIAS_KIND_ZID_NUMERIC_ID,
                        str(nested["id"]).strip(),
                        PLATFORM_ZID,
                    )
                )
            if nested.get("uuid") is not None:
                aliases.append(
                    (ALIAS_KIND_ZID_UUID, str(nested["uuid"]).strip(), PLATFORM_ZID)
                )
        tok_zid = parse_zid_store_id_from_token(token_response)
        if tok_zid:
            aliases.append((ALIAS_KIND_ZID_NUMERIC_ID, tok_zid, PLATFORM_ZID))

    if profile is None:
        access = (getattr(store, "access_token", None) or "").strip()
        if access:
            profile, manager_store_payload, manager_store_url = (
                fetch_zid_identity_sources_for_store(store)
            )
        else:
            manager_store_payload = None
            manager_store_url = None
    else:
        access = (getattr(store, "access_token", None) or "").strip()
        manager_store_payload = None
        manager_store_url = None
        if access:
            _prof, manager_store_payload, manager_store_url = (
                fetch_zid_identity_sources_for_store(store)
            )

    if isinstance(profile, dict):
        aliases.extend(collect_zid_identities_from_profile(profile))
    if isinstance(manager_store_payload, dict):
        aliases.extend(collect_zid_identities_from_manager_store(manager_store_payload))

    effective_store_url = store_url or manager_store_url
    if effective_store_url:
        permalink = extract_zid_permalink_from_url(effective_store_url)
        if permalink:
            aliases.append((ALIAS_KIND_ZID_PERMALINK, permalink, PLATFORM_ZID))

    # Deduplicate by value
    seen: set[str] = set()
    unique: List[Tuple[str, str, Optional[str]]] = []
    for kind, val, plat in aliases:
        vv = normalize_identity_value(val)
        if not vv or vv.casefold() in seen:
            continue
        seen.add(vv.casefold())
        unique.append((kind, vv, plat))

    n = register_identity_aliases(int(sid), unique)
    _log.info(
        "[STORE IDENTITY ZID SYNC] store_id=%s zid=%s aliases_registered=%s",
        sid,
        (current_zid or "-")[:64],
        n,
    )
    if warm_cache:
        warm_widget_config_cache_for_store_row(store)


def sync_zid_identities_for_dashboard_store(row: Any) -> None:
    """Refresh Zid alias rows from live profile before dashboard cache invalidation."""
    if row is None:
        return
    token = (getattr(row, "access_token", None) or "").strip()
    if not token:
        return
    sync_zid_store_identities_after_oauth(row, warm_cache=False)
    profile, manager_store, store_url = fetch_zid_identity_sources_for_store(row)
    for pl in _permalink_values_from_zid_sources(
        profile=profile,
        manager_store=manager_store,
        store_url=store_url,
    ):
        register_store_identity_alias(
            store_id=int(row.id),
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=pl,
            platform=PLATFORM_ZID,
        )
    try:
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()


def backfill_store_identity_aliases_from_stores(*, session: Any = None) -> int:
    """Ensure every Store with ``zid_store_id`` has a cartflow_zid alias row."""
    from services.db_ready_diag_v1 import db_ready_substage  # noqa: PLC0415

    sess = session or db.session
    n = 0
    try:
        with db_ready_substage("identity_backfill_query"):
            rows = sess.query(Store).filter(Store.zid_store_id.isnot(None)).all()
    except (SQLAlchemyError, OSError):
        sess.rollback()
        return 0
    with db_ready_substage("identity_backfill_register"):
        for row in rows:
            zid = canonical_store_slug_on_row(row)
            sid = getattr(row, "id", None)
            if not zid or sid is None:
                continue
            if register_store_identity_alias(
                store_id=int(sid),
                alias_kind=ALIAS_KIND_CARTFLOW_ZID,
                alias_value=zid,
                platform=PLATFORM_CARTFLOW,
                session=sess,
            ):
                n += 1
    if session is None:
        try:
            sess.commit()
        except (SQLAlchemyError, OSError):
            sess.rollback()
    return n


def sync_connected_platform_identities(*, session: Any = None) -> int:
    """
    For platform-connected stores, refresh Zid/Salla alias rows from live profile/API.
    Called once per process warm — not a request-time fallback.
    """
    from services.db_ready_diag_v1 import db_ready_substage  # noqa: PLC0415

    sess = session or db.session
    n = 0
    try:
        with db_ready_substage("platform_sync_query"):
            rows = (
                sess.query(Store)
                .filter(Store.access_token.isnot(None))
                .filter(Store.access_token != "")
                .all()
            )
    except (SQLAlchemyError, OSError):
        sess.rollback()
        return 0
    with db_ready_substage("platform_sync_loop"):
        for row in rows:
            token = (getattr(row, "access_token", None) or "").strip()
            if not token:
                continue
            src = (getattr(row, "integration_source", None) or "").strip().lower()
            if src.startswith("zid") or src == "":
                try:
                    sync_zid_store_identities_after_oauth(row)
                    n += 1
                except Exception as exc:  # noqa: BLE001
                    _log.warning(
                        "platform identity sync skipped store_id=%s err=%s",
                        getattr(row, "id", None),
                        type(exc).__name__,
                    )
    return n


__all__ = [
    "ALIAS_KIND_CARTFLOW_ZID",
    "ALIAS_KIND_SALLA_STORE_ID",
    "ALIAS_KIND_ZID_NUMERIC_ID",
    "ALIAS_KIND_ZID_PERMALINK",
    "ALIAS_KIND_ZID_UUID",
    "PLATFORM_CARTFLOW",
    "PLATFORM_SALLA",
    "PLATFORM_ZID",
    "WIDGET_SANDBOX_SLUGS",
    "attempt_link_zid_storefront_slug",
    "backfill_store_identity_aliases_from_stores",
    "canonical_store_slug_on_row",
    "collect_zid_identities_from_manager_store",
    "collect_zid_identities_from_profile",
    "ensure_cartflow_zid_alias_for_store",
    "ensure_zid_permalink_alias_for_dashboard_store",
    "extract_zid_permalink_from_url",
    "fetch_zid_identity_sources_for_store",
    "is_widget_sandbox_slug",
    "list_public_cache_keys_for_store_row",
    "looks_like_zid_storefront_permalink",
    "normalize_identity_value",
    "permalink_belongs_to_store",
    "register_identity_aliases",
    "register_store_identity_alias",
    "register_zid_permalink_alias_for_store",
    "resolve_canonical_store_slug",
    "resolve_store_row_by_identifier",
    "resolve_store_row_for_storefront_api",
    "sync_connected_platform_identities",
    "sync_zid_identities_for_dashboard_store",
    "sync_zid_store_identities_after_oauth",
    "verify_zid_storefront_permalink_reachable",
    "warm_widget_config_cache_for_store_row",
]
