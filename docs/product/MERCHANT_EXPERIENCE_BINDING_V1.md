# Merchant Experience Binding V1 — Validation

**Date (UTC):** 2026-07-22
**Simulation:** `srs_921fb5de70e349e4ad6bc909483d5002`
**Constraints:** no fixtures · no demo_fixture · BFL consume only · no KF/OT/BFL producer changes

## Binding audit

| Surface | Renderer | Prior source | Canonical source | Binding |
|---------|----------|--------------|------------------|---------|
| Home | `applyHome` MEIF JS | SCF/OT/KF | `business_findings` via BFL consume | `sections.business_findings` + paint |
| Decision | `applyDecision` | SCF review_items | BFL destinations | `sections.business_findings` |
| Carts | `applyCarts` | OT composition | BFL cart destinations | `sections.business_findings` |
| Communication | `applyCommunication` | OT composition | BFL WA destinations | `sections.business_findings` |

## Materialize (historical)

- persisted: 6 · surface_eligible: 5

## MEIF binding

- home_bound: 5
- findings_bound: 5
- ok: True

## Home paint

- painted finding cards: **7**
- titles: ['التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة', 'سلوك العملاء يشير حالياً إلى اتجاهات متعارضة', 'أسباب التردد موزّعة — لا سبب مهيمن بوضوح بعد', 'فعالية واتساب التجارية ما زالت قيد التشكّل', 'لا يمكن بعد التمييز بين ضعف الزيارات وضعف التحويل', 'التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة', 'فعالية واتساب التجارية ما زالت قيد التشكّل']
- screenshots: ['01_desktop_home_business_finding.png', '02_mobile_home_business_finding.png']

### Render diagnostics

```json
{
  "binding_version": "mebf_v1",
  "surface": "home",
  "findings_bound": "5",
  "home_bound": "5",
  "diagnostics": [
    {
      "finding_id": "finding:recovery_channel_effectiveness_v1:widget",
      "finding_type": "recovery_channel_effectiveness_v1",
      "surface_requested": [
        "home",
        "carts"
      ],
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": "None",
      "surface_rendered": "home"
    },
    {
      "finding_id": "finding:insufficient_or_conflicting_evidence_v1:conflict",
      "finding_type": "insufficient_or_conflicting_evidence_v1",
      "surface_requested": [
        "home"
      ],
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": "None",
      "surface_rendered": "home"
    },
    {
      "finding_id": "finding:dominant_hesitation_reason_v1:not_dominant",
      "finding_type": "dominant_hesitation_reason_v1",
      "surface_requested": [
        "home"
      ],
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": "None",
      "surface_rendered": "home"
    },
    {
      "finding_id": "finding:recovery_channel_effectiveness_v1:whatsapp",
      "finding_type": "recovery_channel_effectiveness_v1",
      "surface_requested": [
        "home",
        "communication"
      ],
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": "None",
      "surface_rendered": "home"
    },
    {
      "finding_id": "finding:traffic_versus_conversion_v1",
      "finding_type": "traffic_versus_conversion_v1",
      "surface_requested": [
        "home"
      ],
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": "None",
      "surface_rendered": "home"
    }
  ],
  "paint_events": [
    {
      "finding_id": "finding:recovery_channel_effectiveness_v1:widget",
      "finding_type": "recovery_channel_effectiveness_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    },
    {
      "finding_id": "finding:insufficient_or_conflicting_evidence_v1:conflict",
      "finding_type": "insufficient_or_conflicting_evidence_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    },
    {
      "finding_id": "finding:dominant_hesitation_reason_v1:not_dominant",
      "finding_type": "dominant_hesitation_reason_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    },
    {
      "finding_id": "finding:recovery_channel_effectiveness_v1:whatsapp",
      "finding_type": "recovery_channel_effectiveness_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    },
    {
      "finding_id": "finding:traffic_versus_conversion_v1",
      "finding_type": "traffic_versus_conversion_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    }
  ]
}
```

**Acceptance (Home paints ≥1 real finding):** `True`

### Proof path (historical → pixels)

```
SRS historical demo (May window)
  → BFL materialize (load_db, no fixtures)
  → business_findings rows (persisted / surface_eligible)
  → MEIF attach consumes via load_current_findings_package_v1
  → sections.business_findings on Home
  → applyHome paints meif-card--finding (finding_id + contract)
  → screenshot 01_desktop_home_business_finding.png
```

Example painted finding: `finding:dominant_hesitation_reason_v1:not_dominant`  
Evidence: `top=delivery:…` · confidence low · full render contract on Home.

## STOP

Screenshots + diagnostics submitted. **No commit. No PR.**
