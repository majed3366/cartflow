# Merchant Experience Binding V1 — Validation

**Date (UTC):** 2026-07-24
**Simulation:** `srs_584d8f5bfe3d4c8fa9e117c8c8f4e226`
**Constraints:** no fixtures · no demo_fixture · BFL consume only · no KF/OT/BFL producer changes

## Binding audit

| Surface | Renderer | Prior source | Canonical source | Binding |
|---------|----------|--------------|------------------|---------|
| Home | `applyHome` MEIF JS | SCF/OT/KF | `business_findings` via BFL consume | `sections.business_findings` + paint |
| Decision | `applyDecision` | SCF review_items | BFL destinations | `sections.business_findings` |
| Carts | `applyCarts` | OT composition | BFL cart destinations | `sections.business_findings` |
| Communication | `applyCommunication` | OT composition | BFL WA destinations | `sections.business_findings` |

## Materialize (historical)

- persisted: 5 · surface_eligible: 4

## MEIF binding

- home_bound: 4
- findings_bound: 4
- ok: True

## Home paint

- painted finding cards: **10**
- titles: ['التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة', 'فعالية واتساب التجارية ما زالت قيد التشكّل', 'أسباب التردد موزّعة — لا سبب مهيمن بوضوح بعد', 'لا يمكن بعد التمييز بين ضعف الزيارات وضعف التحويل', 'التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة', 'أسباب التردد موزّعة — لا سبب مهيمن بوضوح بعد', 'فعالية واتساب التجارية ما زالت قيد التشكّل', 'لا يمكن بعد التمييز بين ضعف الزيارات وضعف التحويل', 'التفاعل يلتقط أسباب التردد لكن بيانات التواصل ما زالت ضعيفة', 'فعالية واتساب التجارية ما زالت قيد التشكّل']
- screenshots: ['01_desktop_home_business_finding.png', '03_desktop_home_decisions.png', '02_mobile_home_business_finding.png', '04_mobile_home_decisions.png']

### Render diagnostics

```json
{
  "binding_version": "mebf_v1",
  "surface": "home",
  "findings_bound": "4",
  "home_bound": "4",
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
      "finding_id": "finding:recovery_channel_effectiveness_v1:whatsapp",
      "finding_type": "recovery_channel_effectiveness_v1",
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
      "finding_id": "finding:traffic_versus_conversion_v1",
      "finding_type": "traffic_versus_conversion_v1",
      "surface_requested": "home",
      "renderer_invoked": true,
      "render_accepted": true,
      "render_skipped": false,
      "skip_reason": null
    },
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

## STOP

Screenshots + diagnostics submitted. No commit requested.
