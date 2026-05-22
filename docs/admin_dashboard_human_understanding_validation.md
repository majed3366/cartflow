# Admin Dashboard v2 — Human Understanding Validation Report

**Date (UTC):** 2026-05-19  
**Scope:** Presentation / UX verification only — no code, API, or runtime changes.  
**Method:** Template review + authenticated HTML render checks (`TestClient`, default dev control payload).  
**Pages reviewed:** `/admin/operations`, `/admin/operational-health`, `/admin/control` (placeholder), sidebar navigation, responsive layout markers.

---

## Executive summary (5-second questions)

| Question | Where answered today | Verdict |
|----------|----------------------|---------|
| 1. هل النظام بخير؟ | مركز التشغيل — hero headline + «هل النظام سليم؟» | **PASS** |
| 2. هل يوجد خطر؟ | Hero «أثر العملاء» + «خطر العملاء» + لون/إيموجي الحالة | **PASS** |
| 3. من المتأثر؟ | Hero (عملاء) + قرارات سريعة (متاجر)؛ التفصيل عند 🔴 | **PASS** (جزئي عند 🟢/🟡) |
| 4. ماذا أفعل؟ | Hero «الإجراء» + شريط «الإجراء المطلوب» | **PASS** |
| 5. أين أذهب؟ | الشريط الجانبي (أقسام مجمّعة) | **PASS** |

**Overall:** Dashboard v2 reads as a **product operations console**, not a raw debug dump, for the primary path (**مركز التشغيل**). **لوحة عامة** is understandable but denser than ideal for a non-technical reader in under 10 seconds.

---

## A — لوحة عامة (`/admin/operations`)

**PASS** (with minor confusion)

**Reason:** Within the first screenful, a reader sees **ملخص سريع** (bullet narrative), then **١ — حالة المنصة** with interpretation text, **أولوية** badge, and pills for **تصنيف المنصة** and **ثقة التشغيل**. Store count appears in **متاجر في القاعدة**; production vs trial appears via **وضع Sandbox** and platform category labels. Stability/follow-up is signaled through priority and trust/degradation pills without opening technical sections.

**Confusion points:**

- Many metric cards (8+) and labels like **المسح للثقة**, **بعوائق إعداد**, **تقدير تغطية أرقام** assume operational vocabulary.
- Numbered sections **١ / ٢ / ٣** feel more “internal playbook” than consumer SaaS.
- No single hero verdict equivalent to مركز التشغيل — reader must synthesize from several blocks.

**Suggested improvement (docs only; no implementation in this task):**

- Add one top **platform status sentence** (🟢/🟡/🔴) mirroring مركز التشغيل hero style.
- Reduce visible metrics above the fold to 3–4 with “عرض التفاصيل” for the rest.

---

## B — مركز التشغيل (`/admin/operational-health`)

**PASS**

**Reason:** Support can follow **مشكلة → أثر → إجراء → تحقق** without reading logs:

1. **Level 1 hero** — large status (e.g. **يُفضّل المراقبة**), **الوضع الحالي**, **الإجراء**, **أثر العملاء** in dedicated metric tiles.
2. **Level 2 — قرارات سريعة** — explicit **هل يلزم إجراء؟** answer in the section header area.
3. **Level 3 — قرارات حسب المكوّن** — each card uses Arabic row labels: المشكلة، الأثر، المتاجر/العملاء، الإلحاح، الإجراء المقترح، كيف نتحقق.
4. **Level 4** — technical lines collapsed under «تفاصيل للدعم».

Rendered checks confirmed: `#operational-verdict`, `.admin-hero`, `admin-level-tag`, and component card field labels present.

**Confusion points:**

- Tags **المستوى ١ / ٢ / ٣ / ٤** help engineers more than support leads; some readers may ignore them.
- Per-component cards still show ~7 rows — readable as **decisions**, but skimming many cards takes >30 seconds.
- **أثر المتاجر** may show **لا** while a card still lists **~3 عميل** (presentation estimates per component) — requires knowing cards are per-system, not only the hero.

**Suggested improvement:**

- Rename levels to plain Arabic for support: **الآن / ماذا تفعل / التفاصيل / للدعم التقني** (labels only).
- One-line hint under hero: «البطاقات أدناه = تفصيل كل جزء من النظام».

---

## C — التحكم التشغيلي (`/admin/control` — placeholder)

**PASS** (expectations documented only — page is **قيد التطوير**)

**Reason:** Placeholder correctly sets expectation that **no actions exist yet**. Sidebar description in routes copy references future: إيقاف/تشغيل آمن، فحص يدوي، وضع آمن، إعادة محاولة.

**User expectations (when implemented):**

| Expected capability | Why users would expect it here |
|--------------------|--------------------------------|
| **تشغيل / إيقاف آمن** | Name «التحكم التشغيلي» implies control plane, not read-only status |
| **إعادة فحص / فحص يدوي** | Distinct from مركز التشغيل (observation) — active diagnostics trigger |
| **إعادة محاولة** | Recovery operations after incident |
| **Kill switch / وضع آمن** | Emergency stop for customer impact |
| **تأكيد قبل تنفيذ** | Any destructive action should require explicit confirm |

**Confusion points:**

- Today, clicking **التحكم التشغيلي** after **مركز التشغيل** may feel like “empty second ops page” unless placeholder copy stresses **إجراءات قادمة — المراقبة من مركز التشغيل الآن**.

**Suggested improvement:**

- Placeholder bullet list of **future actions** (no buttons) to align mental model before build.

---

## D — Navigation clarity

**PARTIAL PASS**

**Reason:** Sidebar groups create clear domains:

| Item | Obvious purpose |
|------|-----------------|
| **لوحة عامة** | Platform-wide summary, stores, trust, sandbox counts |
| **مركز التشغيل** | Live health verdict + component decisions |
| **التحكم التشغيلي** | Future runbook actions (placeholder) |
| **المتاجر / الاشتراكات / التقارير** | Domain modules (mostly placeholders) |
| **النظام والدعم** | Logs/technical (placeholders) |

Pages are **not** duplicate implementations of the same data.

**Confusion points:**

- **مركز التشغيل** vs **التحكم التشغيلي** — similar Arabic roots; non-Arabic-native admins may conflate.
- **صحة النظام** (under النظام والدعم) vs **مركز التشغيل** — may sound like the same thing until placeholders clarify split (read vs act).
- **لوحة عامة** vs **مركز التشغيل** — both “operations”; first visit may not know which to open first.

**Suggested improvement:**

- Sidebar subtitles (one line): e.g. مركز التشغيل = «هل نحن بخير؟»، التحكم = «ماذا ننفّذ؟»، لوحة عامة = «ملخص المنصة».

---

## E — Mobile usability

**PASS** (with scrolling caveats)

**Reason:** Layout includes `admin-sidebar-toggle`, off-canvas `left-0` drawer, `lg:pl-[17.5rem]` content offset, responsive hero grid (`sm:grid-cols-2`, `xl:grid-cols-4`), and `admin-nav-active` high-contrast state. Hierarchy remains: hero → quick decisions → collapsible details.

**Confusion points:**

- Long vertical stack on مركز التشغيل — hero + level 2 + many cards; **5-second clarity** still works for hero only; full page needs scroll.
- `admin-level-tag` chips wrap on narrow widths — acceptable but adds noise.
- Placeholder pages centered narrow (`max-w-2xl`) — fine.

**Suggested improvement:**

- Sticky sub-header on mobile showing only verdict emoji + label while scrolling component cards.

---

## Product vs debug page (مركز التشغيل)

| Criterion | Assessment |
|-----------|------------|
| Feels like a **product**? | **Yes** — hero status card, color tiers, grouped nav, collapsed technical |
| Feels like a **debug page**? | **Partially** only inside Level 4 / monospace technical lists |

**Verdict for `/admin/operational-health`:** **Product** for Levels 1–2; **support/debug** acceptable at Level 4 by design.

---

## Verification checklist (automated smoke)

| Check | Result |
|-------|--------|
| No files outside `docs/` modified for this task | Intended |
| `#operational-verdict` present | Yes |
| `.admin-hero` present | Yes |
| Placeholder «قيد التطوير» on `/admin/control` | Yes |
| Merchant `/dashboard` excludes `CartFlow Admin` | Yes (existing test suite) |

---

## Sign-off

| Section | Result |
|---------|--------|
| A — لوحة عامة | **PASS** (minor jargon density) |
| B — مركز التشغيل | **PASS** |
| C — التحكم التشغيلي | **PASS** (expectations only) |
| D — Navigation | **PARTIAL PASS** |
| E — Mobile | **PASS** (scroll depth) |

**Recommendation:** Ship v2 for **مركز التشغيل** as the primary human-facing ops surface. Schedule a small **copy-only** follow-up for لوحة عامة hero + sidebar one-line hints (no backend work).

---

*Report generated as part of CartFlow Admin Dashboard v2 human understanding validation. Commit: `docs: admin dashboard human understanding validation report`.*
