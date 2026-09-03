# -*- coding: utf-8 -*-
"""Isolated synthetic merchant world — simulation-only, never production truth."""
from __future__ import annotations

import hashlib
from typing import Any

from services.revenue_reality_validation_v1.contracts_v1 import (
    CHANNELS,
    SIMULATION_DAYS,
    SIMULATION_SEED,
    SIMULATION_STORE_SLUG,
    VALIDATION_VERSION_V1,
)

# Explicit simulation-only cost for Scenario D lab economics — NOT a production contract.
_SIM_ONLY_COST_NOTE = (
    "SIMULATION-ONLY cost for discount economics lab. "
    "MARGIN INTELLIGENCE remains a DATA GAP in production architecture."
)


def _h(seed: int, *parts: Any) -> int:
    raw = f"{seed}|" + "|".join(str(p) for p in parts)
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _jitter(seed: int, key: str, base: float, spread: float = 0.12) -> float:
    u = (_h(seed, key) % 1000) / 1000.0
    return max(0.0, base * (1.0 - spread + 2.0 * spread * u))


def product_catalog_v1() -> list[dict[str, Any]]:
    """10 products with distinct commercial roles for scenarios A–H."""
    return [
        {
            "product_id": "rrv_p01_discovery",
            "name_ar": "زيت الأرغان المركّز",
            "category": "عناية",
            "sale_price": 189.0,
            "scenario_roles": ["A_discovery"],
            "profile": "discovery_gem",
        },
        {
            "product_id": "rrv_p02_friction",
            "name_ar": "طقم أدوات المطبخ الفاخر",
            "category": "منزل",
            "sale_price": 420.0,
            "scenario_roles": ["B_high_interest_low_conversion"],
            "profile": "shipping_friction",
        },
        {
            "product_id": "rrv_p03_price",
            "name_ar": "سماعات لاسلكية برو",
            "category": "إلكترونيات",
            "sale_price": 349.0,
            "scenario_roles": ["C_price_sensitive"],
            "profile": "price_hesitation",
        },
        {
            "product_id": "rrv_p04_discount_trap",
            "name_ar": "عطر مسائي محدود",
            "category": "عطور",
            "sale_price": 280.0,
            "sim_only_unit_cost": 210.0,  # SIMULATION-ONLY
            "scenario_roles": ["D_discount_destroys_value"],
            "profile": "discount_trap",
        },
        {
            "product_id": "rrv_p05_bundle_a",
            "name_ar": "ماكينة قهوة منزلية",
            "category": "مطبخ",
            "sale_price": 599.0,
            "scenario_roles": ["E_bundle_cross_sell", "G_retention"],
            "profile": "bundle_anchor",
        },
        {
            "product_id": "rrv_p06_bundle_b",
            "name_ar": "حليب لوز عضوي (علبة)",
            "category": "مطبخ",
            "sale_price": 48.0,
            "scenario_roles": ["E_bundle_cross_sell", "G_retention"],
            "profile": "bundle_companion",
        },
        {
            "product_id": "rrv_p07_channel",
            "name_ar": "حقيبة يومية خفيفة",
            "category": "أزياء",
            "sale_price": 159.0,
            "scenario_roles": ["F_channel_quality"],
            "profile": "channel_split",
        },
        {
            "product_id": "rrv_p08_ambiguous",
            "name_ar": "شمعة عطرية تجريبية",
            "category": "منزل",
            "sale_price": 75.0,
            "scenario_roles": ["H_insufficient_evidence"],
            "profile": "ambiguous",
        },
        {
            "product_id": "rrv_p09_steady",
            "name_ar": "كريم ترطيب يومي",
            "category": "عناية",
            "sale_price": 95.0,
            "scenario_roles": [],
            "profile": "steady_baseline",
        },
        {
            "product_id": "rrv_p10_organic",
            "name_ar": "فيتامينات يومية",
            "category": "صحة",
            "sale_price": 120.0,
            "scenario_roles": [],
            "profile": "organic_steady",
        },
    ]


def _channel_mix_for_profile(profile: str) -> dict[str, float]:
    """Share of product views by channel (sums ~1). Simulated truth only."""
    mixes = {
        "discovery_gem": {
            "direct": 0.35,
            "organic": 0.40,
            "tiktok": 0.08,
            "instagram": 0.10,
            "google": 0.07,
        },
        "shipping_friction": {
            "direct": 0.22,
            "organic": 0.18,
            "tiktok": 0.20,
            "instagram": 0.22,
            "google": 0.18,
        },
        "price_hesitation": {
            "direct": 0.20,
            "organic": 0.15,
            "tiktok": 0.25,
            "instagram": 0.25,
            "google": 0.15,
        },
        "discount_trap": {
            "direct": 0.25,
            "organic": 0.20,
            "tiktok": 0.20,
            "instagram": 0.20,
            "google": 0.15,
        },
        "bundle_anchor": {
            "direct": 0.30,
            "organic": 0.25,
            "tiktok": 0.15,
            "instagram": 0.15,
            "google": 0.15,
        },
        "bundle_companion": {
            "direct": 0.28,
            "organic": 0.30,
            "tiktok": 0.12,
            "instagram": 0.15,
            "google": 0.15,
        },
        "channel_split": {
            "direct": 0.10,
            "organic": 0.10,
            "tiktok": 0.45,
            "instagram": 0.15,
            "google": 0.20,
        },
        "ambiguous": {
            "direct": 0.25,
            "organic": 0.25,
            "tiktok": 0.15,
            "instagram": 0.20,
            "google": 0.15,
        },
        "steady_baseline": {
            "direct": 0.30,
            "organic": 0.28,
            "tiktok": 0.12,
            "instagram": 0.15,
            "google": 0.15,
        },
        "organic_steady": {
            "direct": 0.20,
            "organic": 0.45,
            "tiktok": 0.10,
            "instagram": 0.10,
            "google": 0.15,
        },
    }
    return mixes.get(profile, mixes["steady_baseline"])


def _rates_for_profile(profile: str) -> dict[str, float]:
    """Base ATC rate (of views), purchase rate (of ATC), AOV factor, hesitation bias."""
    table = {
        # A: rare views but strong ATC + OK purchase once found
        "discovery_gem": {
            "daily_views": 18.0,
            "atc_rate": 0.28,
            "purchase_rate": 0.42,
            "aov_factor": 1.05,
            "hes_price": 0.08,
            "hes_shipping": 0.10,
            "hes_delivery": 0.06,
            "abandon_rate": 0.35,
            "recovery_attempt_rate": 0.40,
            "recovery_success_rate": 0.22,
            "return_buyer_share": 0.18,
        },
        # B: high engagement, weak purchase — shipping hesitation dominant
        "shipping_friction": {
            "daily_views": 140.0,
            "atc_rate": 0.22,
            "purchase_rate": 0.11,
            "aov_factor": 1.15,
            "hes_price": 0.12,
            "hes_shipping": 0.48,
            "hes_delivery": 0.22,
            "abandon_rate": 0.62,
            "recovery_attempt_rate": 0.55,
            "recovery_success_rate": 0.12,
            "return_buyer_share": 0.10,
        },
        # C: price hesitation strong + enough volume for bounded offer test
        "price_hesitation": {
            "daily_views": 160.0,
            "atc_rate": 0.24,
            "purchase_rate": 0.13,
            "aov_factor": 0.95,
            "hes_price": 0.52,
            "hes_shipping": 0.10,
            "hes_delivery": 0.08,
            "abandon_rate": 0.58,
            "recovery_attempt_rate": 0.50,
            "recovery_success_rate": 0.14,
            "return_buyer_share": 0.12,
        },
        # D: promo window raises conversion but destroys contribution (sim-only cost)
        "discount_trap": {
            "daily_views": 110.0,
            "atc_rate": 0.20,
            "purchase_rate": 0.20,
            "aov_factor": 0.72,  # heavy discount
            "hes_price": 0.15,
            "hes_shipping": 0.10,
            "hes_delivery": 0.08,
            "abandon_rate": 0.40,
            "recovery_attempt_rate": 0.35,
            "recovery_success_rate": 0.18,
            "return_buyer_share": 0.08,
            "promo_active_days": 12,
            "promo_discount_pct": 0.35,
            "promo_purchase_rate_boost": 0.55,
        },
        "bundle_anchor": {
            "daily_views": 95.0,
            "atc_rate": 0.18,
            "purchase_rate": 0.38,
            "aov_factor": 1.20,
            "hes_price": 0.14,
            "hes_shipping": 0.12,
            "hes_delivery": 0.10,
            "abandon_rate": 0.38,
            "recovery_attempt_rate": 0.42,
            "recovery_success_rate": 0.20,
            "return_buyer_share": 0.25,
        },
        "bundle_companion": {
            "daily_views": 70.0,
            "atc_rate": 0.16,
            "purchase_rate": 0.45,
            "aov_factor": 1.0,
            "hes_price": 0.10,
            "hes_shipping": 0.08,
            "hes_delivery": 0.06,
            "abandon_rate": 0.30,
            "recovery_attempt_rate": 0.30,
            "recovery_success_rate": 0.25,
            "return_buyer_share": 0.30,
        },
        # F: TikTok quality high; Google quality weak (simulated for this product only)
        "channel_split": {
            "daily_views": 200.0,
            "atc_rate": 0.15,
            "purchase_rate": 0.25,
            "aov_factor": 1.0,
            "hes_price": 0.18,
            "hes_shipping": 0.12,
            "hes_delivery": 0.10,
            "abandon_rate": 0.45,
            "recovery_attempt_rate": 0.40,
            "recovery_success_rate": 0.15,
            "return_buyer_share": 0.14,
            "channel_quality": {
                "tiktok": {"atc_mult": 1.45, "purchase_mult": 1.35, "aov_mult": 1.10},
                "google": {"atc_mult": 0.55, "purchase_mult": 0.45, "aov_mult": 0.85},
                "instagram": {"atc_mult": 1.05, "purchase_mult": 1.0, "aov_mult": 1.0},
                "direct": {"atc_mult": 1.1, "purchase_mult": 1.1, "aov_mult": 1.05},
                "organic": {"atc_mult": 1.0, "purchase_mult": 1.0, "aov_mult": 1.0},
            },
        },
        # H: thin volume, mixed signals — refuse commercial action
        "ambiguous": {
            "daily_views": 2.5,
            "atc_rate": 0.11,
            "purchase_rate": 0.20,
            "aov_factor": 1.0,
            "hes_price": 0.20,
            "hes_shipping": 0.20,
            "hes_delivery": 0.20,
            "abandon_rate": 0.50,
            "recovery_attempt_rate": 0.25,
            "recovery_success_rate": 0.10,
            "return_buyer_share": 0.05,
        },
        "steady_baseline": {
            "daily_views": 80.0,
            "atc_rate": 0.14,
            "purchase_rate": 0.32,
            "aov_factor": 1.0,
            "hes_price": 0.15,
            "hes_shipping": 0.12,
            "hes_delivery": 0.10,
            "abandon_rate": 0.40,
            "recovery_attempt_rate": 0.38,
            "recovery_success_rate": 0.18,
            "return_buyer_share": 0.20,
        },
        "organic_steady": {
            "daily_views": 65.0,
            "atc_rate": 0.13,
            "purchase_rate": 0.35,
            "aov_factor": 1.02,
            "hes_price": 0.12,
            "hes_shipping": 0.10,
            "hes_delivery": 0.08,
            "abandon_rate": 0.36,
            "recovery_attempt_rate": 0.35,
            "recovery_success_rate": 0.20,
            "return_buyer_share": 0.22,
        },
    }
    return table[profile]


def build_simulation_world_v1(*, seed: int = SIMULATION_SEED, days: int = SIMULATION_DAYS) -> dict[str, Any]:
    """
    Build an in-memory isolated merchant reality.

    Does NOT write to production merchant tables, demo store, or live fixtures.
    """
    products = product_catalog_v1()
    product_days: list[dict[str, Any]] = []
    channel_days: list[dict[str, Any]] = []
    aggregates: dict[str, Any] = {}

    for p in products:
        pid = p["product_id"]
        profile = p["profile"]
        rates = _rates_for_profile(profile)
        mix = _channel_mix_for_profile(profile)
        price = float(p["sale_price"])
        cq = rates.get("channel_quality") or {}

        tot_views = tot_atc = tot_purch = tot_abandon = 0
        tot_rev = 0.0
        tot_hes = {"price": 0, "shipping": 0, "delivery": 0, "other": 0}
        tot_rec_att = tot_rec_ok = 0
        tot_return_buyers = 0
        by_channel: dict[str, dict[str, float]] = {
            ch: {"views": 0, "atc": 0, "purchases": 0, "revenue": 0.0} for ch in CHANNELS
        }
        promo_days = int(rates.get("promo_active_days") or 0)
        promo_disc = float(rates.get("promo_discount_pct") or 0)
        promo_boost = float(rates.get("promo_purchase_rate_boost") or 0)
        promo_purch = promo_rev = promo_contrib = 0.0
        base_purch = base_rev = base_contrib = 0.0
        sim_cost = float(p.get("sim_only_unit_cost") or 0)

        for day in range(1, days + 1):
            is_weekend = day % 7 in (5, 6)
            day_mult = 1.18 if is_weekend else 1.0
            views = max(1, int(round(_jitter(seed, f"{pid}:v:{day}", rates["daily_views"] * day_mult, 0.18))))
            atc = max(0, int(round(views * _jitter(seed, f"{pid}:a:{day}", rates["atc_rate"], 0.10))))
            purch_rate = rates["purchase_rate"]
            effective_price = price
            on_promo = profile == "discount_trap" and day <= promo_days
            if on_promo:
                purch_rate = min(0.95, purch_rate * (1.0 + promo_boost))
                effective_price = price * (1.0 - promo_disc)
            purchases = max(0, int(round(atc * _jitter(seed, f"{pid}:p:{day}", purch_rate, 0.12))))
            abandons = max(0, int(round(atc * rates["abandon_rate"])))
            if purchases + abandons > atc and atc > 0:
                abandons = max(0, atc - purchases)
            aov = effective_price * rates["aov_factor"] * _jitter(seed, f"{pid}:aov:{day}", 1.0, 0.08)
            revenue = purchases * aov
            hes_price = int(round(abandons * rates["hes_price"]))
            hes_ship = int(round(abandons * rates["hes_shipping"]))
            hes_del = int(round(abandons * rates["hes_delivery"]))
            hes_other = max(0, abandons - hes_price - hes_ship - hes_del)
            rec_att = int(round(abandons * rates["recovery_attempt_rate"]))
            rec_ok = int(round(rec_att * rates["recovery_success_rate"]))
            return_buyers = int(round(purchases * rates["return_buyer_share"]))

            product_days.append(
                {
                    "day": day,
                    "product_id": pid,
                    "views": views,
                    "atc": atc,
                    "purchases": purchases,
                    "abandons": abandons,
                    "revenue": round(revenue, 2),
                    "aov": round(aov, 2),
                    "sale_price": price,
                    "effective_price": round(effective_price, 2),
                    "on_promo": on_promo,
                    "hesitation": {
                        "price": hes_price,
                        "shipping": hes_ship,
                        "delivery": hes_del,
                        "other": hes_other,
                    },
                    "recovery_attempts": rec_att,
                    "recovered_purchases": rec_ok,
                    "returning_customers": return_buyers,
                }
            )

            tot_views += views
            tot_atc += atc
            tot_purch += purchases
            tot_abandon += abandons
            tot_rev += revenue
            tot_hes["price"] += hes_price
            tot_hes["shipping"] += hes_ship
            tot_hes["delivery"] += hes_del
            tot_hes["other"] += hes_other
            tot_rec_att += rec_att
            tot_rec_ok += rec_ok
            tot_return_buyers += return_buyers

            contrib = (effective_price - sim_cost) * purchases if sim_cost else None
            if on_promo:
                promo_purch += purchases
                promo_rev += revenue
                if contrib is not None:
                    promo_contrib += contrib
            else:
                base_purch += purchases
                base_rev += revenue
                if contrib is not None:
                    base_contrib += contrib

            # channel split for the day
            remaining = views
            for i, ch in enumerate(CHANNELS):
                if i == len(CHANNELS) - 1:
                    ch_views = remaining
                else:
                    ch_views = int(round(views * mix[ch]))
                    remaining -= ch_views
                mult = cq.get(ch) or {"atc_mult": 1.0, "purchase_mult": 1.0, "aov_mult": 1.0}
                ch_atc = max(0, int(round(ch_views * rates["atc_rate"] * float(mult["atc_mult"]))))
                ch_purch = max(
                    0,
                    int(round(ch_atc * purch_rate * float(mult["purchase_mult"]))),
                )
                ch_aov = aov * float(mult["aov_mult"])
                ch_rev = ch_purch * ch_aov
                by_channel[ch]["views"] += ch_views
                by_channel[ch]["atc"] += ch_atc
                by_channel[ch]["purchases"] += ch_purch
                by_channel[ch]["revenue"] += ch_rev
                channel_days.append(
                    {
                        "day": day,
                        "product_id": pid,
                        "channel": ch,
                        "views": ch_views,
                        "atc": ch_atc,
                        "purchases": ch_purch,
                        "revenue": round(ch_rev, 2),
                        "aov": round(ch_aov, 2) if ch_purch else 0.0,
                    }
                )

        atc_rate = (tot_atc / tot_views) if tot_views else 0.0
        purch_of_atc = (tot_purch / tot_atc) if tot_atc else 0.0
        purch_of_view = (tot_purch / tot_views) if tot_views else 0.0
        agg: dict[str, Any] = {
            "product_id": pid,
            "name_ar": p["name_ar"],
            "category": p["category"],
            "sale_price": price,
            "profile": profile,
            "scenario_roles": list(p["scenario_roles"]),
            "views": tot_views,
            "atc": tot_atc,
            "purchases": tot_purch,
            "abandons": tot_abandon,
            "revenue": round(tot_rev, 2),
            "aov": round(tot_rev / tot_purch, 2) if tot_purch else 0.0,
            "atc_rate": round(atc_rate, 4),
            "purchase_rate_of_atc": round(purch_of_atc, 4),
            "purchase_rate_of_view": round(purch_of_view, 4),
            "hesitation": dict(tot_hes),
            "recovery_attempts": tot_rec_att,
            "recovered_purchases": tot_rec_ok,
            "returning_customers": tot_return_buyers,
            "channels": {
                ch: {
                    "views": int(v["views"]),
                    "atc": int(v["atc"]),
                    "purchases": int(v["purchases"]),
                    "revenue": round(v["revenue"], 2),
                    "aov": round(v["revenue"] / v["purchases"], 2) if v["purchases"] else 0.0,
                    "atc_rate": round(v["atc"] / v["views"], 4) if v["views"] else 0.0,
                    "purchase_rate_of_atc": round(v["purchases"] / v["atc"], 4) if v["atc"] else 0.0,
                }
                for ch, v in by_channel.items()
            },
        }
        if profile == "discount_trap":
            agg["promo_economics_simulation_only"] = {
                "label": _SIM_ONLY_COST_NOTE,
                "unit_cost_sim_only": sim_cost,
                "promo_days": promo_days,
                "discount_pct": promo_disc,
                "promo_purchases": int(promo_purch),
                "promo_revenue": round(promo_rev, 2),
                "promo_contribution_sim_only": round(promo_contrib, 2),
                "non_promo_purchases": int(base_purch),
                "non_promo_revenue": round(base_rev, 2),
                "non_promo_contribution_sim_only": round(base_contrib, 2),
                "conversion_improved": promo_purch / max(1, promo_days)
                > (base_purch / max(1, days - promo_days)),
                "contribution_worse_on_promo": promo_contrib < base_contrib * (
                    promo_days / max(1, days - promo_days)
                ),
            }
        aggregates[pid] = agg

    # Purchase relationships (cart co-occurrence + sequential retention) — simulated truth
    relationships = _build_relationships_v1(seed=seed, aggregates=aggregates)

    return {
        "ok": True,
        "schema": "revenue_reality_simulation_world_v1",
        "validation_version": VALIDATION_VERSION_V1,
        "simulation_only": True,
        "store_slug": SIMULATION_STORE_SLUG,
        "seed": seed,
        "days": days,
        "products": products,
        "product_count": len(products),
        "product_day_rows": product_days,
        "channel_day_rows": channel_days,
        "aggregates": aggregates,
        "relationships": relationships,
        "margin_intelligence": {
            "production_status": "DATA_GAP",
            "note": (
                "No production margin/cost truth in CartFlow architecture. "
                "Scenario D uses SIMULATION-ONLY unit cost for lab validation only."
            ),
        },
        "comparative_market_pricing": {
            "status": "NEEDS_EXTERNAL_DATA",
            "unsafe_with_current_truth": True,
            "required": [
                "trusted comparable-product source",
                "product matching",
                "freshness SLA",
                "geography",
                "variant normalization",
                "shipping/tax normalization",
            ],
            "classification": "UNSAFE_WITH_CURRENT_TRUTH",
        },
    }


def _build_relationships_v1(*, seed: int, aggregates: dict[str, Any]) -> dict[str, Any]:
    a_id = "rrv_p05_bundle_a"
    b_id = "rrv_p06_bundle_b"
    a_purch = int(aggregates[a_id]["purchases"])
    # Strong co-purchase: ~38% of A carts also contain B
    co = max(8, int(round(a_purch * 0.38)))
    # Retention: buyers of A later buy B at ~31% within window (vs ~6% baseline for non-A)
    later_b = max(6, int(round(a_purch * 0.31)))
    baseline_later = max(2, int(round(a_purch * 0.06)))
    return {
        "cart_co_occurrence": [
            {
                "product_a": a_id,
                "product_b": b_id,
                "orders_with_both": co,
                "orders_with_a": a_purch,
                "lift_vs_independent": round(0.38 / max(0.05, aggregates[b_id]["purchase_rate_of_view"]), 2),
                "evidence_strength": "strong" if co >= 20 else "moderate",
            }
        ],
        "retention_sequences": [
            {
                "first_product": a_id,
                "later_product": b_id,
                "buyers_of_first": a_purch,
                "later_purchases": later_b,
                "propensity": round(later_b / a_purch, 4) if a_purch else 0.0,
                "baseline_propensity_non_buyers": round(baseline_later / max(a_purch, 1), 4),
                "materially_higher": later_b >= baseline_later * 3,
                "classification": "retention_not_acquisition",
            }
        ],
        "seed_note": f"relationship_seed={seed}",
    }


__all__ = ["build_simulation_world_v1", "product_catalog_v1"]
