# -*- coding: utf-8 -*-
"""Probe official homepage for Premium vs old landing markers."""
from __future__ import annotations

import hashlib
import re
import time
import urllib.request

URL = f"https://smartreplyai.net/?v={int(time.time())}"
req = urllib.request.Request(
    URL,
    headers={
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "CartFlow-MismatchProbe/1.0",
    },
)
with urllib.request.urlopen(req, timeout=45) as resp:
    raw = resp.read()
    headers = {k.lower(): v for k, v in resp.headers.items()}
    status = getattr(resp, "status", 200)

html = raw.decode("utf-8")
print("url", URL)
print("status", status)
print("len", len(raw))
print("server", headers.get("server"))
print("edge", headers.get("x-railway-edge"))
print("cache_control", headers.get("cache-control"))
print("old_headline", "ليس مجرد رسائل" in html)
print("new_headline", "استعِد ما فات" in html)
print("cf_browser_hero", "cf-browser--hero" in html)
print("dashboard_img", "landing_v1/dashboard.png" in html)
print("css_href", "cartflow_landing_v1.css" in html)
print("signup", "/signup" in html)
print("login", "/login" in html)
print("sha16", hashlib.sha256(raw).hexdigest()[:16])
title = re.search(r"<title>([^<]+)</title>", html)
print("title", title.group(1) if title else None)
h1 = re.search(r'id="hero-title">(.*?)</h1>', html, re.S)
if h1:
    text = re.sub(r"<[^>]+>", "", h1.group(1))
    text = re.sub(r"\s+", " ", text).strip()
    print("h1", text[:140])

with urllib.request.urlopen(
    "https://smartreplyai.net/static/cartflow_landing_v1.css", timeout=30
) as css_resp:
    css = css_resp.read().decode("utf-8", "replace")
print("css_premium_marker", "Premium Visual Upgrade V1" in css)
print("css_len", len(css))
