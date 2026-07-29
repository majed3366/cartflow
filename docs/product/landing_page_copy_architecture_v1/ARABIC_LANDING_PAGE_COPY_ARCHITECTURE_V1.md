# Arabic Landing Page Copy Architecture V1

**Status:** Governed product-copy architecture — message structure only.  
**Date (UTC):** 2026-07-29  
**Governing authorities:**  
- Landing Page Constitution V1 (`docs/product/landing_page_constitution_v1/`)  
- Landing Page Information Architecture V1 (`docs/product/landing_page_information_architecture_v1/`)  

**Non-goals:** No final Arabic copy. No redesign. No Figma. No screenshots. No frontend/UI change.

This document defines **what each section must say, make the merchant feel, and prepare them to understand next**. Final production wording remains unauthorised.

---

## 0. Governing principle

The Arabic landing page is an **original Arabic product experience**.

It must not feel like:

- A literal English translation  
- Imported SaaS language  
- Corporate Arabic  
- Technical documentation  
- Advertising hype  
- A feature catalogue  

The merchant should feel:

```text
هذه الصفحة تفهم المشكلة التي أعيشها في متجري.
```

Not:

```text
هذه ترجمة عربية لموقع أجنبي.
```

### Cognitive journey (binding)

```text
التعرّف على المشكلة
        ↓
الشعور بأن المشكلة أعمق من السلة المتروكة
        ↓
فهم الفرق بين الاستعادة والفهم
        ↓
فهم رحلة CartFlow
        ↓
رؤية الدليل الحقيقي
        ↓
اكتشاف المعرفة المتراكمة
        ↓
فهم أثرها على القرار
        ↓
بناء الثقة
        ↓
اتخاذ خطوة هادئة
```

**Disclosure lock:** Broader CartFlow identity is earned at **LP-09**. It must not be claimed in the Hero.

---

## 1. Contradiction log

| ID | Topic | Finding |
|----|-------|---------|
| CX-01 | None found | No genuine contradiction between Constitution V1, Information Architecture V1, and this Copy Architecture. Constitution section names (Difference / Problem / Benefits / Merchant Journey) map to IA LP-04 / LP-03 / LP-10 / LP-11 as already documented in IA §1. |

If a contradiction is discovered later, document it here — do not silently rewrite Constitution or IA.

---

## 2. Message architecture by section

### LP-01 — Navigation

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-01` |
| **Merchant State Before Reading** | Arriving; scanning for brand and how to begin. |
| **Merchant Question** | أين أنا، وكيف أبدأ؟ |
| **Message Objective** | Orient without opening a second sales story. |
| **Single Core Message** | You are on CartFlow; one calm start path is available. |
| **Supporting Message Roles** | Brand recognition; essential anchors only; Login; one primary start action. |
| **Required Emotional Shift** | From unknown → oriented. |
| **Required Merchant Belief** | أستطيع البدء بهدوء عندما أكون جاهزًا. |
| **Permitted Claim Depth** | Commercial availability of begin path only (no product promises). |
| **Evidence Dependency** | Paths `/signup` and `/login` must remain real. |
| **Arabic Language Direction** | Minimal labels; merchant-familiar verbs; no slogans. |
| **Preferred Sentence Shape** | Words / short labels — not sentences. |
| **CTA Role** | Primary start; Login secondary — never equal promotional weight. |
| **Transition Into Next** | Hands full attention to Hero without competing. |
| **Prohibited Messaging** | Marketing slogan; feature explanation; promotional badge; urgency; multiple equal CTAs; «أفضل منصة»; «ابدأ النجاح الآن». |
| **Copy Readiness** | Architecture ready; final labels later under Tone Governance. |

---

### LP-02 — Hero

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-02` |
| **Merchant State Before Reading** | May believe CartFlow is another abandoned-cart or WhatsApp tool. |
| **Merchant Question** | هل يعالج CartFlow مشكلة أعرفها؟ |
| **Message Objective** | Make the merchant recognise a real commercial problem immediately. |
| **Single Core Message** | Recover missed revenue today while beginning to reveal what prevents customers from completing purchases — problem first, not category first. |
| **Supporting Message Roles** | See role map below. |
| **Required Emotional Shift** | Curiosity → recognition. |
| **Required Merchant Belief** | CartFlow يعالج مشكلة أعرفها، لكنه يرى شيئًا أوسع من مجرد السلة المتروكة. |
| **Permitted Claim Depth** | Problem recognition + light operational foreshadow (recovery + understanding beginnings). Not knowledge platform claims. |
| **Evidence Dependency** | Optional product preview must not drive the message; message stands with or without preview. |
| **Arabic Language Direction** | Merchant pain in natural Gulf-commercial Arabic; concrete store language. |
| **Preferred Sentence Shape** | One dominant short headline idea + one supporting sentence. |
| **CTA Role** | Primary: calm begin (`/signup`). Secondary optional: Login. No Demo until path exists. |
| **Transition Into Next** | Creates need to examine whether the abandoned cart is the full problem. |
| **Prohibited Messaging** | Commerce Intelligence Platform; AI-powered; revolutionary; autonomous intelligence; full transformation; guaranteed growth; fake recovery %; category creation; deep feature explanation. |
| **Copy Readiness** | Architecture ready; final headline unauthorised. |

**Hero role map (not final wording):**

| Role | Job |
|------|-----|
| **Headline** | Name the merchant-recognisable problem / immediate value in one dominant idea. |
| **Supporting line** | Connect recovery with beginning to see what blocks purchase — without knowledge-layer disclosure. |
| **Primary CTA** | Calm next step to `/signup`. |
| **Optional secondary CTA** | Login only. |
| **Product-preview caption** | If preview exists: outcome-oriented, secondary to headline; never a feature inventory. |

**Permitted themes:** Lost revenue; customers leaving before purchase; hesitation; recovery; understanding what blocks purchase; better store visibility.  

---

### LP-03 — Problem Recognition

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-03` |
| **Merchant State Before Reading** | Recognises abandon/lost revenue pain from Hero. |
| **Merchant Question** | هل السلة المتروكة هي المشكلة كاملة؟ |
| **Message Objective** | Expand understanding: causes and movement around the cart are often invisible. |
| **Single Core Message** | The abandoned cart is visible; the why and the movement around it usually are not. |
| **Supporting Message Roles** | Situation beats (see permitted situations); no diagnosis as conclusion. |
| **Required Emotional Shift** | Recognition → deeper urgency (calm, not fear). |
| **Required Merchant Belief** | المشكلة ليست فقط أن العميل لم يشترِ؛ بل أنني لا أعرف لماذا. |
| **Permitted Claim Depth** | Problem recognition only. |
| **Evidence Dependency** | Situations may be illustrative if labeled; no fake stats. |
| **Arabic Language Direction** | Store-life situations; respectful; no blame. |
| **Preferred Sentence Shape** | Short situation statements; one idea per beat. |
| **CTA Role** | None (scroll continues). |
| **Transition Into Next** | Opens: why reminders/discounts alone don’t explain. |
| **Prohibited Messaging** | Final recommendations; definitive diagnosis without evidence; fake statistics; merchant/customer blame; fear copy («أنت تخسر كل يوم»، «متجرك ينزف»). |
| **Copy Readiness** | Architecture ready; situations need natural Arabic drafting later. |

**Permitted situation themes (not final copy):**

- Customer returns more than once but does not purchase  
- Product frequently added, weak completion  
- Return after WhatsApp, still leaves  
- Shipping cost as recurring hesitation  
- Discounts do not change the outcome  
- Traffic exists, conversion remains weak  
- Evidence insufficient for a safe conclusion  

---

### LP-04 — Recovery Limitation Reframe

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-04` |
| **Merchant State Before Reading** | Feels the problem is deeper than the abandon event. |
| **Merchant Question** | لماذا لا تكفي التذكيرات والخصومات وحدها؟ |
| **Message Objective** | Calmly explain incompleteness of recovery actions without understanding. |
| **Single Core Message** | Sending a recovery action ≠ learning what happened before and after that action. |
| **Supporting Message Roles** | Contrast both sides fairly; affirm usefulness without sufficiency. |
| **Required Emotional Shift** | Urgency → reframe (hopeful clarity, not attack). |
| **Required Merchant Belief** | إرسال الرسالة قد يكون مفيدًا، لكنه لا يفسر ما يمنع الشراء. |
| **Permitted Claim Depth** | Problem recognition / category reframe — not product superiority metrics. |
| **Evidence Dependency** | Conceptual; no competitor evidence required. |
| **Arabic Language Direction** | Respectful to existing tools; precise contrast. |
| **Preferred Sentence Shape** | Two-part contrast; short clauses. |
| **CTA Role** | None. |
| **Transition Into Next** | Merchant wants to know CartFlow’s connected approach. |
| **Prohibited Messaging** | «الأدوات التقليدية فاشلة»; «الخصومات لا تعمل»; «المنافسون لا يفهمون»; «واتساب وحده بلا قيمة»; unsupported superiority. |
| **Copy Readiness** | Architecture ready. |

**Core contrast (binding):**

```text
إجراء استعادة
        مقابل
فهم ما حدث قبل الإجراء وبعده
```

---

### LP-05 — How CartFlow Works

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-05` |
| **Merchant State Before Reading** | Accepts that recovery-without-learning is incomplete. |
| **Merchant Question** | ماذا يفعل CartFlow فعليًا؟ |
| **Message Objective** | Simple conceptual understanding of the connected journey. |
| **Single Core Message** | CartFlow connects the customer journey to what the merchant later sees — not isolated steps. |
| **Supporting Message Roles** | Step labels along governed path only; no deep layer tours. |
| **Required Emotional Shift** | Reframe → orientation (“I see the path”). |
| **Required Merchant Belief** | CartFlow لا ينفذ خطوات منفصلة؛ بل يربط رحلة العميل بما يراه التاجر لاحقًا. |
| **Permitted Claim Depth** | Operational capability at outline level only. |
| **Evidence Dependency** | Conceptual; depth proof deferred to LP-06…LP-09. |
| **Arabic Language Direction** | Merchant verbs; no architecture vocabulary. |
| **Preferred Sentence Shape** | Step labels / very short lines; no long paragraphs. |
| **CTA Role** | None. |
| **Transition Into Next** | Need early-hesitation proof (widget). |
| **Prohibited Messaging** | Internal architecture; event names; state machines; provider details; deep Widget/WhatsApp/Dashboard/Knowledge explanation. |
| **Copy Readiness** | Architecture ready. |

**Governed message path:**

```text
نلاحظ حركة العميل
        ↓
نفهم التردد المبكر
        ↓
نبدأ الاستعادة
        ↓
نواصل الرحلة عند الحاجة
        ↓
نتابع العودة والشراء
        ↓
نحوّل ما حدث إلى معرفة أو نصرّح بأن الدليل غير كافٍ
```

---

### LP-06 — Widget Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-06` |
| **Merchant State Before Reading** | Knows the journey outline includes early behaviour. |
| **Merchant Question** | كيف يفهم CartFlow التردد مبكرًا؟ |
| **Message Objective** | Position the in-store tool as early understanding and assistance — not merely an offer surface. |
| **Single Core Message** | Early opportunity to understand hesitation and respond before the customer disappears. |
| **Supporting Message Roles** | Hesitation; calm intervention; reason/choice; storefront journey. |
| **Required Emotional Shift** | Outline → concrete early proof. |
| **Required Merchant Belief** | CartFlow يبدأ بفهم التردد داخل المتجر، وليس بعد مغادرة العميل فقط. |
| **Permitted Claim Depth** | Observed product behaviour (widget). |
| **Evidence Dependency** | **Must appear beside real widget evidence.** |
| **Arabic Language Direction** | Storefront merchant language (see Tone pack for Widget term). |
| **Preferred Sentence Shape** | One claim + one support line beside evidence. |
| **CTA Role** | None. |
| **Transition Into Next** | What continues after the customer leaves. |
| **Prohibited Messaging** | «الودجيت يعرف نية العميل»; mind-reading; guaranteed conversion; «يمنع كل سلة متروكة»; settings-centric; install tech; all-visitors-interact. |
| **Copy Readiness** | Requires product screenshot / evidence capture. |

---

### LP-07 — WhatsApp Journey Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-07` |
| **Merchant State Before Reading** | Believes early in-store understanding is real. |
| **Merchant Question** | ماذا يحدث عندما تستمر الاستعادة خارج المتجر؟ |
| **Message Objective** | WhatsApp as later continuation layer — not product identity. |
| **Single Core Message** | Governed WhatsApp can continue the journey while preserving response, follow-up, return, and purchase states. |
| **Supporting Message Roles** | Timing; continuation; response; follow-up; return; purchase closure; suppression after purchase. |
| **Required Emotional Shift** | Early proof → continuation confidence (not WA-tool identity). |
| **Required Merchant Belief** | رسالة واتساب ليست نهاية العملية؛ CartFlow يتابع ما يحدث بعدها. |
| **Permitted Claim Depth** | Operational claim bounded by provider readiness. |
| **Evidence Dependency** | Beside journey/operational evidence; revalidate Meta/Twilio readiness at publication. |
| **Arabic Language Direction** | Continuation language; avoid blaster vocabulary. |
| **Preferred Sentence Shape** | Outcome sentences tied to states. |
| **CTA Role** | None. |
| **Transition Into Next** | What the merchant sees day-to-day. |
| **Prohibited Messaging** | Bulk/blast; guaranteed delivery/reply; «واتساب ذكي»; AI-writes-messages; Meta theatre; unsupported production-readiness. |
| **Copy Readiness** | Requires evidence capture + operational verification. |

---

### LP-08 — Dashboard Evidence

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-08` |
| **Merchant State Before Reading** | Accepts storefront + WhatsApp layers. |
| **Merchant Question** | ماذا سأرى كتاجر؟ |
| **Message Objective** | Outcome of the dashboard — not a UI tour. |
| **Single Core Message** | Brings together attention, recovery what-happened, customer movement, and what to know now. |
| **Supporting Message Roles** | Caption/outcome labels subordinate to screenshot. |
| **Required Emotional Shift** | Continuation → operational trust. |
| **Required Merchant Belief** | سأرى ما يحدث بوضوح، ولن أضطر لتجميع القصة من عدة أدوات. |
| **Permitted Claim Depth** | Observed product behaviour / operational capability. |
| **Evidence Dependency** | **Must appear beside current real dashboard evidence**; copy must not overpower screenshot. |
| **Arabic Language Direction** | Outcome-based; merchant priority language. |
| **Preferred Sentence Shape** | Short outcome lines; avoid card-by-card inventory. |
| **CTA Role** | None. |
| **Transition Into Next** | Opens: what CartFlow learns beyond operations (LP-09 earns broader identity). |
| **Prohibited Messaging** | «كل شيء في مكان واحد» unless defined; «تحكم كامل»; «رؤية 360 درجة»; «لحظيًا» unless true; «دقة 100%»; fake KPIs. |
| **Copy Readiness** | Requires product evidence capture (current faces). |

**Foreshadow rule:** May sense “more than recovery tooling” via evidence — must **not** name category or complete broader-identity claim (LP-09 owns that).

---

### LP-09 — Knowledge Layer Discovery

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-09` |
| **Merchant State Before Reading** | Trusts CartFlow as a real operating surface. |
| **Merchant Question** | ماذا يتعلّم CartFlow مما لم أكن أراه؟ |
| **Message Objective** | Reveal broader identity **through evidence**: recovery activity can become store understanding; insufficient evidence must be stated. |
| **Single Core Message** | Repeated behaviour, recovery outcomes, movement, purchase, and hesitation evidence can form recurring-pattern understanding — or honestly say evidence is insufficient. |
| **Supporting Message Roles** | Pattern themes; confidence/insufficient/conflict states; labeled illustrative if needed. |
| **Required Emotional Shift** | Trust in ops → discovery of understanding. |
| **Required Merchant Belief** | CartFlow لا يعرض ما حدث فقط؛ بل يساعدني على فهم ما يتكرر ولماذا قد يكون مهمًا. |
| **Permitted Claim Depth** | Evidence-backed understanding (ceiling). |
| **Evidence Dependency** | Real knowledge cards preferred; illustrative **must be labeled**; no fabricated findings. |
| **Arabic Language Direction** | Merchant “فهم المتجر / الأنماط” — avoid internal “طبقة المعرفة” unless approved in Tone pack. |
| **Preferred Sentence Shape** | Pattern + evidence state; conditional modality. |
| **CTA Role** | None. |
| **Transition Into Next** | How this changes decisions. |
| **Prohibited Messaging** | “CartFlow knows your business”; always-knows-why; AI hidden opportunities; guaranteed recommendations; automatic growth engine; fabricated findings; fake confidence %; knowledge without evidence state; “Commerce Intelligence Platform” unless separately approved. |
| **Copy Readiness** | Requires Reality Validation + evidence capture; illustrative disclosure if used. |

**Permitted knowledge themes:** Recurring shipping hesitation; frequent add / rare purchase; WA return without completion; discount ineffectiveness in context; traffic vs conversion; insufficient / conflicting evidence; confidence; product/category patterns.

---

### LP-10 — Decision Value

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-10` |
| **Merchant State Before Reading** | Sees that CartFlow can form store understanding. |
| **Merchant Question** | كيف يساعدني هذا الفهم في إدارة المتجر؟ |
| **Message Objective** | Translate understanding into practical decision value. |
| **Single Core Message** | Helps identify where attention is needed, avoid weak assumptions, and decide from clearer evidence. |
| **Supporting Message Roles** | Permitted outcomes list (not feature list). |
| **Required Emotional Shift** | Discovery → practical confidence. |
| **Required Merchant Belief** | هذه المعرفة تساعدني على معرفة ما أراجع، وما أتوقف عن افتراضه. |
| **Permitted Claim Depth** | Decision support (not autonomous authority). |
| **Evidence Dependency** | Anchored to behaviours already shown; no new capability invention. |
| **Arabic Language Direction** | Operator language: مراجعة، انتباه، افتراض، قرار. |
| **Preferred Sentence Shape** | Outcome bullets; one outcome per line. |
| **CTA Role** | None. |
| **Transition Into Next** | Does value accumulate over time? |
| **Prohibited Messaging** | Runs your store; no expertise required; guaranteed growth/decision quality; autonomous action; advice as authority; unproven ROI numbers. |
| **Copy Readiness** | Partially ready — stay inside proven behaviours. |

**Permitted outcomes:** Know what needs attention; traffic vs conversion weakness; repeated hesitation; avoid ineffective actions; know when no conclusion is safe; prioritise right issue; more informed decisions.

---

### LP-11 — Continuous Value Journey

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-11` |
| **Merchant State Before Reading** | Accepts practical decision value. |
| **Merchant Question** | هل تزداد فائدة CartFlow مع الوقت؟ |
| **Message Objective** | Value can grow through continued real usage and accumulated evidence. |
| **Single Core Message** | Each observed journey can contribute evidence; accumulated evidence may create clearer understanding over time. |
| **Supporting Message Roles** | Continuity steps with conditional language. |
| **Required Emotional Shift** | Practical confidence → long-horizon trust. |
| **Required Merchant Belief** | قيمة CartFlow لا تنتهي عند استعادة سلة واحدة؛ الفائدة تتراكم عندما تتراكم الأدلة. |
| **Permitted Claim Depth** | Evidence-backed understanding (temporal / conditional). |
| **Evidence Dependency** | Conceptual continuity; no fake learning curves. |
| **Arabic Language Direction** | Prefer «مع الوقت»، «عندما تتكرر الإشارات»، «كلما توفر دليل كافٍ»، «قد تتضح أنماط». |
| **Preferred Sentence Shape** | Conditional progression lines. |
| **CTA Role** | None. |
| **Transition Into Next** | Can I trust what it tells me? |
| **Prohibited Messaging** | «يتعلم تلقائيًا»; «يصبح أذكى كل يوم»; «يعرف عملاءك»; evolving AI; guaranteed results over time. |
| **Copy Readiness** | Architecture ready with modality constraints. |

---

### LP-12 — Trust and Governance

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-12` |
| **Merchant State Before Reading** | Sees continuity value; may fear overclaim/AI guesswork. |
| **Merchant Question** | هل أستطيع الوثوق بما يقوله CartFlow؟ |
| **Message Objective** | Translate governance into merchant trust: no false certainty. |
| **Single Core Message** | CartFlow should not pretend certainty where evidence is weak. |
| **Supporting Message Roles** | Approved trust themes only. |
| **Required Emotional Shift** | Long-horizon interest → trust. |
| **Required Merchant Belief** | CartFlow لا يملأ الفراغ بالتخمين. |
| **Permitted Claim Depth** | Trust principle. |
| **Evidence Dependency** | Tied to real behaviours (purchase stop, insufficient evidence, isolation); legal/privacy claims need verification. |
| **Arabic Language Direction** | Plain merchant trust language — no audit/enterprise jargon. |
| **Preferred Sentence Shape** | Short principle statements. |
| **CTA Role** | None. |
| **Transition Into Next** | Practical fit: platforms. |
| **Prohibited Messaging** | Registry names; architecture; audit language; enterprise/military-grade; fake certifications; absolute privacy/security without legal verification. |
| **Copy Readiness** | Partially ready; privacy absolute claims → legal review. |

**Approved trust themes:** No recommendation without sufficient evidence; insufficient stated clearly; purchase stops unnecessary recovery; observation ≠ conclusion; merchant data isolated; product states shown honestly; claims bounded by evidence.

---

### LP-13 — Integration Readiness

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-13` |
| **Merchant State Before Reading** | Trust principles accepted; asks platform fit. |
| **Merchant Question** | هل يعمل مع منصة متجري؟ |
| **Message Objective** | Platform availability without ambiguity. |
| **Single Core Message** | CartFlow states what works now vs what is planned. |
| **Supporting Message Roles** | Readiness vocabulary rows. |
| **Required Emotional Shift** | Trust → practical clarity. |
| **Required Merchant Belief** | CartFlow يوضح ما يعمل الآن وما يزال ضمن الخطة. |
| **Permitted Claim Depth** | Commercial availability / integration claim (truth-bounded). |
| **Evidence Dependency** | **Requires integration readiness verification** immediately before final copy. |
| **Arabic Language Direction** | Status language: متاح الآن / قيد التحقق / مخطط له. |
| **Preferred Sentence Shape** | Platform + state; short caveats. |
| **CTA Role** | None (or soft pointer only if truthful). |
| **Transition Into Next** | Residual objections → FAQ. |
| **Prohibited Messaging** | «يدعم جميع المنصات»; «تكامل فوري»; «ثبته خلال دقائق»; logos without permission/readiness; hiding ops-gate; scaffold as live. |
| **Copy Readiness** | Requires integration readiness verification. |

**Baseline states (revalidate before final copy):**

```text
زد: مدعوم حاليًا، وقد يتطلب التفعيل تدخلًا تشغيليًا
سلة: مخطط له
Shopify: مخطط له
```

---

### LP-14 — FAQ

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-14` |
| **Merchant State Before Reading** | Mostly convinced; residual blockers remain. |
| **Merchant Question** | ما الذي ما زال يمنعني من البدء؟ |
| **Message Objective** | Architecture of high-value objection answers — **no final answers in this phase**. |
| **Single Core Message** | Remaining concerns have honest, bounded answers. |
| **Supporting Message Roles** | Question families only (see §3). |
| **Required Emotional Shift** | Residual doubt → resolved enough to act. |
| **Required Merchant Belief** | أسئلتي المهمة لها إجابات واضحة وصادقة. |
| **Permitted Claim Depth** | Per-answer ceiling from Claim Matrix; never invent readiness. |
| **Evidence Dependency** | Each category has source owner (see FAQ contracts). |
| **Arabic Language Direction** | Conversational Q; calm A later. |
| **Preferred Sentence Shape** | Short questions; answers later: short paragraphs. |
| **CTA Role** | None inside FAQ body. |
| **Transition Into Next** | Clears path to Final CTA. |
| **Prohibited Messaging** | Second feature dump; SEO stuffing; contradicting LP-13. |
| **Copy Readiness** | Categories ready; answers deferred to approved copy phase. |

---

### LP-15 — Final CTA

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-15` |
| **Merchant State Before Reading** | Story complete; objections addressed. |
| **Merchant Question** | ما الخطوة الآمنة التالية؟ |
| **Message Objective** | Invite a safe next step after understanding. |
| **Single Core Message** | One calm action matching current readiness. |
| **Supporting Message Roles** | Primary `/signup`; secondary `/login`; Demo deferred. |
| **Required Emotional Shift** | Trust → calm action. |
| **Required Merchant Belief** | البدء خطوة مناسبة وآمنة — بلا ضغط. |
| **Permitted Claim Depth** | Commercial availability of signup/login only. |
| **Evidence Dependency** | Destination paths must exist. |
| **Arabic Language Direction** | Calm verb; no urgency theatre (Tone pack). |
| **Preferred Sentence Shape** | One invitation line + button label. |
| **CTA Role** | Primary conversion owner for the page end. |
| **Transition Into Next** | Footer for verify/contact. |
| **Prohibited Messaging** | ابدأ النجاح الآن؛ لا تفوّت الفرصة؛ ضاعف مبيعاتك؛ استعد أرباحك فورًا؛ جرّب مجانًا قبل فوات الأوان؛ انضم لآلاف المتاجر؛ احجز مكانك؛ نتائج مضمونة. |
| **Copy Readiness** | Architecture ready; **final CTA wording unauthorised**. |

**Arabic CTA architecture (structure only):**

| Element | Rule |
|---------|------|
| Desired feeling | Safe, proportionate, respectful |
| Verb type | Begin / understand / start — not seize / don’t miss |
| Promise boundary | Access to product path — not guaranteed results |
| Destination truth | Primary → `/signup`; secondary → `/login` |
| Hierarchy | One primary; secondary visually quieter |
| Mobile | Primary dominant; secondary below |

**Deferred:** Book a Demo until real booking path exists.

---

### LP-16 — Footer

| Field | Definition |
|-------|------------|
| **Section ID** | `LP-16` |
| **Merchant State Before Reading** | Decided or still verifying. |
| **Merchant Question** | أين أتحقق أو أتواصل أو أتعلم المزيد؟ |
| **Message Objective** | Verification, contact, legal, essential navigation language. |
| **Single Core Message** | CartFlow is a real product you can contact and verify. |
| **Supporting Message Roles** | Product; login/signup; contact; privacy; terms; platform state if appropriate; company/legal identity where available. |
| **Required Emotional Shift** | Action residual → verifiable legitimacy. |
| **Required Merchant Belief** | أستطيع التحقق والتواصل دون قصة تسويقية جديدة. |
| **Permitted Claim Depth** | Commercial / legal availability only. |
| **Evidence Dependency** | Real links only; privacy/terms need legal verification if claimed. |
| **Arabic Language Direction** | Utility labels. |
| **Preferred Sentence Shape** | Labels / short links. |
| **CTA Role** | Utility links only — not a second hero CTA story. |
| **Transition Into Next** | None. |
| **Prohibited Messaging** | New product claims; second hero; feature repetition; fake office; fake support hours; non-existent social links. |
| **Copy Readiness** | Partially ready — legal pages must be real before claiming them. |

---

## 3. FAQ category contracts (no final answers)

| Category | Merchant concern | Answer objective | Permitted facts | Evidence/source required | Forbidden claim | Truth owner |
|----------|------------------|------------------|-----------------|--------------------------|-----------------|-------------|
| What is CartFlow? | Identity confusion | Frame recovery + understanding without category slogan | Aligned with Core Promise | Constitution + product surfaces | Commerce Intelligence Platform as brand claim | Product |
| Only abandoned-cart tool? | Narrow tool fear | Broader-than-recovery earned truth | LP-09 themes | Knowledge readiness | Always-on intelligence | Product |
| Replace current tools? | Switching risk | Clarify complement vs replace honestly | Current scope | Product scope | “Replaces everything” | Product |
| Widget & storefront speed | Performance fear | Honest speed stance | Measured impact only | Perf evidence | Claim speed-safe without verification | Engineering |
| WhatsApp activation | Activation friction | Requirements & gates | Real provider/ops steps | Ops readiness | Instant one-click if untrue | Ops / Product |
| After purchase | Spam fear | Stop/suppression truth | Purchase Truth behaviour | Purchase stop evidence | Continues messaging after purchase | Product |
| When recommendations? | Advice trust | Evidence threshold | Guidance/decision rules | Reality Validation | Always recommends | Product |
| Insufficient evidence meaning | Empty/weak states | Honesty ≠ broken | Insufficient-state UX | Product screens | Hidden uncertainty | Product |
| Supported platforms | Fit | Zid / planned others | Readiness table | Integration verify | All platforms | Product |
| Setup requires? | Complexity | Honest setup path | Ops-gated truths | Onboarding reality | “Minutes” if untrue | Ops |
| Self-service today? | Expectation | True self-serve level | Current onboarding | Ops | Full self-serve if false | Ops |
| Data separation | Privacy/trust | Isolation truth | Store isolation model | Engineering + Legal | Absolute privacy slogans | Legal / Eng |

---

## 4. Cross-section review

### 4.1 Message overlap

| Risk | Resolution |
|------|------------|
| Recovery mentioned in Hero, LP-04, LP-07 | Hero = problem+value; LP-04 = incompleteness of action-only; LP-07 = continuation proof — reinforcement allowed, not re-introduction of same claim |
| Understanding foreshadow vs LP-09 | Pre-LP-09 may foreshadow “see why / visibility”; **earned broader identity only at LP-09** |
| Trust in LP-09 insufficient vs LP-12 | LP-09 shows insufficient as knowledge behaviour; LP-12 owns trust principles narrative |

### 4.2 Premature disclosure

Compliant if LP-02…LP-08 avoid category labels and “platform that understands your business” as identity claim. LP-08 may operationally foreshadow; LP-09 completes earned realisation.

### 4.3 Feature drift

Blocked by: one core message per section; LP-05 outline-only; LP-08 no UI inventory; no components collage messaging.

### 4.4 Arabic naturalness

Governed by Tone pack: original Arabic direction, consistent merchant POV, preferred vocabulary, anti-translation patterns.

### 4.5 Evidence integrity

Capability claims gated in Claim Matrix; Knowledge/WhatsApp/Integrations/Speed require validation or capture.

### 4.6 Merchant relevance

Each section answers an IA merchant question mapped to Saudi/Gulf store concerns (shipping, WA, platforms, discounts, speed, trust).

### 4.7 Emotional continuity

Curiosity → Recognition → Reframe → Orientation → Proof → Discovery → Decision confidence → Continuity → Trust → Calm action.

### 4.8 CTA integrity

Primary `/signup`; Login secondary; Demo deferred; prohibited urgency phrases listed.

### 4.9 Mobile compression

Every section defines preferred sentence shape; Message Contracts define Desktop / Mobile / Microcopy depths with stable meaning.

### 4.10 Truthful uncertainty

LP-09, LP-11, LP-12, FAQ explicitly allow «لا توجد أدلة كافية بعد» as honesty — not product failure.

---

## 5. Decision table

| Section | Message Role Approved | Needs Rewrite Later | Needs Evidence | Needs Validation | Deferred Claim | Reason |
|---------|:---------------------:|:-------------------:|:--------------:|:----------------:|:--------------:|--------|
| LP-01 | ✓ | Labels only | | | Urgency/promo CTAs | Orientation only |
| LP-02 | ✓ | Final headline | Optional preview | | Category / AI / ROI | Problem-first |
| LP-03 | ✓ | Situation Arabic | Optional | | Fake stats / fear | Problem depth |
| LP-04 | ✓ | Contrast wording | | | Competitor attack | Calm reframe |
| LP-05 | ✓ | Step labels | | | Deep layer tours | Outline only |
| LP-06 | ✓ | Caption/copy | ✓ | | Mind-reading / all visitors | Beside widget |
| LP-07 | ✓ | Caption/copy | ✓ | Ops/provider | Guaranteed delivery / AI WA | Continuation |
| LP-08 | ✓ | Captions | ✓ current faces | | 360° / 100% accuracy | Outcome not inventory |
| LP-09 | ✓ | Pattern copy | ✓ | Reality Validation | Fabricated findings / CIP label | Earned identity |
| LP-10 | ✓ | Outcome lines | Anchors only | | Runs-your-store / ROI | Decision support |
| LP-11 | ✓ | Continuity lines | | | Auto-learning ML | Conditional language |
| LP-12 | ✓ | Principles | Behavioural | Legal for absolutes | Enterprise/military seals | Merchant trust |
| LP-13 | ✓ | Status rows | | Integration revalidate | All platforms / instant | Truthful readiness |
| LP-14 | ✓ categories | Final answers | Per category | Per category | Invented readiness | Architecture only |
| LP-15 | ✓ | Final CTA words | Path truth | | Book a Demo / hype CTAs | Calm signup |
| LP-16 | ✓ | Link labels | | Legal pages | Fake contact/social | Utility only |

---

## 6. Approval

Final Arabic landing copy, headlines, CTA labels, FAQ answers, and captions remain **unauthorised** until product and language approval after this pack.

See pack `README.md` STOP gate.
