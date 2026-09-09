# Contract Projections V1

Design-only projections. These are contract shapes, not rendered output, and
nothing here is implemented or deployed.

## 1. R17 projection — shipping 12/20 = 60%

Current truth: `hesitation_total = 20`, `hesitation_top = shipping:12`,
`share = 0.60`. COL classifies this `PRODUCTION_TRUTH_READY`.

```yaml
intervention_id: "civ1:shipping_friction:2:clarify_cost_vs_duration"
family: shipping_friction
recommendation_level: 2
eligibility_state: ELIGIBLE
conflict_group: disclosure_only

what_we_see_ar: "أقوى تردد مسجّل الآن مرتبط بالشحن."
evidence_ar: "12 من 20 سبب تردد مسجّل (60٪)."

what_we_suggest_ar: >
  وضّح تكلفة الشحن ومدة التوصيل، وحدّد أيهما يتكرر قبل تغيير السعر أو العرض.

why_this_is_safe_ar: >
  هذا التدخل لا يغيّر سعرك ولا تكلفة الشحن التي تتحملها — يوضّح المعلومة فقط.

blocked_candidates:
  - level: 3
    class: "شحن مجاني / دعم الشحن / حد شحن"
    blocked_reason: ECONOMIC_INPUTS_REQUIRED
    missing_inputs: [shipping_cost, shipping_subsidy, product_cost, gross_margin, margin_floor]
    merchant_ar: >
      لا نقترح شحنًا مجانيًا أو حدًّا للشحن لأننا لا نعرف تكلفة الشحن التي تتحملها
      ولا هامشك — لا نستطيع إثبات أن التدخل لن يخسّرك.

dont_do_ar: "لا تخفض السعر ولا تجعل الشحن مجانيًا الآن."

primary_metric: "حصة أسباب الشحن من إجمالي أسباب التردد"
guardrail_metric: "لا تراجع في تحوّل السلة إلى شراء"
measurement_window: 7
recheck_condition: "بلوغ حد الكفاية المعتمد، أو انخفاض واضح في حصة الشحن"

success_condition: "انخفاض حصة الشحن، أو اتضاح أن السبب هو التكلفة أو المدة"
failure_condition: "بقاء الحصة كما هي مع استمرار الالتباس بين التكلفة والمدة"
mind_change_condition: "انتقال التردد الأقوى إلى عائلة أخرى (سعر أو ثقة منتج)"

evidence_refs:
  - "hesitation_total:20"
  - "hesitation_top:shipping:12"
  - "hesitation_share:0.60"
```

Diagnosis is unchanged from what production emits today. Level is 2. No monetary
value, threshold, or direction appears anywhere in the merchant-facing fields.
Measurement reuses the existing hesitation and purchase contracts, and recheck
reuses existing mission recheck semantics.

The 60% share is what makes the problem worth attention; it is not evidence about
*which* shipping intervention works. Escalating on share alone is the error this
contract structurally prevents.

## 2. Insufficient-evidence projection

Truth: `hesitation_total = 4`, no dominant reason. COL classifies `INSUFFICIENT`.

```yaml
intervention_id: "civ1:wait_insufficient_evidence:0:hold"
family: wait_insufficient_evidence
recommendation_level: 0
eligibility_state: INSUFFICIENT_EVIDENCE
conflict_group: null

what_we_see_ar: "الأدلة الحالية لا تكفي لتوصية بتغيير تجاري."
evidence_ar: "عيّنة أسباب التردد الحالية (4) لم تستوفِ حد الكفاية المعتمد، ولا يوجد سبب واحد مهيمن."

what_we_suggest_ar: >
  أبقِ السعر والشحن والعرض كما هي، وواصل تسجيل أسباب تردد العملاء حتى يظهر سبب واحد بوضوح كافٍ.

why_this_is_safe_ar: >
  الانتظار هنا قرار — التوصية على عيّنة غير كافية توجّه متجرك في الاتجاه الخطأ.

blocked_candidates:
  - level: 2
    blocked_reason: INSUFFICIENT_EVIDENCE
    merchant_ar: "لا نقترح تدخلاً الآن لأن العيّنة لا تكفي لتحديد السبب."

dont_do_ar: "لا تغيّر سعراً أو شحناً أو عرضاً بناءً على عيّنة غير كافية."

primary_metric: "عدد أسباب التردد المسجّلة وظهور سبب مهيمن"
guardrail_metric: null
measurement_window: 7
recheck_condition: "عندما تصل العيّنة إلى حد الكفاية المعتمد ويظهر سبب واحد مهيمن"
mind_change_condition: "ظهور سبب مهيمن واحد ضمن حد الكفاية"
```

The merchant sees a reasoned position, not an empty card. The card states what is
being waited for, why waiting is the correct action, and what will end the wait.

`guardrail_metric` is null because nothing is being changed. A guardrail on an
unchanged store would be theatre.

## 3. Future Level 3 projection

Design-only. Not emittable. No real numbers, and none are invented — every
economic quantity is a placeholder that resolves only from an authoritative
input.

Precondition: all of `shipping_cost`, `shipping_subsidy`, `product_cost`,
`gross_margin`, `margin_floor`, `payment_fees`, `platform_commission` registered,
fresh, and store-scoped.

```yaml
intervention_id: "civ1:shipping_friction:3:free_shipping_threshold"
family: shipping_friction
recommendation_level: 3
eligibility_state: ELIGIBLE            # only if every input below resolves
conflict_group: shipping_economics

required_economic_inputs:
  [shipping_cost, shipping_subsidy, product_cost, gross_margin, margin_floor,
   payment_fees, platform_commission, AOV]
missing_inputs: []                     # must be empty, else ECONOMIC_INPUTS_REQUIRED

economic_safety_check:
  intervention_direct_cost: "<SHIPPING_COST>"
  margin_after_intervention: "<GROSS_MARGIN> − <SHIPPING_COST>"
  margin_floor: "<MERCHANT_DECLARED_MARGIN_FLOOR>"
  assertion: "margin_after_intervention >= margin_floor"
  stop_loss_condition: "تجاوز دعم الشحن التراكمي <SUBSIDY_BOUND> قبل نهاية النافذة"

what_we_suggest_ar: "اختبر الشحن المجاني فوق <THRESHOLD> ر.س."

primary_metric: "التحوّل إلى شراء"
guardrail_metrics: ["متوسط قيمة السلة", "الهامش بعد التدخل", "إنفاق دعم الشحن"]
measurement_window: 7
```

`<THRESHOLD>` is derived from AOV and margin floor together; it is never chosen
as a round number. Three guardrails are required because free shipping can raise
conversion while destroying margin, and a single-metric read would score that as
success.

Reaching this state is an acquisition problem, not a copy problem. Until the
manifest resolves, this projection stays a document.
