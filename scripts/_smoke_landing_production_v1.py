# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
from main import app

c = TestClient(app)
r = c.get("/")
html = r.text
print("status", r.status_code)
for k in (
    "cartflow_landing_v1.css",
    'id="hero"',
    'id="widget"',
    'id="dashboard"',
    'id="knowledge"',
    "PLACEHOLDER",
    "/signup",
    "landing_v1/widget.png",
    "landing_v1/dashboard.png",
):
    print(("OK" if k in html else "MISS"), k)
