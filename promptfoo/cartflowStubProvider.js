/**
 * Deterministic stub — mirrors rule-first cart copy (no LLM, no discounts).
 * @see https://promptfoo.dev/docs/providers/custom-api/
 */
class CartflowStubProvider {
  id() {
    return "cartflow-stub";
  }

  async callApi(prompt, context) {
    const v = context.vars || {};
    const name = String(v.product_name || "المنتج").trim();
    const val = Number(v.cart_value);
    const safeVal = Number.isFinite(val) ? val : 0;
    const out = `هلا 👋 لاحظنا إن «${name}» باقي في السلة (حوالي ${safeVal} ر.س.). ودّك تكمل الطلب؟`;
    return {
      output: out,
      tokenUsage: { total: 0, prompt: 0, completion: 0 },
    };
  }
}

module.exports = CartflowStubProvider;
