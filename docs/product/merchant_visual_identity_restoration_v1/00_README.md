# Merchant Visual Identity Restoration & Regression Prevention V1

**Status:** local candidate — production proof required  
**Parent:** `480d7d52`  
**Canonical route:** `/dashboard`  
**Canonical UI:** V2 · `merchant_app_v2.html` · `merchant_ui_v2`  
**Visual system:** `merchant-visual-system-v1`

This pack is the binding contract that makes the approved CartFlow identity the only canonical production render, and makes silent fallback to the older dashboard detectable and blocked.

It does **not** redesign surfaces. Home / Workspace language primitives (P12–P16) already emit on the current V2 painters. The material defect was **runtime selection**, not missing CSS.
