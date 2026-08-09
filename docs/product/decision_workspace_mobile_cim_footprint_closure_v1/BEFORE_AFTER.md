# BEFORE / AFTER — Mobile CIM Footprint Closure V1

## Root cause

`merchant_ui_v2_language.css`:

```css
.cf2-evfield[data-cf2-density="sparse"] {
  gap: 16px;
  min-height: 100px;
}
```

On mobile Workspace this produced a tall semi-empty signal band above the first evidence bullet.

## Before

- Sparse field ~100px tall
- Large empty vertical zone under «الأدلة ما زالت محدودة»
- Evidence statement delayed

Evidence: `01_mobile_430_before.png`, `03_mobile_390_before.png`

## After (`d52da0b`)

- Mobile Workspace field ~16px tall, `min-height: 0`
- Confidence → first evidence gap ~24px
- CIM bars still present; Living Route retained
- Desktop sparse field remains 100px

Evidence: `02_mobile_430_after.png`, `04_mobile_390_after.png`
