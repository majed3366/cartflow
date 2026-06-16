# -*- coding: utf-8 -*-
"""Read-only: check Store.access_token presence for cartflow-42b491 (no token output)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_dotenv() -> None:
    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def main() -> int:
    _load_dotenv()
    slug = (os.getenv("ZID_PROBE_STORE_SLUG") or "cartflow-42b491").strip()
    partner = (os.getenv("ZID_API_AUTHORIZATION") or "").strip()
    if not (os.getenv("DATABASE_URL") or "").strip():
        print("ERROR: DATABASE_URL not set — cannot read Store.access_token from DB")
        print(f"partner_auth_configured={'yes' if partner else 'no'}")
        return 2

    from extensions import db, init_database
    from models import Store
    from services.merchant_store_connection_v1 import is_merchant_store_platform_connected

    init_database()
    row = (
        db.session.query(Store)
        .filter(Store.zid_store_id == slug)
        .order_by(Store.id.desc())
        .first()
    )
    if row is None:
        row = (
            db.session.query(Store)
            .filter(Store.zid_store_id.ilike(f"%{slug}%"))
            .order_by(Store.id.desc())
            .first()
        )
    if row is None:
        print(f"store_not_found slug={slug}")
        return 1

    token_present = bool((getattr(row, "access_token", None) or "").strip())
    auth_token_present = bool((getattr(row, "zid_authorization_token", None) or "").strip())
    partner_or_store_auth = bool(partner) or auth_token_present
    print(f"store_id={getattr(row, 'id', None)}")
    print(f"zid_store_id={getattr(row, 'zid_store_id', None)!r}")
    print(f"integration_source={getattr(row, 'integration_source', None)!r}")
    print(f"connected_at={getattr(row, 'connected_at', None)}")
    print(f"token_present={'yes' if token_present else 'no'}")
    print(f"authorization_token_present={'yes' if auth_token_present else 'no'}")
    print(f"platform_connected={'yes' if is_merchant_store_platform_connected(row) else 'no'}")
    print(f"partner_auth_configured={'yes' if partner else 'no'}")
    print(
        "webhook_registration_ready="
        + ("yes" if token_present and partner_or_store_auth else "no")
    )
    if not token_present:
        print("missing_credential=store_access_token (Store.access_token empty)")
    if not partner_or_store_auth:
        print(
            "missing_credential=zid_authorization "
            "(Store.zid_authorization_token empty and ZID_API_AUTHORIZATION unset)"
        )
    db.session.remove()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
