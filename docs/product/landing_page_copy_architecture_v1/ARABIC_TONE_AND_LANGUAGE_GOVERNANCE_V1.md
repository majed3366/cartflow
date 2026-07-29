# Arabic Tone and Language Governance V1

**Status:** Binding Arabic language system for future landing copy.  
**Date (UTC):** 2026-07-29  
**Parent pack:** Landing Page Copy Architecture V1  
**Audience of this doc:** Product, language reviewers, future copywriters  

Examples in §4.10 are **tone governance only**. They are **not** approved landing copy.

---

## 4.1 Audience

**Primary:** Saudi and Gulf e-commerce merchants.

Must work for:

- Non-technical store owners  
- Operators  
- Small teams  
- Growing merchants  
- Decision-makers evaluating SaaS tools  

Must **not** require technical or marketing expertise.

Target felt outcome:

```text
هذه الصفحة تفهم المشكلة التي أعيشها في متجري.
```

---

## 4.2 Language register

Use **clear Modern Arabic** with natural **Gulf commercial familiarity**.

| Be | Do not become |
|----|----------------|
| Clear | Formal government Arabic |
| Calm | Dialect-heavy |
| Confident | Overly literary |
| Specific | Translated SaaS Arabic |
| Respectful | Technical jargon |
| Direct | Aggressive sales copy |
| Human | Corporate press-release Arabic |

Original Arabic product experience — **not** a translation of an English landing page.

---

## 4.3 Addressing the merchant

### Approved point of view (binding)

Address the merchant in the **second person** tied to the store:

| Prefer | Role |
|--------|------|
| متجرك | The store as the merchant’s world |
| عملاؤك | Customers of that store |
| تستطيع / ترى / تعرف | Merchant capability / perception |

### Consistency rule

Do **not** unstable-switch between:

- أنت (alone without store anchor)  
- التاجر (third-person lecture)  
- أصحاب المتاجر (broadcast plural)  
- المستخدم  
- العميل (when meaning the merchant)

**Rule:** Merchant = «أنت» via متجرك / عملاؤك.  
Store customer = «العميل» / «عملاؤك».  
CartFlow = «CartFlow» (brand) or «نـ…» only in journey outline where “we observe” is intentional (LP-05 path) — do not mix «نحن» lecture with «أنت» blame.

LP-05 governed path may use first-person plural product voice («نلاحظ») as system voice; elsewhere prefer merchant-facing «ترى / تستطيع».

---

## 4.4 Preferred vocabulary

| Concept | Preferred Arabic | Permitted alternative | English retained? | Avoid | Reason |
|---------|------------------|----------------------|-------------------|-------|--------|
| Store | المتجر / متجرك | — | No | المنصة (for merchant store) | Platform ≠ store |
| Merchant | أنت via متجرك | التاجر (rare, FAQ only) | No | المستخدم | SaaS translation smell |
| Customer | العميل / عملاؤك | الزائر (pre-purchase browsing only) | No | اليوزر | Borrowed noise |
| Purchase | الشراء / إتمام الشراء | الطلب المكتمل | No | الكونفرجن (alone) | Keep Arabic primary |
| Checkout | إتمام الطلب / صفحة الدفع | — | Checkout rare | التشيك آوت | Prefer Arabic |
| Abandoned cart | السلة المتروكة | سلة لم تُكمَّل | No | الكارت المهجور (harsh/odd) | Merchant-familiar |
| Hesitation | التردد | التردد قبل الشراء | No | الهيزيتيشن | Natural Arabic |
| Recovery (action) | الاستعادة / استعادة فرص الشراء | متابعة العميل بعد الترك | No | استرجاع الإيرادات (as guaranteed) | Revenue not confirmed until purchase |
| Return to store | العودة إلى المتجر | — | No | الريتيرن | Clear |
| Customer movement | حركة العميل | تنقّل العميل | No | الجرني (alone) | Prefer Arabic |
| Evidence | الدليل / الأدلة | ما حدث فعليًا | No | البيانات (as if = conclusion) | Data ≠ conclusion |
| Knowledge | فهم المتجر / معرفة تتكون من الأدلة | الأنماط المتكررة | No as section brand | طبقة المعرفة (internal) | Don’t expose internal layer name |
| Insight | ملاحظة مبنية على دليل | نمط متكرر | No | إنسایت | Avoid import |
| Recommendation | توصية | اقتراح عند كفاية الدليل | No | توصية مضمونة | Must be evidence-bound |
| Decision | القرار | قرار تشغيلي | No | — | Clear |
| Attention | ما يحتاج انتباهك | الأولوية الآن | No | التنبيهات العاجلة (hype) | Calm |
| Insufficient evidence | لا توجد أدلة كافية بعد | الدليل غير كافٍ | No | لا توجد بيانات (ambiguous) | Honesty without “broken” |
| Widget | أداة داخل المتجر | — | Widget OK in parentheses once | الودجيت as sole term forever | See §4.5 |
| WhatsApp journey | رحلة واتساب / المتابعة عبر واتساب | — | WhatsApp yes | واتساب ذكي | Brand name OK; “smart” hype no |
| Dashboard | لوحة المتجر | لوحة CartFlow | No | الداشبورد alone | See §4.5 |
| Product/category behaviour | سلوك المنتج / سلوك التصنيف | — | No | — | Specific |
| Conversion | إتمام الشراء / التحويل إلى شراء | — | Conversion rare | — | Prefer Arabic phrase |
| Traffic | زيارات المتجر / حركة الزيارات | — | Traffic rare | ترافيك | Prefer Arabic |

---

## 4.5 Terminology decisions (resolved)

### Widget — **primary landing expression**

| Decision | **أداة داخل المتجر** |
|----------|----------------------|
| Permitted | First mention may add `(Widget)` once for recognition |
| Avoid as primary | الودجيت · نافذة المساعدة · أداة التفاعل (too vague/cute) |
| Reason | Merchant-clear; not slang; not settings language |

### Dashboard — **primary landing expression**

| Decision | **لوحة المتجر** |
|----------|-----------------|
| Permitted | لوحة CartFlow when distinguishing product UI |
| Avoid as primary | لوحة التحكم (generic admin smell) · واجهة التاجر (abstract) · الداشبورد |
| Reason | Merchant owns a store, not an “admin panel” identity |

### Knowledge Layer — **primary landing expression**

| Decision | **فهم المتجر** / **ما يتضح من الأدلة** |
|----------|----------------------------------------|
| Permitted | الأنماط المتكررة · معرفة مبنية على الدليل |
| Avoid on landing | طبقة المعرفة · Knowledge Layer as Arabic section brand |
| Reason | Internal product term; landing must earn understanding without lab vocabulary |

### Recovery — **primary landing expression**

| Decision | **الاستعادة** / **استعادة فرص الشراء** |
|----------|------------------------------------------|
| Permitted | متابعة العملاء بعد الترك (when emphasizing continuation) |
| Avoid | استرجاع الإيرادات as if purchase already recovered; استرجاع المبيعات المضمونة |
| Reason | Truth: opportunity ≠ confirmed revenue |

### Evidence — **primary landing expression**

| Decision | **الدليل / الأدلة** |
|----------|---------------------|
| Permitted | ما حدث فعليًا · إشارات (early/weak only, never as conclusion) |
| Avoid | البيانات as synonym for conclusion; إثبات قاطع without basis |
| Reason | Preserves observation vs conclusion (Trust Law) |

---

## 4.6 Sentence rules

### Prefer

- Short to medium sentences  
- One claim per sentence  
- Concrete verbs  
- Clear cause → effect  
- Direct merchant relevance  
- Active voice  
- Natural Arabic rhythm  

### Avoid

- Long nested sentences  
- Three+ claims in one paragraph  
- Excessive nominal phrasing  
- English word order forced into Arabic  
- Repeated «من خلال» / «حيث» / «بهدف»  
- Empty rhetorical questions  
- Excessive punctuation  
- Multiple exclamation marks  

---

## 4.7 Claim modality

### Prefer (evidence-aware)

| Form | Use when |
|------|----------|
| يساعدك | Decision support / outcomes |
| يمكنه | Capability that exists in product |
| قد يكشف / قد تتضح | Pattern discovery (conditional) |
| عندما تتوفر أدلة كافية | Knowledge / recommendation threshold |
| يعرض | Dashboard / UI truth |
| يتابع | Journey continuation |
| يفصل | Observation vs conclusion |
| يوضح | Readiness / states / honesty |

### Forbidden / blocked as default

| Form | Why |
|------|-----|
| يضمن | False certainty |
| يعرف دائمًا | Violates insufficient-evidence honesty |
| يمنع (absolute) | Overclaim (e.g. prevents all abandons) |
| يحل | Magic solve |
| يضاعف | Unproven ROI |
| يتنبأ بدقة | Unsupported prediction |
| يتخذ القرار عنك | Autonomy overclaim |

---

## 4.8 Saudi / Gulf market sensitivity

Copy may **acknowledge** local merchant realities:

- Shipping cost hesitation  
- Cash-flow pressure  
- WhatsApp-centric communication  
- Zid / Salla platform context  
- Mobile-heavy shopping  
- Discount dependency  
- Setup complexity  
- Storefront speed concerns  
- Distrust of opaque recommendations  

**Do not** turn these into stereotypes, fear tactics, or unsupported claims (“كل متاجر السعودية…”).

---

## 4.9 Numerals, names, and English terms

| Item | Governance |
|------|------------|
| Numerals | Prefer **Western digits** `0–9` for UI consistency with product; keep consistent page-wide |
| Platform names | زد · سلة · Shopify (as commonly recognised); no fake logos |
| WhatsApp | واتساب (Arabic script) or WhatsApp — pick one primary; recommend **واتساب** in body |
| CartFlow | **CartFlow** Latin brand always |
| Widget | Arabic primary «أداة داخل المتجر»; optional `(Widget)` once |
| CTA labels | Arabic verbs; calm; see prohibited CTA list in Copy Architecture LP-15 |
| English product names | Retain brand/platform names; explain in Arabic |
| Currency | Use only if real and necessary; no fake SAR uplift |
| Percentages | Forbidden unless verified Truth Policy evidence |
| Dates | Rare on landing; if used, clear Arabic date form |
| Technical terms | Avoid; if unavoidable, Arabic gloss first |

---

## 4.10 Tone examples (non-final — not approved copy)

### Too translated

```text
تمكين التجار من تعظيم استعادة الإيرادات عبر منصة مدعومة بالذكاء الاصطناعي.
```

### Too corporate

```text
نقدّم حلولًا متكاملة ترتقي بكفاءة العمليات التجارية وتعزّز منظومة اتخاذ القرار.
```

### Too promotional

```text
ضاعف مبيعاتك الآن مع أقوى أداة استعادة في المنطقة!
```

### Too technical

```text
يقوم النظام بالتقاط أحداث التردد وربطها بحزم الأدلة عبر طبقة المعرفة قبل إصدار التوجيه.
```

### Approved direction (tone only — not final landing copy)

```text
السلة المتروكة ظاهرة. غالبًا السبب ليس كذلك.
CartFlow يساعدك على استعادة فرص الشراء، وفهم ما يمنع العميل من الإتمام عندما تتوفر أدلة كافية.
```

```text
رسالة واتساب ليست نهاية القصة. المهم ما يحدث بعدها: رد، عودة، شراء — أو توقّف عند الشراء.
```

```text
عندما لا يكفي الدليل، يقولها CartFlow بوضوح. لا يملأ الفراغ بالتخمين.
```

---

## 4.11 Emotional register by journey stage

| Stage | Tone |
|-------|------|
| Hero / Problem | Recognising, concrete, calm urgency |
| Reframe | Fair, clarifying, non-attacking |
| Journey outline | Simple, stepwise |
| Evidence sections | Specific, proof-led, humble |
| Knowledge | Earned confidence + honest uncertainty |
| Decision / Continuity | Practical, conditional |
| Trust | Steady, restrained |
| CTA | Calm invitation |

---

## 4.12 Prohibited global phrases (landing)

Including but not limited to:

- منصة ذكاء تجاري / Commerce Intelligence Platform (unless separately approved)  
- مدعوم بالذكاء الاصطناعي / AI-powered  
- ثوري / ثورة في التجارة  
- نتائج مضمونة / نمو مضمون  
- رؤية 360 درجة / تحكم كامل  
- ابدأ النجاح الآن / لا تفوّت الفرصة  
- انضم لآلاف المتاجر (without truth)  
- متجرك ينزف / أنت تخسر كل يوم  

---

## Approval

Terminology and tone in this file govern future final copy.  
Final headlines, CTAs, and FAQ answers remain unauthorised until language approval.
