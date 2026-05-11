/**
 * E2E: widget → reason POST → cart_abandoned → JSON contract for scheduling.
 * Complements tests/operational and k6 (browser timing + API semantics).
 */
import { test, expect } from "@playwright/test";

const DEMO_TEST_PHONE = "9665444555666";

test.describe("CartFlow lifecycle (widget → reason → cart-event)", () => {
  test("reason persistence then abandon returns recovery_scheduled contract", async ({
    page,
  }) => {
    await page.goto(
      `/demo/store?cf_test_phone=${encodeURIComponent(DEMO_TEST_PHONE)}`,
    );
    const introDismiss = page.locator("#cf-store-intro-dismiss");
    if (await introDismiss.isVisible({ timeout: 2500 }).catch(() => false)) {
      await introDismiss.click();
    }

    await expect
      .poll(
        async () =>
          await page.evaluate(
            () => window.CARTFLOW_RUNTIME_STATUS?.return_tracker_loaded === true,
          ),
        { timeout: 25_000 },
      )
      .toBe(true);

    await expect
      .poll(
        async () =>
          await page.evaluate(() => {
            return typeof (window as unknown as { cartflowDemoArmStoreWidget?: unknown })
              .cartflowDemoArmStoreWidget === "function";
          }),
        { timeout: 15_000 },
      )
      .toBe(true);

    await page.locator("#p-earbuds .add-btn").click();
    await expect(page.locator("#cart-list")).toContainText("TrueSound");

    await page.evaluate(() => {
      const arm = (
        window as unknown as { cartflowDemoArmStoreWidget?: () => void }
      ).cartflowDemoArmStoreWidget;
      if (typeof arm === "function") arm();
    });

    await page.waitForSelector("[data-cartflow-bubble], [data-cartflow-fab]", {
      timeout: 25_000,
    });
    const bubble = page.locator("[data-cartflow-bubble]");
    if (await bubble.count()) {
      await bubble.getByRole("button", { name: "نعم" }).click({ timeout: 15_000 });
    }

    const reasonPost = page.waitForResponse(
      (r) =>
        r.url().includes("/api/cart-recovery/reason") &&
        r.request().method() === "POST",
      { timeout: 20_000 },
    );
    const warrantyBtn = page.getByRole("button", { name: "الضمان" });
    if (!(await warrantyBtn.isVisible().catch(() => false))) {
      const fab = page.locator("[data-cartflow-fab]");
      if (await fab.isVisible().catch(() => false)) {
        await fab.click();
        await page
          .locator("[data-cartflow-bubble]")
          .getByRole("button", { name: "نعم" })
          .click({ timeout: 10_000 })
          .catch(() => {});
      }
    }
    await warrantyBtn.click({ timeout: 15_000 });
    const reasonResp = await reasonPost;
    expect(reasonResp.ok()).toBeTruthy();

    const cartEventRes = await page.evaluate(async (phone: string) => {
      const sid = sessionStorage.getItem("cartflow_recovery_session_id") || "";
      const w = window as unknown as {
        cart?: Array<{ name?: string; price?: number }>;
        CARTFLOW_STORE_SLUG?: string;
      };
      const cart = Array.isArray(w.cart) ? w.cart : [];
      const body: Record<string, unknown> = {
        event: "cart_abandoned",
        store: (w.CARTFLOW_STORE_SLUG || "demo").trim(),
        session_id: sid,
        cart_id: sid.slice(0, 220) + "_demo_cart",
        cart,
      };
      if (phone) body.cf_test_phone = phone;
      const r = await fetch("/api/cart-event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      return {
        ok: r.ok,
        status: r.status,
        json: j as Record<string, unknown>,
        ms: r.headers.get("x-response-time") || "",
      };
    }, DEMO_TEST_PHONE);

    expect(cartEventRes.ok, JSON.stringify(cartEventRes)).toBe(true);
    const j = cartEventRes.json;
    expect(j.ok).toBe(true);
    expect(j.event).toBe("cart_abandoned");
    expect(typeof j.recovery_scheduled).toBe("boolean");
    if (j.recovery_vip_manual === true) {
      expect(j.recovery_scheduled).toBe(false);
    }
  });
});
