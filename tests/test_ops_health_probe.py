# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class OpsHealthProbeTests(unittest.TestCase):
    def test_health_without_db_probe(self) -> None:
        c = TestClient(app)
        r = c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue((r.json() or {}).get("ok"))
        self.assertNotIn("database", r.json() or {})

    def test_health_with_db_probe(self) -> None:
        c = TestClient(app)
        r = c.get("/health?db=1")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json() or {}
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("database"), "ok")


if __name__ == "__main__":
    unittest.main()
