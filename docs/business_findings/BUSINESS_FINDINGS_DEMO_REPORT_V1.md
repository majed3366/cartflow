# Business Findings Demo Report V1

**Store:** `demo`  
**Generated:** 2026-07-17T23:17:05+00:00  
**Engine:** business_findings_engine_v1  
**Evidence:** demo_rich_fixture_v1  

## Findings

### 1. نقص بيانات التواصل يعيق استرجاع جزء مهم من السلال

- **Family:** `contact_blocker` / `missing_contact_blocks_recovery_v1`
- **Summary:** يوجد حالياً 43 سلة لا يمكن بدء استرجاعها لأن وسيلة التواصل غير متوفرة.
- **Commercial meaning:** كل سلة بلا تواصل صالح تبقى خارج مسار واتساب، فيتأجل استرجاع الإيراد.
- **Evidence:** 43 سلة نشطة بلا رقم صالح من أصل 60.
- **Confidence:** high (0.95)
- **Recommendation:** `act_now` — حسّن التقاط رقم العميل قبل مغادرة المتجر، وراجع السلال المحظورة.
- **Status:** `confirmed`
- **Authoritative surface:** `carts`
- **Sample size:** 43

### 2. منتج X يجذب اهتماماً مرتفعاً لكن نادراً ما يصل إلى الشراء

- **Family:** `product_conversion` / `high_interest_low_purchase_product_v1`
- **Summary:** أُضيف منتج X إلى السلة 34 مرة عبر 22 سلة، بينما اكتمل الشراء 2 مرة فقط (6%).
- **Commercial meaning:** الاهتمام موجود، لكن مسار الشراء يتعثّر قبل الإتمام — الفرصة التجارية معلّقة.
- **Evidence:** add_to_cart=34 unique_carts=22 purchases=2 store_baseline=16%
- **Confidence:** high (0.89)
- **Recommendation:** `test` — اختبر مراجعة السعر أو وضوح العرض أو تفاصيل المنتج — دون الجزم بسبب واحد.
- **Status:** `confirmed`
- **Authoritative surface:** `products`
- **Sample size:** 34

### 3. تكلفة الشحن هو أبرز سبب للتردّد حالياً ضمن مجموعة منتجات مرتبطة بهذا السبب

- **Family:** `hesitation` / `dominant_hesitation_reason_v1`
- **Summary:** تكلفة الشحن يتكرر في 16 من أصل 28 سبب مسجّل (57%) — وهو الأعلى بوضوح أمام بقية الأسباب.
- **Commercial meaning:** هذا النمط يشير إلى عائق شراء متكرر يؤثر على جزء كبير من السلال المترددة.
- **Evidence:** distribution={'shipping': 16, 'price': 7, 'thinking': 3, 'delivery_time': 2}; top=shipping:16; compared_against=['delivery_time', 'price', 'shipping', 'thinking']
- **Confidence:** high (0.83)
- **Recommendation:** `investigate` — راجع وضوح التكلفة/العرض المرتبط بهذا السبب، واختبر تحسيناً واحداً وقِس الأثر.
- **Status:** `confirmed`
- **Authoritative surface:** `knowledge_layer`
- **Sample size:** 28

### 4. واتساب يُعيد العملاء، لكن إتمام الشراء ما زال ضعيفاً

- **Family:** `channel_whatsapp` / `recovery_channel_effectiveness_v1`
- **Summary:** عادات العودة واضحة (18/32) بينما الشراء (3) ما زال منخفضاً نسبياً.
- **Commercial meaning:** القناة تُحرّك العودة، بينما قيمة الإيراد تتحقق عند إغلاق الشراء بعد العودة.
- **Evidence:** sent=32 returned=18 purchased=3 failed=2 suppressed=1
- **Confidence:** high (0.87)
- **Recommendation:** `investigate` — حافظ على القناة إن كانت تُعيد الاهتمام، وركّز التحسين على ما بعد العودة.
- **Status:** `confirmed`
- **Authoritative surface:** `whatsapp`
- **Sample size:** 32

### 5. تردّد «تكلفة الشحن» يبقى غالباً بلا حل حتى بعد التواصل

- **Family:** `hesitation_resolution` / `hesitation_resolution_effectiveness_v1`
- **Summary:** حالات غير محلولة ≈ 9 مع مشتريات=1 بعد العودة=10.
- **Commercial meaning:** التواصل وحده لا يُزيل هذا العائق — يلزم اختبار عرض أو سياسة مرتبطة به.
- **Evidence:** reason=shipping unresolved=9 returned=10 purchased=1
- **Confidence:** medium (0.6)
- **Recommendation:** `test` — اختبر تحسيناً واحداً مرتبطاً بهذا السبب وقِس الشراء بعد العودة.
- **Status:** `confirmed`
- **Authoritative surface:** `knowledge_layer`
- **Sample size:** 19

### 6. العملاء يعودون بعد التواصل لكن أغلبهم لا يُكمل الشراء

- **Family:** `return_outcome` / `return_without_purchase_v1`
- **Summary:** من أصل 22 عودة مسجّلة، غادر 16 دون شراء (73%) واكتمل الشراء في 6 فقط.
- **Commercial meaning:** الاسترجاع يُعيد الاهتمام، لكن عائق الشراء ما زال قائماً بعد العودة.
- **Evidence:** returns=22 without_purchase=16 with_purchase=6 wa_sent=32
- **Confidence:** high (0.77)
- **Recommendation:** `investigate` — افحص سبب التردد بعد العودة، واختبر تحسين العرض أو المتابعة — دون ادعاء سبب نهائي.
- **Status:** `confirmed`
- **Authoritative surface:** `customers`
- **Sample size:** 22

### 7. منتج X يجذب اهتماماً متكرراً عبر زيارات متعددة دون شراء

- **Family:** `repeated_interest` / `repeated_interest_v1`
- **Summary:** ظَهرت إعادة إضافة (11) وإشارات عودة (8) حول منتج X، بينما المشتريات = 2 فقط.
- **Commercial meaning:** اهتمام متكرر غير محسوم غالباً يعني فرصة ضائعة أكثر من ضعف اهتمام.
- **Evidence:** repeat_adds=11 revisits=8 add_to_cart=34 purchases=2
- **Confidence:** medium (0.6)
- **Recommendation:** `test` — اختبر عرضاً أو تذكيراً موجّهاً لهذا المنتج بعد العودة.
- **Status:** `emerging`
- **Authoritative surface:** `products`
- **Sample size:** 34

### 8. العودة بعد واتساب متكررة والشراء ضعيف — يستحق اختبار الرسالة أو التوقيت

- **Family:** `channel_whatsapp_test` / `whatsapp_message_timing_test_v1`
- **Summary:** بعد 32 رسالة عاد 18 عميل تقريباً، لكن الشراء اكتمل 3 مرة فقط.
- **Commercial meaning:** الدليل يبرر اختبار صياغة أو وقت إرسال مختلف — دون الجزم بأن الصياغة الحالية هي السبب.
- **Evidence:** sent=32 returned=18 purchased=3 failed=2 failed_share=6%
- **Confidence:** medium (0.62)
- **Recommendation:** `test` — اختبر رسالة أو وقت إرسال واحد، وقارن العودة والشراء.
- **Status:** `emerging`
- **Authoritative surface:** `whatsapp`
- **Sample size:** 32

### 9. منتج C يحصل على اهتمام أضعف بكثير من منتجات مشابهة

- **Family:** `product_interest` / `low_product_interest_v1`
- **Summary:** أُضيف منتج C 2 مرة فقط، بينما منتجات مقارنة تتجاوز حوالي 18 إضافة.
- **Commercial meaning:** ضعف الاهتمام يقلّل فرص التحويل حتى قبل مرحلة التردد أو الاسترجاع.
- **Evidence:** product_atc=2 peer_median_atc=18
- **Confidence:** medium (0.55)
- **Recommendation:** `test` — اختبر الصور أو طريقة العرض أو السعر أو مصدر الزيارة — كتوصيات اختبار لا كأسباب مؤكدة.
- **Status:** `emerging`
- **Authoritative surface:** `products`
- **Sample size:** 20

### 10. من يذكرون «وقت التوصيل» كثيراً ما يعودون ويُكملون الشراء

- **Family:** `hesitation_resolution` / `hesitation_resolution_effectiveness_v1`
- **Summary:** بعد العودة (2) اكتمل الشراء 2 مرة لهذا السبب — نسبة حل أعلى من غيره.
- **Commercial meaning:** هذا السبب قابل للحل نسبياً بعد التواصل أو العودة.
- **Evidence:** reason=delivery_time returned=2 purchased=2
- **Confidence:** medium (0.58)
- **Recommendation:** `monitor` — حافظ على مسار المتابعة لهذا السبب ووثّق ما ينجح.
- **Status:** `confirmed`
- **Authoritative surface:** `knowledge_layer`
- **Sample size:** 2

### 11. لا يمكن بعد التمييز بين ضعف الزيارات وضعف التحويل

- **Family:** `traffic_conversion` / `traffic_versus_conversion_v1`
- **Summary:** بيانات زيارات المتجر الموثوقة غير متاحة حالياً، ولا يصح استنتاج حجم الزيارات من عدد السلال وحدها.
- **Commercial meaning:** أي توصية إعلانية أو مرورية الآن ستكون افتراضاً لا دليلاً.
- **Evidence:** visitor_total=unavailable; carts_not_used_as_traffic_proxy
- **Confidence:** insufficient (0.0)
- **Recommendation:** `insufficient_evidence` — اربط مصدر زيارات موثوقاً قبل الحكم على الزيارات مقابل التحويل.
- **Status:** `insufficient_evidence`
- **Authoritative surface:** `knowledge_layer`
- **Sample size:** 60

## Home candidates (consume later — no Home redesign)

- **most_important_finding:** نقص بيانات التواصل يعيق استرجاع جزء مهم من السلال
- **strongest_opportunity:** منتج X يجذب اهتماماً مرتفعاً لكن نادراً ما يصل إلى الشراء
- **highest_value_action:** نقص بيانات التواصل يعيق استرجاع جزء مهم من السلال
- **new_understanding:** تكلفة الشحن هو أبرز سبب للتردّد حالياً ضمن مجموعة منتجات مرتبطة بهذا السبب

## Observability (internal)

- produced: 11
- suppressed: 1
- deduplicated: 1
- insufficient: 1
- conflicting: 0
- families: contact_blocker, product_conversion, hesitation, channel_whatsapp, hesitation_resolution, return_outcome, repeated_interest, channel_whatsapp_test, product_interest, traffic_conversion
- gaps: visitor_truth_unavailable, product_views_unavailable, widget_shown_metrics_unavailable
