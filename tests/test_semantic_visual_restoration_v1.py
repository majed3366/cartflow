# -*- coding: utf-8 -*-
"""Semantic Visual Restoration V1 — derivation + painter contracts + falsification."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.semantic_visual_model_v1 import (
    SEMANTIC_MODEL_VERSION,
    project_home_surface,
    project_workspace,
)

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
LANG_JS = (ROOT / "static" / "merchant_ui_v2_language.js").read_text(encoding="utf-8")
SEM_JS = (ROOT / "static" / "merchant_ui_v2_semantic_model.js").read_text(
    encoding="utf-8"
)
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


def _node_eval(expr: str) -> dict:
    script = f"""
var fs = require('fs');
var vm = require('vm');
var g = {{ window: {{}}, globalThis: {{}}, document: null, location: {{ search: '' }} }};
g.window = g; g.globalThis = g;
function load(p) {{ vm.runInNewContext(fs.readFileSync(p, 'utf8'), g); }}
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_semantic_model.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_language.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_home.js"))});
load({json.dumps(str(ROOT / "static" / "merchant_ui_v2_workspace.js"))});
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


class SemanticDerivationTests(unittest.TestCase):
    def test_version(self) -> None:
        self.assertEqual(SEMANTIC_MODEL_VERSION, "semantic-visual-model-v1")

    def test_home_coarse_omits_unsupported_roles(self) -> None:
        pkg = {
            "enabled": True,
            "sections": [
                {
                    "id": "decisions",
                    "dominant": True,
                    "empty": False,
                    "title_ar": "أهم قرار اليوم",
                    "diagnosis_ar": "أقوى الأدلة تشير إلى تردد عند الشحن.",
                }
            ],
        }
        sem = project_home_surface(pkg, pkg["sections"][0])
        self.assertEqual(sem["evidence_sufficiency"], "UNKNOWN")
        self.assertEqual(sem["uncertainty_level"], "UNKNOWN")
        roles = [r["role"] for r in sem["roles"]]
        self.assertEqual(roles, ["attention"])
        self.assertNotIn("أدلة ناقصة", [r["label"] for r in sem["roles"]])

    def test_home_empty_insufficient(self) -> None:
        pkg = {
            "enabled": True,
            "sections": [
                {"id": "decisions", "dominant": True, "empty": True, "status_ar": "أدلة غير كافية"}
            ],
        }
        sem = project_home_surface(pkg, pkg["sections"][0])
        self.assertEqual(sem["core_silence"], "QUIET")
        self.assertEqual(sem["attention_intensity"], "NONE")
        self.assertEqual(sem["roles"], [])

    def test_home_status_insufficient_not_quiet_when_monitor(self) -> None:
        pkg = {
            "enabled": True,
            "sections": [
                {
                    "id": "decisions",
                    "dominant": True,
                    "empty": True,
                    "status_ar": "أدلة غير كافية",
                },
                {"id": "situations", "empty": False, "title_ar": "منتج"},
            ],
        }
        sem = project_home_surface(pkg, pkg["sections"][0])
        self.assertEqual(sem["core_silence"], "ACTIVE")
        self.assertEqual(sem["evidence_sufficiency"], "INSUFFICIENT")
        self.assertEqual(sem["uncertainty_level"], "MEDIUM")
        self.assertEqual([r["role"] for r in sem["roles"]], ["evidence", "uncertainty"])

    def test_copy_containing_adilla_does_not_force_insufficient(self) -> None:
        pkg = {
            "enabled": True,
            "sections": [
                {
                    "id": "decisions",
                    "dominant": True,
                    "empty": False,
                    "diagnosis_ar": "الأدلة تشير إلى مسار واضح.",
                    "recommendation_ar": "افتح القرار.",
                }
            ],
        }
        sem = project_home_surface(pkg, pkg["sections"][0])
        self.assertEqual(sem["evidence_sufficiency"], "UNKNOWN")

    def test_workspace_needs_more(self) -> None:
        proj = {"quiet": False, "zone_b": [{"decision_id": "d1"}]}
        card = {
            "is_primary_decision": True,
            "execution_readiness": "NEEDS_MORE_EVIDENCE",
            "evidence_lines_ar": ["a", "b", "c", "d", "e", "f", "g", "h", "i"],
        }
        sem = project_workspace(proj, card)
        self.assertEqual(sem["evidence_sufficiency"], "INSUFFICIENT")
        self.assertEqual(sem["density"], "LOW")
        self.assertEqual(sem["mass"], "OPEN")
        self.assertEqual(sem["tension"], "NONE")
        self.assertEqual(sem["uncertainty_level"], "MEDIUM")
        self.assertIn("evidence", [r["role"] for r in sem["roles"]])
        self.assertIn("uncertainty", [r["role"] for r in sem["roles"]])

    def test_workspace_ready(self) -> None:
        proj = {"quiet": False, "zone_b": [{}]}
        card = {
            "is_primary_decision": True,
            "execution_readiness": "READY",
            "execution_available": True,
            "decision_sentence_ar": "نفّذ الخطوة",
        }
        sem = project_workspace(proj, card)
        self.assertEqual(sem["evidence_sufficiency"], "SUFFICIENT")
        self.assertEqual(sem["density"], "PRESENT")
        self.assertEqual(sem["mass"], "READY")
        self.assertEqual(sem["tension"], "NONE")
        self.assertEqual(sem["wait_kind"], "ACTION_REQUIRED")
        self.assertEqual([r["role"] for r in sem["roles"]], ["attention"])

    def test_workspace_not_ready_without_conflict(self) -> None:
        proj = {"quiet": False, "zone_b": [{}]}
        card = {
            "is_primary_decision": True,
            "execution_readiness": "NEEDS_MORE_EVIDENCE",
        }
        sem = project_workspace(proj, card)
        self.assertEqual(sem["tension"], "NONE")
        self.assertEqual(sem["mass"], "OPEN")

    def test_workspace_conflict(self) -> None:
        proj = {"quiet": False, "zone_b": [{}]}
        card = {
            "is_primary_decision": True,
            "execution_readiness": "NEEDS_MORE_EVIDENCE",
            "diagnosis_status": "conflicting_evidence",
        }
        sem = project_workspace(proj, card)
        self.assertEqual(sem["evidence_conflict"], "CONFLICT")
        self.assertEqual(sem["tension"], "HIGH")
        self.assertEqual(sem["uncertainty_level"], "HIGH")

    def test_workspace_blocked_tension_without_conflict_field(self) -> None:
        proj = {"quiet": False, "zone_b": [{}]}
        card = {"is_primary_decision": True, "execution_readiness": "BLOCKED"}
        sem = project_workspace(proj, card)
        self.assertEqual(sem["mass"], "HELD")
        self.assertEqual(sem["tension"], "HIGH")
        self.assertEqual(sem["evidence_conflict"], "UNKNOWN")

    def test_unknown_null(self) -> None:
        sem = project_workspace(None, None)
        self.assertEqual(sem["core_silence"], "QUIET")
        self.assertEqual(sem["roles"], [])
        self.assertEqual(sem["density"], "NEUTRAL")
        self.assertEqual(sem["tension"], "UNKNOWN")

    def test_same_label_different_truth_roles_differ(self) -> None:
        a = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {
                "is_primary_decision": True,
                "execution_readiness": "NEEDS_MORE_EVIDENCE",
                "decision_sentence_ar": "راجع القرار",
            },
        )
        b = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {
                "is_primary_decision": True,
                "execution_readiness": "READY",
                "decision_sentence_ar": "راجع القرار",
            },
        )
        self.assertEqual(a["wait_kind"] != b["wait_kind"], True)
        self.assertNotEqual([r["kind"] for r in a["roles"]], [r["kind"] for r in b["roles"]])
        self.assertNotEqual(a["density"], b["density"])
        self.assertNotEqual(a["mass"], b["mass"])

    def test_different_label_same_semantic(self) -> None:
        a = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {
                "is_primary_decision": True,
                "execution_readiness": "READY",
                "decision_sentence_ar": "أصلح الشحن",
            },
        )
        b = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {
                "is_primary_decision": True,
                "execution_readiness": "READY",
                "decision_sentence_ar": "راجع التواصل",
            },
        )
        self.assertEqual(a["density"], b["density"])
        self.assertEqual(a["mass"], b["mass"])
        self.assertEqual(a["tension"], b["tension"])
        self.assertEqual([r["role"] for r in a["roles"]], [r["role"] for r in b["roles"]])


class SemanticJsParityTests(unittest.TestCase):
    def test_js_matches_python_ready_and_conflict(self) -> None:
        out = _node_eval(
            """(function(){
              var S = g.CartFlowSemanticVisualV1;
              var ready = S.projectWorkspace({quiet:false,zone_b:[{}]}, {is_primary_decision:true, execution_readiness:'READY'});
              var conf = S.projectWorkspace({quiet:false,zone_b:[{}]}, {is_primary_decision:true, execution_readiness:'NEEDS_MORE_EVIDENCE', diagnosis_status:'conflicting_evidence'});
              return {ready: ready, conf: conf};
            })()"""
        )
        py_ready = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {"is_primary_decision": True, "execution_readiness": "READY"},
        )
        py_conf = project_workspace(
            {"quiet": False, "zone_b": [{}]},
            {
                "is_primary_decision": True,
                "execution_readiness": "NEEDS_MORE_EVIDENCE",
                "diagnosis_status": "conflicting_evidence",
            },
        )
        self.assertEqual(
            [r["role"] for r in out["ready"]["roles"]],
            [r["role"] for r in py_ready["roles"]],
        )
        self.assertEqual(out["ready"]["mass"], py_ready["mass"])
        self.assertEqual(out["conf"]["tension"], py_conf["tension"])
        self.assertEqual(out["conf"]["uncertainty_level"], py_conf["uncertainty_level"])


class SemanticPainterContractTests(unittest.TestCase):
    def test_fixed_triple_gone(self) -> None:
        self.assertNotIn("isWeakText", HOME_JS)
        self.assertNotIn("densityFromCount", HOME_JS)
        self.assertNotIn("densityFromCount(lines.length)", WS_JS)
        self.assertNotIn("mapHomeObjects", HOME_JS)
        self.assertNotIn("mapWorkspaceObjects(card)", WS_JS)
        self.assertIn("evidenceFieldFromSufficiency", HOME_JS)
        self.assertIn("evidenceFieldFromSufficiency", WS_JS)
        self.assertIn("NOT_CURRENTLY_SUPPORTED", HOME_JS)
        self.assertNotIn("momentumTrace(", HOME_JS)
        self.assertIn("living-route-scaffold", WS_JS)
        self.assertNotIn("is-arriving", WS_JS)
        self.assertIn("merchant_ui_v2_semantic_model.js", V2_HTML)

    def test_no_narrative_length_density(self) -> None:
        self.assertNotIn("densityFromCount(lines.length)", WS_JS)
        self.assertNotIn("densityFromCount(evCount)", HOME_JS)
        self.assertIn("evidenceFieldFromSufficiency(density)", WS_JS)

    def test_render_home_omits_unsupported(self) -> None:
        out = _node_eval(
            """(function(){
              var html = g.CartFlowUiV2Home.render({
                enabled:true,
                sections:[{id:'decisions', dominant:true, empty:false, title_ar:'قرار', diagnosis_ar:'أقوى الأدلة تشير إلى تردد.', recommendation_ar:'راجع'}]
              });
              return {
                html: html,
                roles: (html.match(/data-cf2-role="/g)||[]).length,
                insufficient: html.indexOf('أدلة ناقصة')>=0,
                uncertainty: html.indexOf('عدم يقين')>=0,
                attention: html.indexOf('انتباه')>=0,
                mtrace: html.indexOf('cf2-mtrace')>=0,
                evfield: html.indexOf('cf2-evfield')>=0
              };
            })()"""
        )
        self.assertTrue(out["attention"])
        self.assertFalse(out["insufficient"])
        self.assertFalse(out["uncertainty"])
        self.assertEqual(out["roles"], 1)
        self.assertFalse(out["mtrace"])
        self.assertFalse(out["evfield"])

    def test_render_workspace_cases(self) -> None:
        out = _node_eval(
            """(function(){
              var W = g.CartFlowUiV2Workspace;
              function paint(card){
                return W.render({quiet:false, zone_b:[Object.assign({is_primary_decision:true, decision_id:'d1'}, card)]});
              }
              var nme = paint({execution_readiness:'NEEDS_MORE_EVIDENCE', decision_sentence_ar:'راجع القرار', evidence_lines_ar:['1','2','3','4','5','6','7','8','9']});
              var ready = paint({execution_readiness:'READY', execution_available:true, decision_sentence_ar:'راجع القرار'});
              var ready2 = paint({execution_readiness:'READY', execution_available:true, decision_sentence_ar:'قرار آخر'});
              var conf = paint({execution_readiness:'NEEDS_MORE_EVIDENCE', diagnosis_status:'conflicting_evidence', decision_sentence_ar:'راجع القرار'});
              var quiet = W.render({quiet:true, zone_b:[]});
              function roles(h){ return (h.match(/data-cf2-role="/g)||[]).length; }
              function dens(h){ var m=h.match(/data-cf2-density="([^"]+)"/); return m&&m[1]; }
              function mass(h){ var m=h.match(/data-cf2-mass="([^"]+)"/); return m&&m[1]; }
              function tens(h){ var m=h.match(/cf2-dmass[^>]*data-cf2-tension="([^"]+)"/); return m&&m[1]; }
              return {
                nmeRoles: roles(nme), nmeDens: dens(nme), nmeMass: mass(nme), nmeTens: tens(nme),
                readyRoles: roles(ready), readyDens: dens(ready), readyMass: mass(ready), readyTens: tens(ready),
                ready2Roles: roles(ready2), ready2Mass: mass(ready2),
                confTens: tens(conf), confUnc: conf.indexOf('data-cf2-uncertainty="high"')>=0,
                quietRoles: roles(quiet), quietSilence: quiet.indexOf('data-cf2-silence="quiet"')>=0,
                arriving: nme.indexOf('is-arriving')>=0,
                mtrace: nme.indexOf('cf2-mtrace')>=0
              };
            })()"""
        )
        self.assertGreaterEqual(out["nmeRoles"], 2)
        self.assertLessEqual(out["nmeRoles"], 3)
        self.assertEqual(out["nmeDens"], "low")
        self.assertEqual(out["nmeMass"], "open")
        self.assertEqual(out["nmeTens"], "none")
        self.assertEqual(out["readyRoles"], 1)
        self.assertEqual(out["readyDens"], "present")
        self.assertEqual(out["readyMass"], "ready")
        self.assertEqual(out["readyTens"], "none")
        self.assertEqual(out["ready2Roles"], out["readyRoles"])
        self.assertEqual(out["ready2Mass"], out["readyMass"])
        self.assertEqual(out["confTens"], "high")
        self.assertTrue(out["confUnc"])
        self.assertEqual(out["quietRoles"], 0)
        self.assertTrue(out["quietSilence"])
        self.assertFalse(out["arriving"])
        self.assertFalse(out["mtrace"])

    def test_dashboard_hosts_semantic_layer(self) -> None:
        html = TestClient(app).get("/dashboard?cf_ui=v2").text
        self.assertIn("merchant_ui_v2_semantic_model.js", html)
        self.assertIn("semantic-visual-model-v1", html)
        ident = TestClient(app).get("/dev/merchant-runtime-identity").json()
        self.assertEqual(ident.get("semantic_model_version"), SEMANTIC_MODEL_VERSION)
        self.assertEqual(ident.get("visual_system_version"), "merchant-visual-system-v1")


class SemanticOperationalRegressionTests(unittest.TestCase):
    def test_dashboard_v2_and_identity(self) -> None:
        r = TestClient(app).get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), "merchant_ui_v2")
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Semantic-Model"),
            SEMANTIC_MODEL_VERSION,
        )
        self.assertIn("cf2-utility", r.text)
        self.assertNotIn("home_executive_summary_v1.js", r.text)

    def test_summary_and_workspace_routes_exist(self) -> None:
        self.assertIn("/api/dashboard/summary", HOME_JS)
        self.assertIn("/api/cart-workspace/v1/projection", WS_JS)
        self.assertIn("qpool1", V2_HTML)
