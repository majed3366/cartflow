# Commercial Action Language Contract V1

Merchant-facing action language for the four current decision kinds only.

**DEPLOY: NO.** CTA `اعتمد هذه المهمة` is frozen.

## Law

Every recommendation answers, where applicable:

1. What should I do?
2. Where / on what?
3. Why is this the next step?
4. What should I not do yet?
5. What will CartFlow measure?
6. When will CartFlow recheck?

Vague openers (`راجع` / `حسّن` / `افصل` / `راقب` / `انتبه`) are forbidden unless the sentence immediately names the concrete object and change. Internal surface name «ودجت» is not merchant language.

Truth boundary is unchanged: association ≠ causation; store-level ≠ product-level; insufficient stays insufficient; no discount without evidence; no visit/exposure claims.

## Overlay

`services/commercial_action_language_v1/` rewrites merchant-visible action fields after COL/OGL compose. Ranking, thresholds, windows, CDC, and portfolio are untouched.

## CTA

Acceptance still means **decision accepted**, not execution started.

## Actions (merchant-facing)

- **shipping_friction:** اجعل أسباب التردد التي يختارها العميل عند الشحن تفرّق بوضوح بين «تكلفة الشحن مرتفعة» و«مدة التوصيل طويلة» — حتى نعرف أيّهما يوقف الشراء.
- **product_confidence:** أظهر في صفحة المنتج ما يثبت الجودة أو الضمان مما هو قائم فعلاً (مثل مدة الضمان أو ما يشمله المنتج) — بلا تقييمات أو شهادات غير موجودة.
- **price_hesitation:** بيّن في صفحة المنتج ماذا يحصل عليه العميل مقابل السعر الحالي قبل أي تخفيض — ثم نعيد قراءة حصة سبب السعر.
- **wait_insufficient_evidence:** أبقِ السعر والشحن والعرض كما هي، وواصل تسجيل أسباب تردد العملاء حتى يظهر سبب واحد بوضوح كافٍ.
