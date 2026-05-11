/**
 * Browser regression: layer-D «السعر مرتفع» must POST /api/cart-recovery/reason
 * and mount the price follow-up UI (no uncaught page errors).
 */
import { test, expect } from "@playwright/test";

const DEMO_TEST_PHONE = "9665444555666";

test.describe("Widget reason — السعر مرتفع regression", () => {
  test("click advances flow and posts cart-recovery reason", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => {
      pageErrors.push(String(e.message || e));
    });

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
            () =>
              (window as unknown as { CARTFLOW_RUNTIME_STATUS?: { return_tracker_loaded?: boolean } })
                .CARTFLOW_RUNTIME_STATUS?.return_tracker_loaded === true,
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

    await expect(page.locator("#cart-list")).toBeVisible();
    await page.locator("#p-earbuds .add-btn").click();
    await expect(page.locator("#cart-list")).toContainText("TrueSound");

    await page.evaluate(() => {
      const arm = (
        window as unknown as { cartflowDemoArmStoreWidget?: () => void }
      ).cartflowDemoArmStoreWidget;
      if (typeof arm === "function") {
        arm();
      }
    });

    const bubbleOrFab = "[data-cartflow-bubble], [data-cartflow-fab]";
    await page.waitForSelector(bubbleOrFab, { timeout: 25_000 });

    const bubble = page.locator("[data-cartflow-bubble]");
    if (await bubble.count()) {
      await bubble
        .getByRole("button", { name: "نعم" })
        .click({ timeout: 15_000 });
    }

    const priceBtn = page.getByRole("button", { name: "السعر مرتفع" });
    if (!(await priceBtn.isVisible().catch(() => false))) {
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

    const reasonPost = page.waitForResponse(
      (r) =>
        r.url().includes("/api/cart-recovery/reason") &&
        r.request().method() === "POST",
      { timeout: 20_000 },
    );

    await priceBtn.click({ timeout: 15_000 });
    const res = await reasonPost;
    expect(res.ok()).toBe(true);

    await expect(page.locator("[data-cf-price-followup-intro]")).toBeVisible({
      timeout: 15_000,
    });

    expect(pageErrors, pageErrors.join("\n---\n")).toEqual([]);
  });
});
