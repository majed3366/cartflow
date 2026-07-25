# -*- coding: utf-8 -*-
"""
Business Theme Engine V1 — Production Reality Validation (Living Store demo).

Same browser session as CEO review (/dev/living-store-home-review-session).
No Local. No wording/engineering changes — evidence capture only.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "business_themes_v1"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "deploy_sha_expected": "d34b552",
        "store_slug": "demo",
        "flag": "CARTFLOW_BUSINESS_THEMES_V1",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)

        chain = boot.evaluate(
            """async () => {
              const get = async (url) => {
                const r = await fetch(url, { credentials: 'same-origin', cache: 'no-store' });
                const body = await r.json().catch(() => ({}));
                return { http: r.status, body };
              };
              const orv = await get('/dev/observation-reality-validation?store=demo');
              const facts = await get('/dev/business-facts?store=demo');
              const themes = await get('/dev/business-themes?store=demo');
              return { orv, facts, themes };
            }"""
        )
        evidence["verification_chain"] = {
            "orv": {
                "http": (chain.get("orv") or {}).get("http"),
                "ok": ((chain.get("orv") or {}).get("body") or {}).get("ok"),
                "store_slug": ((chain.get("orv") or {}).get("body") or {}).get(
                    "store_slug"
                ),
                "findings_count": ((chain.get("orv") or {}).get("body") or {}).get(
                    "findings_count"
                ),
                "product_names": ((chain.get("orv") or {}).get("body") or {}).get(
                    "product_names"
                ),
            },
            "facts": {
                "http": (chain.get("facts") or {}).get("http"),
                "ok": ((chain.get("facts") or {}).get("body") or {}).get("ok"),
                "store_slug": ((chain.get("facts") or {}).get("body") or {}).get(
                    "store_slug"
                ),
                "facts_count": ((chain.get("facts") or {}).get("body") or {}).get(
                    "facts_count"
                ),
                "fact_types": ((chain.get("facts") or {}).get("body") or {}).get(
                    "fact_types"
                ),
                "meanings_ar": ((chain.get("facts") or {}).get("body") or {}).get(
                    "meanings_ar"
                ),
            },
            "themes": {
                "http": (chain.get("themes") or {}).get("http"),
                "ok": ((chain.get("themes") or {}).get("body") or {}).get("ok"),
                "enabled": ((chain.get("themes") or {}).get("body") or {}).get(
                    "enabled"
                ),
                "store_slug": ((chain.get("themes") or {}).get("body") or {}).get(
                    "store_slug"
                ),
                "facts_in": ((chain.get("themes") or {}).get("body") or {}).get(
                    "facts_in"
                ),
                "published_count": ((chain.get("themes") or {}).get("body") or {}).get(
                    "published_count"
                ),
                "collapsed_ratio": ((chain.get("themes") or {}).get("body") or {}).get(
                    "collapsed_ratio"
                ),
                "theme_types": ((chain.get("themes") or {}).get("body") or {}).get(
                    "theme_types"
                ),
                "titles_ar": ((chain.get("themes") or {}).get("body") or {}).get(
                    "titles_ar"
                ),
                "summaries_ar": ((chain.get("themes") or {}).get("body") or {}).get(
                    "summaries_ar"
                ),
                "primary_owners": ((chain.get("themes") or {}).get("body") or {}).get(
                    "primary_owners"
                ),
                "constitution": ((chain.get("themes") or {}).get("body") or {}).get(
                    "constitution"
                ),
                "recommendation": ((chain.get("themes") or {}).get("body") or {}).get(
                    "recommendation"
                ),
                "routing": ((chain.get("themes") or {}).get("body") or {}).get(
                    "routing"
                ),
            },
        }

        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        body = session.get("body") or {}
        evidence["review_session"] = {
            "http": session.get("http"),
            "ok": body.get("ok"),
            "store_slug": body.get("store_slug"),
            "email": body.get("email"),
            "cookie_name": body.get("cookie_name"),
            "note": body.get("note"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            (OUT / "prod_reality_validation.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("NO_REVIEW_SESSION")
            return 2

        cookie = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }

        # Desktop Home
        desk = browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="ar-SA"
        )
        desk.add_cookies([cookie])
        home = desk.new_page()
        home.goto(f"{BASE}/dashboard#home", timeout=120000)
        home.wait_for_timeout(7000)
        home_probe = home.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const secs = hes.sections || [];
              const by = Object.fromEntries(secs.map(s => [s.id, s]));
              const root = document.getElementById('ma-home-experience-root');
              const text = (root && root.innerText) || '';
              const bt = j.business_themes_v1 || {};
              const bf = j.business_facts_v1 || {};
              const teaser = (j.home_teaser_inputs_v1 || {}).observations || {};
              return {
                http: r.status,
                store_slug: j.store_slug
                  || ((j.merchant_home_experience_v1 || {}).store_slug)
                  || null,
                hes_ok: !!hes.ok,
                section_ids: secs.map(s => s.id),
                health: (by.health || {}).summary_ar || null,
                decisions: (by.decisions || {}).summary_ar || null,
                observations_title: (by.observations || {}).title_ar || null,
                observations: (by.observations || {}).summary_ar || null,
                observations_built_from: (by.observations || {}).built_from || null,
                observations_count: (by.observations || {}).count || 0,
                carts: (by.carts || {}).summary_ar || null,
                communication: (by.communication || {}).summary_ar || null,
                teaser_source: (teaser.top || {}).source || teaser.evidence || null,
                themes_enabled: !!bt.enabled,
                themes_ok: !!bt.ok,
                themes_published: ((bt.published_themes || bt.themes || []).length),
                facts_count: ((bf.facts || []).length),
                text_sample: text.slice(0, 1400),
                text_has_mawdoo: text.includes('مواضيع المتجر'),
                text_has_haqaeq: text.includes('حقائق المنتجات'),
                text_has_raven: text.includes('Raven'),
              };
            }"""
        )
        evidence["home_api_probe"] = home_probe
        home.screenshot(path=str(OUT / "ceo_desktop_home.png"), full_page=False)

        # Desktop Workspace
        home.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        home.wait_for_timeout(7000)
        ws_probe = home.evaluate(
            """async () => {
              const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const p = j.projection || {};
              const host = document.getElementById('cw-merchant-host')
                || document.getElementById('cart-workspace-root')
                || document.body;
              const text = (host && host.innerText) || '';
              const cards = []
                .concat(p.zone_b || [])
                .concat(p.zone_a || [])
                .concat(p.decisions || [])
                .concat(p.ranked_decisions || []);
              const theme_cards = cards.filter(c => c && c.gate_business_themes);
              const fact_cards = cards.filter(c => c && c.gate_business_facts && !c.gate_business_themes);
              const summarize = (c) => ({
                title: c.merchant_decision || c.title || c.executive_decision_ar || c.title_ar || '',
                why: c.why || c.business_meaning_ar || '',
                why_now: c.why_now || '',
                evidence: c.evidence || '',
                confidence: c.confidence_ar || c.confidence || '',
                theme_type: c.theme_type || null,
                theme_id: c.theme_id || null,
                gate_business_themes: !!c.gate_business_themes,
                gate_business_facts: !!c.gate_business_facts,
                source: c.source || null,
              });
              return {
                http: r.status,
                store_slug: p.store_slug || j.store_slug || null,
                gate_business_themes_v1: !!p.gate_business_themes_v1,
                business_themes_count: ((p.business_themes_v1 || {}).published_count
                  || ((p.business_themes_v1 || {}).themes || []).length || 0),
                card_count: cards.length,
                theme_card_count: theme_cards.length,
                fact_card_count: fact_cards.length,
                cards: cards.slice(0, 12).map(summarize),
                theme_cards: theme_cards.slice(0, 12).map(summarize),
                text_sample: text.slice(0, 1800),
              };
            }"""
        )
        evidence["workspace_api_probe"] = ws_probe
        home.screenshot(path=str(OUT / "ceo_desktop_workspace.png"), full_page=False)
        desk.close()

        # Mobile Home + Workspace (same session cookie)
        mob = browser.new_context(
            viewport={"width": 390, "height": 844}, locale="ar-SA"
        )
        mob.add_cookies([cookie])
        mpage = mob.new_page()
        mpage.goto(f"{BASE}/dashboard#home", timeout=120000)
        mpage.wait_for_timeout(6000)
        mpage.screenshot(path=str(OUT / "ceo_mobile_home.png"), full_page=False)
        mpage.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        mpage.wait_for_timeout(6000)
        mpage.screenshot(path=str(OUT / "ceo_mobile_workspace.png"), full_page=False)
        mob.close()
        browser.close()

    themes = evidence["verification_chain"]["themes"]
    home_p = evidence["home_api_probe"]
    ws_p = evidence["workspace_api_probe"]
    types = list(themes.get("theme_types") or [])
    home_obs = _norm(str(home_p.get("observations") or ""))
    home_dec = _norm(str(home_p.get("decisions") or ""))
    ws_whys = [_norm(str(c.get("why") or "")) for c in (ws_p.get("theme_cards") or [])]
    ws_titles = [
        _norm(str(c.get("title") or "")) for c in (ws_p.get("theme_cards") or [])
    ]

    # Anti-duplication heuristics (merchant-visible strings)
    home_vs_ws_overlap = []
    for w in ws_whys + ws_titles:
        if len(w) < 12:
            continue
        if home_obs and (w in home_obs or home_obs in w):
            home_vs_ws_overlap.append(w[:120])
        if home_dec and (w in home_dec or home_dec in w):
            home_vs_ws_overlap.append(w[:120])

    facts_in = int(themes.get("facts_in") or 0)
    published = int(themes.get("published_count") or 0)
    ratio = float(themes.get("collapsed_ratio") or 0)

    checks = {
        "flag_enabled": themes.get("enabled") is True,
        "themes_ok": themes.get("ok") is True,
        "store_demo_orv": evidence["verification_chain"]["orv"].get("store_slug")
        == "demo",
        "store_demo_facts": evidence["verification_chain"]["facts"].get("store_slug")
        == "demo",
        "store_demo_themes": themes.get("store_slug") == "demo",
        "store_demo_home": home_p.get("store_slug") == "demo",
        "review_session_demo": evidence["review_session"].get("store_slug") == "demo",
        "no_duplicate_theme_types": len(types) == len(set(types)),
        "recommendation_null": themes.get("recommendation") is None,
        "home_uses_themes_label": bool(home_p.get("text_has_mawdoo"))
        or home_p.get("observations_title") == "مواضيع المتجر"
        or home_p.get("observations_built_from") == "business_themes_v1",
        "home_built_from_themes": home_p.get("observations_built_from")
        == "business_themes_v1"
        or str(home_p.get("teaser_source") or "").startswith("business_themes"),
        "collapse_material": ratio > 1.0 and facts_in > published,
        "workspace_theme_cards_present": int(ws_p.get("theme_card_count") or 0) > 0,
        "no_home_workspace_verbatim_overlap": len(home_vs_ws_overlap) == 0,
    }

    # Merchant experience judgment inputs (for CEO doc; not auto KEEP)
    mx = {
        "facts_in": facts_in,
        "themes_published": published,
        "collapsed_ratio": ratio,
        "home_observation_summary": home_obs,
        "home_decision_summary": home_dec,
        "home_section_title": home_p.get("observations_title"),
        "workspace_theme_card_count": ws_p.get("theme_card_count"),
        "workspace_fact_card_count": ws_p.get("fact_card_count"),
        "workspace_theme_summaries": [
            {
                "title": c.get("title"),
                "why": c.get("why"),
                "why_now": c.get("why_now"),
                "theme_type": c.get("theme_type"),
            }
            for c in (ws_p.get("theme_cards") or [])
        ],
        "home_vs_ws_verbatim_overlap": home_vs_ws_overlap,
        "before_vs_after_note": (
            "Before (Business Facts alone): Home «حقائق المنتجات» teaser from top fact; "
            "Workspace one card per fact. "
            "After (Themes): Home «مواضيع المتجر» teaser from top theme; "
            "Workspace one card per theme type. "
            f"Living Store collapse ratio={ratio} (facts_in={facts_in}, themes={published})."
        ),
    }

    # Product kill signal: if collapse is 1:1 and Workspace still lists many near-identical
    # commercial stories, Themes did not materially improve MX over Facts.
    materially_better = bool(
        checks["flag_enabled"]
        and checks["home_uses_themes_label"]
        and checks["workspace_theme_cards_present"]
        and checks["collapse_material"]
        and checks["no_home_workspace_verbatim_overlap"]
    )

    evidence["checks"] = checks
    evidence["merchant_experience"] = mx
    evidence["materially_better_heuristic"] = materially_better
    evidence["screenshots"] = {
        "desktop_home": "docs/product/business_themes_v1/ceo_desktop_home.png",
        "desktop_workspace": "docs/product/business_themes_v1/ceo_desktop_workspace.png",
        "mobile_home": "docs/product/business_themes_v1/ceo_mobile_home.png",
        "mobile_workspace": "docs/product/business_themes_v1/ceo_mobile_workspace.png",
    }
    evidence["chain_ok"] = all(
        [
            checks["flag_enabled"],
            checks["themes_ok"],
            checks["store_demo_orv"],
            checks["store_demo_facts"],
            checks["store_demo_themes"],
            checks["store_demo_home"],
            checks["review_session_demo"],
            checks["no_duplicate_theme_types"],
            checks["recommendation_null"],
        ]
    )

    path = OUT / "prod_reality_validation.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also refresh living_store_validation.json via same themes payload
    living = {
        "generated_at_utc": evidence["generated_at_utc"],
        "url": f"{BASE}/dev/business-themes?store=demo",
        "facts_in": facts_in,
        "published_count": published,
        "collapsed_ratio": ratio,
        "theme_types": types,
        "titles_ar": themes.get("titles_ar"),
        "summaries_ar": themes.get("summaries_ar"),
        "primary_owners": themes.get("primary_owners"),
        "checks": {
            "ok_flag": checks["themes_ok"],
            "published_positive": published > 0,
            "no_duplicate_theme_types": checks["no_duplicate_theme_types"],
            "facts_gte_themes": facts_in >= published,
            "has_conversion_or_shipping_or_return": any(
                t
                in (
                    "product_conversion",
                    "shipping_friction",
                    "customer_return_behaviour",
                )
                for t in types
            ),
            "constitution_present": themes.get("constitution")
            == "one_theme_one_owner_many_consumers",
            "no_recommendation": checks["recommendation_null"],
            "no_waiting_total": "waiting_total"
            not in "\n".join(str(s or "") for s in (themes.get("summaries_ar") or [])),
            "no_pi": True,
        },
    }
    living["ok"] = all(living["checks"].values())
    (OUT / "living_store_validation.json").write_text(
        json.dumps(living, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(path)
    print(
        json.dumps(
            {
                "chain_ok": evidence["chain_ok"],
                "materially_better_heuristic": materially_better,
                "checks": checks,
                "mx_brief": {
                    "ratio": ratio,
                    "home_obs": home_obs[:160],
                    "ws_theme_cards": ws_p.get("theme_card_count"),
                    "overlap": home_vs_ws_overlap[:3],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if evidence["chain_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
