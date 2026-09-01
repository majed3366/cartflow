# -*- coding: utf-8 -*-
"""Page-Specific Semantic Composition V1 — organism contracts + regression."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from services.semantic_visual_model_v1 import SEMANTIC_MODEL_VERSION

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(encoding="utf-8")
SEM_PY = (ROOT / "services" / "semantic_visual_model_v1.py").read_bytes()
SEM_JS = (ROOT / "static" / "merchant_ui_v2_semantic_model.js").read_bytes()
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


def _node_eval(expr: str) -> dict:
    script = f"""
var fs = require('fs');
var vm = require('vm');
var g = {{ window: {{}}, globalThis: {{}}, document: null, location: {{ search: '' }},
  matchMedia: function(){{ return {{ matches: false }}; }} }};
g.window = g; g.globalThis = g;
function load(p) {{ vm.runInNewContext(fs.readFileSync(p, 'utf8'), g); }}
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_semantic_model.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_language.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_home.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_workspace.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_carts.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_comms.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_settings.js"))});
var out = {expr};
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout.strip().splitlines()[-1])


class SemanticModelUnchangedTests(unittest.TestCase):
    def test_semantic_model_files_not_rewritten_in_spirit(self) -> None:
        self.assertEqual(SEMANTIC_MODEL_VERSION, "semantic-visual-model-v1")
        py = SEM_PY.decode("utf-8", errors="replace")
        js = SEM_JS.decode("utf-8", errors="replace")
        self.assertIn("def clause_roles", py)
        self.assertIn("function clauseRoles", js)
        self.assertIn("project_home_surface", py)
        self.assertIn("projectHomeSurface", js)
        # Painters must not invent new truth fields
        for blob in (HOME_JS, WS_JS, CARTS_JS, COMMS_JS, SETTINGS_JS):
            self.assertNotIn("invented_", blob)
            self.assertNotIn("fake_evidence", blob)


class OrganismContractTests(unittest.TestCase):
    def test_home_no_repeated_attention_glyph(self) -> None:
        out = _node_eval(
            """(function(){
              var html = g.CartFlowUiV2Home.render({
                enabled:true,
                sections:[
                  {id:'decisions', dominant:true, empty:false, title_ar:'قرار', diagnosis_ar:'راجع مسار الشحن.', recommendation_ar:'افتح'},
                  {id:'situations', empty:false, title_ar:'منتج', diagnosis_ar:'منتج يتحرك.'},
                  {id:'health', empty:false, title_ar:'صحة', status_ar:'مستقر', diagnosis_ar:'المتجر مستقر.'}
                ]
              });
              return {
                attentionGlyph: (html.match(/cf2-co--attention/g)||[]).length,
                coRow: (html.match(/cf2-co-row/g)||[]).length,
                gravity: html.indexOf('data-cf2-gravity="primary"')>=0,
                satellite: (html.match(/data-cf2-satellite=/g)||[]).length,
                organism: html.indexOf('gravity-well')>=0
              };
            })()"""
        )
        self.assertEqual(out["attentionGlyph"], 0)
        self.assertEqual(out["coRow"], 0)
        self.assertTrue(out["gravity"])
        self.assertGreaterEqual(out["satellite"], 1)
        self.assertTrue(out["organism"])

    def test_workspace_ready_zero_icons_and_conflict_via_void(self) -> None:
        out = _node_eval(
            """(function(){
              var W = g.CartFlowUiV2Workspace;
              var ready = W.render({quiet:false, zone_b:[{is_primary_decision:true, decision_id:'r1', execution_readiness:'READY', execution_available:true, decision_sentence_ar:'نفّذ'}]});
              var conf = W.render({quiet:false, zone_b:[{is_primary_decision:true, decision_id:'c1', execution_readiness:'NEEDS_MORE_EVIDENCE', diagnosis_status:'conflicting_evidence', decision_sentence_ar:'راجع'}]});
              return {
                readyIcons: (ready.match(/cf2-co--/g)||[]).length,
                readyRoles: (ready.match(/data-cf2-role=/g)||[]).length,
                readyMass: ready.indexOf('data-cf2-mass="ready"')>=0,
                confIcons: (conf.match(/cf2-co--/g)||[]).length,
                confVoid: conf.indexOf('cf2-ws__void')>=0,
                confHigh: conf.indexOf('data-cf2-tension="high"')>=0,
                confConflict: conf.indexOf('data-cf2-conflict="conflict"')>=0
              };
            })()"""
        )
        self.assertEqual(out["readyIcons"], 0)
        self.assertEqual(out["readyRoles"], 0)
        self.assertTrue(out["readyMass"])
        self.assertEqual(out["confIcons"], 0)
        self.assertTrue(out["confVoid"])
        self.assertTrue(out["confHigh"])
        self.assertTrue(out["confConflict"])

    def test_carts_incomplete_not_generic_empty_card(self) -> None:
        out = _node_eval(
            """(function(){
              var C = g.CartFlowUiV2Carts;
              var root = { innerHTML:'', className:'', attrs:{},
                setAttribute:function(k,v){ this.attrs[k]=v; },
                removeAttribute:function(k){ delete this.attrs[k]; },
                getAttribute:function(k){ return this.attrs[k]; },
                querySelectorAll:function(){ return []; }
              };
              C.applyPayloadAndPaint(root, {
                carts:[], archived:[], snapshot_reason:'no_snapshot',
                _snapshot:{ status:'miss', reason:'no_snapshot' }
              });
              var html = root.innerHTML;
              return {
                organism: root.attrs['data-cf2-organism']==='weighted-queue',
                incomplete: root.attrs['data-carts-truth']==='incomplete' || html.indexOf('is-withheld')>=0,
                whiteEmpty: html.indexOf('cf2-carts__empty\"')>=0 && html.indexOf('cf2-carts__filters')>=0,
                filters: html.indexOf('cf2-carts__filters')>=0,
                withheld: html.indexOf('is-withheld')>=0
              };
            })()"""
        )
        self.assertTrue(out["organism"])
        self.assertTrue(out["incomplete"] or out["withheld"])
        self.assertTrue(out["withheld"])
        self.assertFalse(out["filters"])

    def test_carts_and_comms_distinguishable_without_page_title(self) -> None:
        self.assertIn("weighted-queue", CARTS_JS)
        self.assertIn("lifecycle-continuum", COMMS_JS)
        self.assertIn("cf2-carts__object", CARTS_JS)
        self.assertIn("cf2-comms__life", COMMS_JS)
        self.assertIn("data-cf2-continuity", CARTS_JS)
        self.assertIn("data-cf2-lifecycle", COMMS_JS)
        self.assertNotEqual(
            "weighted-queue",
            "lifecycle-continuum",
        )
        # CSS organisms diverge structurally
        self.assertIn("cf2-carts__object.is-actionable", CARTS_CSS)
        self.assertIn("cf2-comms__tick", COMMS_CSS)
        self.assertNotIn("cf2-comms__tick", CARTS_CSS)
        self.assertNotIn("cf2-carts__object.is-withheld", COMMS_CSS)

    def test_settings_distinguishable_ledger(self) -> None:
        self.assertIn("config-ledger", SETTINGS_JS)
        self.assertIn("data-cf2-joint", SETTINGS_JS)
        self.assertIn("cf2-settings__joint", SETTINGS_CSS)
        self.assertIn('data-cf2-joint="closed"', SETTINGS_CSS)
        self.assertIn('data-cf2-joint="open"', SETTINGS_CSS)
        self.assertNotIn("cf2-co--attention", SETTINGS_JS)
        self.assertNotIn("cf2-evfield", SETTINGS_JS)
        self.assertNotIn("cf2-dmass", SETTINGS_JS)


class PageNameHiddenStructuralTests(unittest.TestCase):
    def test_five_organism_markers_present(self) -> None:
        markers = {
            "home": "gravity-well",
            "workspace": "formation",
            "carts": "weighted-queue",
            "comms": "lifecycle-continuum",
            "settings": "config-ledger",
        }
        self.assertIn(markers["home"], HOME_JS)
        self.assertIn(markers["workspace"], WS_JS)
        self.assertIn(markers["carts"], CARTS_JS)
        self.assertIn(markers["comms"], COMMS_JS)
        self.assertIn(markers["settings"], SETTINGS_JS)
        self.assertEqual(len(set(markers.values())), 5)

    def test_family_shared_grammar_survives(self) -> None:
        # Shared family cues remain across surfaces
        self.assertIn("border-inline-start", HOME_CSS)
        self.assertIn("border-inline-start", WS_CSS)
        self.assertIn("border-inline-start", CARTS_CSS)
        self.assertIn("border-inline-start", COMMS_CSS)
        self.assertIn("border-inline-start", SETTINGS_CSS)
        self.assertIn("psg1", V2_HTML)


class MobileOrganismPreservationTests(unittest.TestCase):
    def test_mobile_hooks_remain(self) -> None:
        self.assertIn("1023", CARTS_JS)
        self.assertIn("1023", COMMS_JS)
        self.assertIn("is-detail-open", CARTS_JS)
        self.assertIn("is-detail-open", COMMS_JS)
        self.assertIn("mobile-hierarchy", WS_JS)
        self.assertIn("@media", HOME_CSS)
        self.assertIn("@media", WS_CSS)


class OperationalRegressionTests(unittest.TestCase):
    def test_dashboard_hosts_psg_and_semantic_model(self) -> None:
        self.assertIn("psg1", V2_HTML)
        self.assertIn("merchant_ui_v2_semantic_model.js", V2_HTML)
        self.assertIn("semantic-visual-model-v1", HOME_JS)
        self.assertIn("semantic-visual-model-v1", WS_JS)
        self.assertEqual(SEMANTIC_MODEL_VERSION, "semantic-visual-model-v1")

    def test_no_new_truth_apis_in_painters(self) -> None:
        self.assertIn("/api/dashboard/summary", HOME_JS)
        self.assertIn("/api/cart-workspace/v1/projection", WS_JS)
        self.assertIn("/api/dashboard/normal-carts", CARTS_JS)
        self.assertIn("/api/dashboard/followups", COMMS_JS)
        self.assertNotIn("/api/semantic-", HOME_JS + WS_JS + CARTS_JS + COMMS_JS)


if __name__ == "__main__":
    unittest.main()
