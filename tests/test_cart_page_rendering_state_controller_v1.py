# -*- coding: utf-8 -*-
"""Cart Page V2 Phase 2.6 — Rendering State Controller V1 transition tests."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_RSC_JS = _ROOT / "static" / "cart_page_rendering_state_controller_v1.js"
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


def _run_rsc_harness(script: str) -> dict:
    """Execute RSC transitions in Node; return JSON result object."""
    harness = f"""
const api = require({json.dumps(str(_RSC_JS).replace(chr(92), "/"))});
{script}
"""
    proc = subprocess.run(
        ["node", "-e", harness],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"node harness failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


class CartPageRenderingStateControllerV1Tests(unittest.TestCase):
    def test_controller_script_and_template_order(self) -> None:
        self.assertTrue(_RSC_JS.is_file())
        self.assertIn("cart_page_rendering_state_controller_v1.js", _TMPL)
        idx_rsc = _TMPL.index("cart_page_rendering_state_controller_v1.js")
        idx_lazy = _TMPL.index("merchant_dashboard_lazy.js")
        self.assertLess(idx_rsc, idx_lazy)

    def test_lazy_wires_rsc_owner_and_events(self) -> None:
        self.assertIn("CartPageRenderingStateController", _LAZY_JS)
        self.assertIn("function paintCartPageFromRsc", _LAZY_JS)
        self.assertIn('rscDispatch("CACHE_HYDRATED"', _LAZY_JS)
        self.assertIn('rscDispatch("FETCH_STARTED"', _LAZY_JS)
        self.assertIn('rscDispatch("SOFT_REVALIDATE"', _LAZY_JS)
        self.assertIn("rscShouldMerchantVisibleRefresh", _LAZY_JS)
        self.assertIn('rscDispatch("APPLY_SUCCESS"', _LAZY_JS)
        self.assertIn('rscDispatch("APPLY_KEEP"', _LAZY_JS)
        self.assertIn('rscDispatch("APPLY_CONFIRMED_EMPTY"', _LAZY_JS)
        self.assertIn('rscDispatch("FETCH_FAILED"', _LAZY_JS)
        self.assertIn('rscDispatch("ROWS_PATCHED"', _LAZY_JS)
        self.assertIn("skipComposition: true", _LAZY_JS)
        self.assertIn("preserveMi: true", _LAZY_JS)

    def test_presenters_do_not_independently_choose_pending(self) -> None:
        # Workspace must not invent pending from missing MI when RSC owns composition.
        ws_start = _LAZY_JS.index("function renderMiCartsV1Workspace")
        ws_end = _LAZY_JS.index("function renderPeV2CartsQueue")
        ws = _LAZY_JS[ws_start:ws_end]
        self.assertIn("Paint-only", ws)
        self.assertNotIn("renderMiCartsV1Pending(rows)", ws)
        self.assertIn("return false", ws)

    def test_setup_render_build_bumped_for_rsc(self) -> None:
        from services.merchant_setup_render_build import MERCHANT_SETUP_RENDER_BUILD

        self.assertIn("rsc-v1", MERCHANT_SETUP_RENDER_BUILD)
        self.assertIn("ui-setup-v8g-rsc-v1_1", MERCHANT_SETUP_RENDER_BUILD)
        self.assertIn("ui-setup-v8g-rsc-v1_1", _LAZY_JS)

    def test_boot_cache_then_fetch_pending(self) -> None:
        out = _run_rsc_harness(
            """
const commits = [];
const c = api.createController({
  countPrimaryActions: (rows) => ({
    contact_customer: 0, follow_up_manually: 0, review_cart: 0,
    wait: rows.length, no_action_required: 0, reopen: 0, archive: 0, other: 0,
    total_active: rows.length, needs_you: 0,
  }),
  onCommit: (s) => commits.push({ phase: s.phase, freshness: s.freshness, bodyMode: s.bodyMode, verdictMode: s.verdictMode }),
});
c.dispatch("CACHE_HYDRATED", { rows: [{ id: 1 }], reason: "cache" });
c.dispatch("FETCH_STARTED", { reason: "boot_fetch" });
console.log(JSON.stringify({ commits, snap: c.getSnapshot() }));
"""
        )
        self.assertEqual(out["commits"][0]["phase"], "cached")
        self.assertEqual(out["commits"][0]["freshness"], "pending")
        self.assertEqual(out["commits"][1]["phase"], "refreshing")
        self.assertEqual(out["commits"][1]["freshness"], "pending")
        self.assertEqual(out["snap"]["verdictMode"], "refreshing")

    def test_apply_success_sets_final(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({
  countPrimaryActions: (rows) => ({
    contact_customer: rows.length ? 1 : 0, follow_up_manually: 0, review_cart: 0,
    wait: 0, no_action_required: 0, reopen: 0, archive: 0, other: 0,
    total_active: rows.length, needs_you: rows.length ? 1 : 0,
  }),
});
c.dispatch("FETCH_STARTED", { reason: "fetch" });
const mi = { merchant_value_stories_v1: { stories: [{ id: "s1" }] } };
const snap = c.dispatch("APPLY_SUCCESS", {
  rows: [{ id: 1, cart_page_primary_action: "contact_customer" }],
  miPayload: mi,
  reason: "apply",
  appliedGen: 1,
});
console.log(JSON.stringify({
  phase: snap.phase, freshness: snap.freshness, bodyMode: snap.bodyMode,
  verdictMode: snap.verdictMode, miSource: snap.miSource,
  hasLastGood: !!(snap.lastGood && snap.lastGood.miPayload),
}));
"""
        )
        self.assertEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "final")
        self.assertEqual(out["bodyMode"], "stories")
        self.assertEqual(out["miSource"], "live")
        self.assertTrue(out["hasLastGood"])
        self.assertIn(out["verdictMode"], ("needs_you", "automatic", "calm", "empty"))

    def test_apply_keep_preserves_last_good_mi(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({
  countPrimaryActions: (rows) => ({
    contact_customer: 0, follow_up_manually: 0, review_cart: 0,
    wait: rows.length, no_action_required: 0, reopen: 0, archive: 0, other: 0,
    total_active: rows.length, needs_you: 0,
  }),
});
const mi = { merchant_value_stories_v1: { stories: [{ id: "s1" }] } };
c.dispatch("APPLY_SUCCESS", {
  rows: [{ id: 1 }],
  miPayload: mi,
  reason: "apply",
  appliedGen: 1,
});
c.dispatch("SOFT_REVALIDATE", { reason: "token_refresh_state" });
const keep = c.dispatch("APPLY_KEEP", {
  rows: [{ id: 1 }, { id: 2 }],
  miPayload: { ok: true, merchant_carts_page_rows: [{ id: 1 }] },
  reason: "thin_keep",
  rowsSource: "memory",
});
console.log(JSON.stringify({
  phase: keep.phase, freshness: keep.freshness, bodyMode: keep.bodyMode,
  miSource: keep.miSource,
  storiesLen: (keep.miPayload && keep.miPayload.merchant_value_stories_v1
    && keep.miPayload.merchant_value_stories_v1.stories || []).length,
  verdictMode: keep.verdictMode,
  silent: !!keep.silentRevalidate,
}));
"""
        )
        # V1.1: keep with trusted last-good stays FINAL (no merchant Refreshing).
        self.assertEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "final")
        self.assertEqual(out["bodyMode"], "stories")
        self.assertEqual(out["storiesLen"], 1)
        self.assertNotEqual(out["verdictMode"], "refreshing")
        self.assertIn(out["miSource"], ("last_good", "live"))

    def test_confirmed_empty_is_final_empty(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({});
c.dispatch("FETCH_STARTED", {});
const snap = c.dispatch("APPLY_CONFIRMED_EMPTY", { reason: "confirmed_empty", appliedGen: 2 });
console.log(JSON.stringify({
  phase: snap.phase, freshness: snap.freshness, bodyMode: snap.bodyMode, verdictMode: snap.verdictMode,
}));
"""
        )
        self.assertEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "final")
        self.assertEqual(out["bodyMode"], "empty")

    def test_fetch_failed_keeps_last_good(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({
  countPrimaryActions: (rows) => ({
    contact_customer: 0, follow_up_manually: 0, review_cart: 0,
    wait: rows.length, no_action_required: 0, reopen: 0, archive: 0, other: 0,
    total_active: rows.length, needs_you: 0,
  }),
});
const mi = { merchant_intelligence_store_v1: { groups: [{ key: "g1" }] } };
c.dispatch("APPLY_SUCCESS", { rows: [{ id: 1 }], miPayload: mi, appliedGen: 1 });
c.dispatch("SOFT_REVALIDATE", { reason: "token_refresh_state" });
const fail = c.dispatch("FETCH_FAILED", { reason: "fetch_error" });
console.log(JSON.stringify({
  phase: fail.phase, freshness: fail.freshness, bodyMode: fail.bodyMode,
  hasMi: !!(fail.miPayload && fail.miPayload.merchant_intelligence_store_v1),
  verdictMode: fail.verdictMode,
}));
"""
        )
        # V1.1: failure with trusted last-good keeps FINAL visible.
        self.assertEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "final")
        self.assertEqual(out["bodyMode"], "stories")
        self.assertTrue(out["hasMi"])
        self.assertNotEqual(out["verdictMode"], "refreshing")

    def test_no_final_without_apply_success(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({});
c.dispatch("CACHE_HYDRATED", { rows: [{ id: 1 }] });
c.dispatch("FETCH_STARTED", {});
c.dispatch("APPLY_KEEP", { rows: [{ id: 1 }], reason: "partial_keep" });
const snap = c.getSnapshot();
console.log(JSON.stringify({ phase: snap.phase, freshness: snap.freshness }));
"""
        )
        self.assertNotEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "pending")

    def test_token_refresh_does_not_leave_final(self) -> None:
        out = _run_rsc_harness(
            """
const commits = [];
const c = api.createController({
  countPrimaryActions: (rows) => ({
    contact_customer: 0, follow_up_manually: 0, review_cart: 0,
    wait: rows.length, no_action_required: 0, reopen: 0, archive: 0, other: 0,
    total_active: rows.length, needs_you: 0,
  }),
  onCommit: (s) => commits.push({ phase: s.phase, freshness: s.freshness, verdictMode: s.verdictMode, silent: !!s.silentRevalidate }),
});
const mi = { merchant_value_stories_v1: { stories: [{ id: "s1" }] } };
c.dispatch("APPLY_SUCCESS", { rows: [{ id: 1 }], miPayload: mi, appliedGen: 1 });
c.dispatch("FETCH_STARTED", { reason: "token_refresh_state", silent: true });
c.dispatch("SOFT_REVALIDATE", { reason: "pending_cart_poll" });
c.dispatch("FETCH_STARTED", { reason: "normal_carts_retry_thin" });
const snap = c.getSnapshot();
console.log(JSON.stringify({
  phase: snap.phase, freshness: snap.freshness, verdictMode: snap.verdictMode,
  commits: commits.slice(1),
}));
"""
        )
        self.assertEqual(out["phase"], "final")
        self.assertEqual(out["freshness"], "final")
        self.assertNotEqual(out["verdictMode"], "refreshing")
        for c in out["commits"]:
            self.assertEqual(c["phase"], "final")
            self.assertEqual(c["freshness"], "final")
            self.assertNotEqual(c["verdictMode"], "refreshing")

    def test_boot_without_trust_still_shows_refreshing(self) -> None:
        out = _run_rsc_harness(
            """
const c = api.createController({});
const snap = c.dispatch("FETCH_STARTED", { reason: "boot_priority" });
console.log(JSON.stringify({
  phase: snap.phase, freshness: snap.freshness, verdictMode: snap.verdictMode,
}));
"""
        )
        self.assertEqual(out["phase"], "refreshing")
        self.assertEqual(out["freshness"], "pending")
        self.assertEqual(out["verdictMode"], "refreshing")

    def test_silent_reason_helper(self) -> None:
        out = _run_rsc_harness(
            """
console.log(JSON.stringify({
  token: api.isSilentFetchReason("token_refresh_state"),
  pending: api.isSilentFetchReason("pending_cart_poll"),
  retry: api.isSilentFetchReason("normal_carts_retry_thin"),
  boot: api.isSilentFetchReason("boot_priority"),
  manual: api.isSilentFetchReason("manual_now"),
}));
"""
        )
        self.assertTrue(out["token"])
        self.assertTrue(out["pending"])
        self.assertTrue(out["retry"])
        self.assertFalse(out["boot"])
        self.assertFalse(out["manual"])


if __name__ == "__main__":
    unittest.main()