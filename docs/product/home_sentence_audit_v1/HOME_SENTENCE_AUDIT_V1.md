# Home Sentence Audit V1

**Status:** Audit only — awaiting disposition before Home Constitution V2  
**Date (UTC):** 2026-07-27  
**Law:** [`HOME_INFORMATION_BUDGET_V1.md`](../home_information_budget_v1/HOME_INFORMATION_BUDGET_V1.md) — especially **Executive Information Value Law**  
**Sources audited:** `static/home_executive_summary_v1.js`, `services/home_executive_summary_v1/compose_v1.py`, `services/decision_composition_engine_v1/merchant_publication_v1.py`, `services/decision_composition_engine_v1/merchant_understanding_v1.py`, Home hero/`pagePurpose` in `static/merchant_app.js` + `templates/merchant_app.html`  

**Scope:** Every merchant-visible **sentence** (and sentence-like status/count fragment) that Home can paint today when Executive Summary owns the surface. Not cards-as-objects. Not implementation.

**Legend (actions):** mark exactly one of Keep / Rewrite / Remove with `✓`.

---

## A. Shell & loading (visible on Home route)

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| A1 | ماذا يجب أن أعرف الآن عن متجري؟ (`#pagePurpose`) | YES | Frames the Home job; orients next attention | Home | ✓ | | |
| A2 | الرئيسية (nav / title chrome when applied) | NO | Navigation label only; does not change next action | Home (nav) | ✓ | | |
| A3 | نظرة عامة (sidebar) | NO | Nav label | Home (nav) | ✓ | | |
| A4 | مرحباً (loading shell greeting) | NO | Polite filler; no next move | — | | | ✓ |
| A5 | {store display name} e.g. متجرك / Living Store Review (loading shell) | NO | Identity; available from Account Identity panel | Settings / Identity | | | ✓ |
| A6 | {Arabic date header} (loading shell) | NO | Calendar context; not executive | — | | | ✓ |
| A7 | CartFlow يجهّز ملخص يومك… | NO | Loading chrome; discard when brief paints | — | | ✓ | |
| A8 | نجهز ملخص عملك اليوم… / equivalent pending copy (if shown) | NO | Same as A7 | — | | | ✓ |

**Note:** After HES paints, A4–A8 are replaced. They still fail Value Law while visible.

---

## B. HES header chrome

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| B1 | ملخص تنفيذي (`eyebrow_ar`) | NO | Category label; duplicates A1 / B2 | Home | | | ✓ |
| B2 | ماذا يجب أن تعرف الآن؟ (`title_ar`) | YES* | Same job as A1; *duplicate executive framing* | Home | | ✓ | |
| B3 | ملخص سريع فقط — التفاصيل في صفحاتها. (`lede_ar`) | NO | Meta-instruction about the UI; does not change store action | Home | | | ✓ |
| B4 | تعذّر تحميل الملخص — أعد المحاولة. (error lede) | YES | Changes behaviour → retry | Home | ✓ | | |
| B5 | الرئيسية تقدّم ما يهم أولاً · مساحة القرار تشرح القرار · المنتجات والسلال والتواصل للتفاصيل التشغيلية. (footer) | NO | Ownership essay; teaching the IA, not directing a move | — (docs/IA) | | | ✓ |

**Duplicate law:** A1 and B2 produce the **same** executive behaviour. Keep **one** (prefer A1 constitutional question). Rewrite or remove B2.

---

## C. Section titles (always painted per section)

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| C1 | حالة المتجر | NO | Label only | Home | ✓ | | |
| C2 | أهم قرار اليوم | NO | Label only — value is in the summary | Home | ✓ | | |
| C3 | أهم منتج يستحق الانتباه | YES* | Weak: already asserts “needs attention”; summary must carry the subject | Products → Workspace | | ✓ | |
| C4 | ملاحظات المنتجات (legacy observations title) | NO | Internal/legacy framing; “ملاحظات” ≠ executive move | Products / Workspace | | ✓ | |
| C5 | السلال | NO | Label only | Carts | ✓ | | |
| C6 | التواصل | NO | Label only | Communication | ✓ | | |

\*Titles may remain as structure if summaries carry Value Law; C3/C4 should not restate diagnosis without a product subject.

---

## D. Status chips (`status_ar`) — sentence-like fragments

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| D1 | مستقر | YES | Authorizes calm (not intervening) | Home | ✓ | | |
| D2 | هادئ | YES | Same as D1 (duplicate family) | Home | | ✓ | |
| D3 | يتطلب متابعة | YES | Signals act now | Home | ✓ | | |
| D4 | يحتاج انتباهك | YES | Same family as D3 — pick one vocabulary | Home | | ✓ | |
| D5 | يحتاج تدخلاً عاجلاً | YES | Urgency changes next move | Home | ✓ | | |
| D6 | مستقر مع فرصة تستحق الانتباه | YES | Calm + pursue opportunity | Home | ✓ | | |
| D7 | أدلة غير كافية | YES | Changes behaviour → do not force a false decision | Home / Workspace | ✓ | | |
| D8 | القرار الأهم | NO | Restates section title; no new move | Home | | | ✓ |
| D9 | منتج | NO | Category tag | Products | | | ✓ |
| D10 | يتطلب انتباهاً (observations) | YES* | Vague without subject | Products | | ✓ | |
| D11 | لا مهام | YES | Authorizes calm on that domain | Home | ✓ | | |
| D12 | نشط | NO | Ambiguous activity; not a next move | Carts | | ✓ | |
| D13 | بانتظار متابعة | YES | Points to follow-up | Communication | ✓ | | |
| D14 | مكتمل اليوم | NO | Reporting completion; rarely changes next move | Communication | | | ✓ |
| D15 | يحتاج ضبطاً | YES | Directs Settings/WhatsApp path | Communication / Settings | ✓ | | |

**Duplicate law:** D1/D2 and D3/D4 — keep one calm term and one attention term.

---

## E. Store Health summaries (`health.summary_ar` templates)

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| E1 | جاهزية المتجر غير مكتملة — اضبط الربط أولاً. | YES | Directs setup/connect | Settings | ✓ | | |
| E2 | المتجر يحتاج تدخلاً عاجلاً — متابعة العملاء مقيدة بسبب نقص معلومات التواصل. | YES | Unblock contact / Communication→Carts | Home → Communication | ✓ | | |
| E3 | المتجر مستقر، لكن انخفاض التحويل في {product} يستحق انتباهك. | YES | Directs product attention | Products / Workspace | ✓ | | |
| E4 | المتجر مستقر، لكن توجد فرصة تجارية تستحق انتباهك في {product}. | YES | Same family as E3 | Products / Workspace | | ✓ | |
| E5 | المتجر مستقر، لكن توجد {n} فرص تجارية تستحق انتباهك. | YES* | Opportunity yes; bare **{n}** risks count-first framing | Products | | ✓ | |
| E6 | المتجر يحتاج انتباهك اليوم. | YES | Generic act-now | Workspace | ✓ | | |
| E7 | المتجر مستقر. | YES | Authorizes calm | Home | ✓ | | |
| E8 | لا توجد أدلة كافية لتقييم حالة المتجر اليوم. | YES | Stop false certainty | Home | ✓ | | |
| E9 | لا توجد مشكلات تجارية حرجة ظاهرة. | YES | Authorizes calm | Home | ✓ | | |
| E10 | فرص استعادة المبيعات محدودة اليوم. | YES | Changes recovery priority | Workspace / Carts | ✓ | | |
| E11 | نشاط المتجر مستقر. | YES | Calm (duplicate of E7 family) | Home | | ✓ | |

---

## F. Today’s Top Decision summaries

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| F1 | {primary_action} e.g. راجع مسار التحويل لـ Raven — حزام جلد للساعة. | YES | Names the move + subject | Workspace | ✓ | | |
| F2 | راجع تجربة إتمام الشراء ومتابعة العملاء. | YES | Directs checkout/recovery review | Workspace | ✓ | | |
| F3 | راجع آلية جمع رقم العميل قبل مغادرة المتجر. | YES | Directs contact capture | Workspace / Communication | ✓ | | |
| F4 | راجع حالات الشراء التي تحتاج تدخلك. | YES | Directs ops review | Workspace | ✓ | | |
| F5 | لا توجد أولوية قرار واضحة اليوم. | YES | Authorizes no forced decision | Home | ✓ | | |
| F6 | راجع أدلة الطلب لـ {product}. | YES* | “أدلة” edges into Workspace evidence language | Workspace | | ✓ | |

---

## G. Product / situations / observations sentences

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| G1 | {title_ar} on situation card (product/situation title) | YES | Names subject of attention | Products / Workspace | ✓ | | |
| G2 | {statement_ar} on situation card | YES if action-bearing; NO if raw observation | Must pass Value Law | Products / Workspace | | ✓ | |
| G3 | المنتج {name}: {statement} | YES if statement changes next move | Subject + signal | Products | ✓ | | |
| G4 | المنتج {name} يستحق الانتباه. | YES | Directs Products/Workspace | Products | ✓ | | |
| G5 | لا يوجد منتج حالياً بأدلة كافية لملاحظة تجارية. | YES* | “أدلة” / “ملاحظة” is analytic; calm-empty can be shorter | Products | | ✓ | |
| G6 | اهتمام العملاء بالمنتجات يتزايد. | NO* | Trend reporting unless tied to a named next move | Products | | ✓ | |
| G7 | يبدو أن الشحن يضعف إتمام الشراء. | YES | Directs shipping/checkout attention | Products / Workspace | ✓ | | |
| G8 | إتمام الشراء أبطأ من المعتاد. | YES | Directs checkout review | Workspace | ✓ | | |
| G9 | طلب واضح على {product} — راجع جودة الأدلة قبل التوسع. | NO on Home | “جودة الأدلة” is Workspace evidence | Workspace | | | ✓ |

---

## H. Carts summaries & notes

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| H1 | {n} سلة تحتاج متابعة تشغيلية. | NO* | Count-first; matches forbidden “172 carts” pattern unless rewritten without bare inventory | Carts | | ✓ | |
| H2 | سلتان تحتاجان متابعة تشغيلية. | NO* | Same as H1 | Carts | | ✓ | |
| H3 | سلال العملاء تحتاج متابعة نشطة. | YES | Behaviour → open Carts / act | Carts | ✓ | | |
| H4 | تقدّم سلال العملاء مستقر. | YES | Authorizes calm | Carts | ✓ | | |
| H5 | لا توجد سلال تحتاج متابعة فردية حالياً. | YES | Calm | Carts | ✓ | | |
| H6 | متابعة بعض العملاء مقيدة حالياً. | YES | Unblock path | Communication / Carts | ✓ | | |
| H7 | لا يحتاج إجراءً فردياً الآن. (`cart_level_action_ar`) | YES | Authorizes no per-cart chase | Carts | ✓ | | |
| H8 | Visible numeric **count badge** (e.g. `185`) beside Carts | NO | Bare count; Value Law forbids | Carts | | | ✓ |

---

## I. Communication summaries

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| I1 | متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل. | YES | Unblock → affected customers / WhatsApp | Communication | ✓ | | |
| I2 | تواصل العملاء يسير بشكل طبيعي. | YES | Authorizes calm | Communication | ✓ | | |
| I3 | تواصل العملاء يحتاج انتباهاً. | YES | Act on Communication | Communication | ✓ | | |
| I4 | {n} عملاء بانتظار متابعة. | NO | Headcount without path (“8 customers”) | Communication | | | ✓ |
| I5 | {sent} رسالة وصلت للعملاء اليوم. | NO | Delivery reporting | Communication | | | ✓ |
| I6 | تواصل العملاء يحتاج ضبطاً بسيطاً. | YES | Directs WhatsApp/settings | Communication / Settings | ✓ | | |
| I7 | Communication numeric **count badge** | NO | Bare count | Communication | | | ✓ |

---

## J. CTAs (“عرض التفاصيل”)

| # | Current sentence | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|------------------|--------------------|------|-------|------|---------|--------|
| J1 | عرض التفاصيل ← (per card, up to 5) | YES | Navigation to constitutional owner — required by budget | Owner page | ✓ | | |
| J2 | عرض التفاصيل ← (situation item, duplicates section CTA) | YES* | Same behaviour as J1 for same owner — **duplicate** | Workspace | | | ✓ |

**Duplicate law:** One View Details per card; situation-item CTA + section CTA for the same destination → keep one.

---

## K. Health View Details mis-ownership (sentence destination)

| # | Current sentence + href | Behaviour changed? | Why? | Owner | Keep | Rewrite | Remove |
|---|-------------------------|--------------------|------|-------|------|---------|--------|
| K1 | عرض التفاصيل on Health → `#carts` (default) | YES* | Often wrong owner when health is decision/comms-led | Workspace or Communication as appropriate | | ✓ | |
| K2 | عرض التفاصيل on Health → `#home-setup` when disconnected | YES | Correct Settings path (prefer `#settings` setup) | Settings | | ✓ | |

---

## Audit rollup

### Must Remove (fail Value Law or duplicate)

| IDs | Reason |
|-----|--------|
| A4, A5, A6, A8 | Loading identity/date filler |
| B1, B3, B5 | Meta chrome / IA essay |
| D8, D9, D14 | Non-executive status tags / reporting |
| G9 | Evidence language on Home |
| H8, I4, I5, I7 | Bare counts / delivery reporting |
| J2 | Duplicate View Details |

### Must Rewrite (keep slot; change wording or ownership)

| IDs | Direction |
|-----|-----------|
| A7 | Minimal busy state or none |
| B2 | Drop or merge with A1 (single Home question) |
| C3, C4, D2, D4, D10, D12 | Vocabulary / non-vague status |
| E4, E5, E11 | One opportunity pattern; avoid count-first |
| F6 | Drop “أدلة” → action language |
| G2, G5, G6 | Value-Law pass; no raw observation |
| H1, H2 | Executive cart line without bare inventory count |
| K1, K2 | Owner-correct href |

### Keep (pass Value Law as executive briefing)

| IDs |
|-----|
| A1–A3 (nav), B4, C1–C2, C5–C6, D1/D3/D5–D7/D11/D13/D15 (after vocabulary collapse), E1–E3, E6–E10, F1–F5, G1/G3/G4/G7/G8, H3–H7, I1–I3, I6, J1 |

---

## Sentence budget vs Information Budget V1

| Budget rule | Audit finding |
|-------------|----------------|
| Every sentence needs executive value | Many chrome/status/count sentences fail |
| ≤5 View Details | OK if J2 removed |
| No bare counts | H1/H2/H8/I4/I5/I7 violate |
| One primary decision | F* summaries OK; D8 “القرار الأهم” redundant |
| Duplicate behaviour → one sentence | A1↔B2; D1↔D2; D3↔D4; J1↔J2 |

---

## STOP

- Deliverable is **only** this audit.  
- **No** implementation, redesign, or UI changes.  
- **No** Home Constitution V2 until this audit’s Keep / Rewrite / Remove dispositions are approved.

---

*End of Home Sentence Audit V1*
