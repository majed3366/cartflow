/**
 * Synthetic operational checks against a running CartFlow instance.
 * Uses demo store + test customer phone only (no production data).
 */
import { test, expect } from "@playwright/test";

/** Matches Python integration tests — not a real subscriber number. */
const DEMO_TEST_PHONE = "9665444555666";

test.describe("CartFlow synthetic operational flow", () => {
  test("widget, reason, cart-event, dashboard, admin, return tracker", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

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
    const reasonPost = page.waitForResponse(
      (r) =>
        r.url().includes("/api/cart-recovery/reason") &&
        r.request().method() === "POST",
      { timeout: 20_000 },
    );
    await warrantyBtn.click({ timeout: 15_000 });
    await reasonPost;

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
      return { ok: r.ok, status: r.status, json: j as Record<string, unknown> };
    }, DEMO_TEST_PHONE);

    expect(cartEventRes.ok, JSON.stringify(cartEventRes)).toBe(true);
    expect(cartEventRes.json).toMatchObject({ ok: true, event: "cart_abandoned" });

    await page.goto("/dashboard/normal-carts");
    await expect(
      page.getByRole("heading", { name: "السلال العادية" }),
    ).toBeVisible();

    const strip = page.locator(".cf-onboarding-strip");
    const clarity = page.locator("[data-merchant-clarity-onboarding]");
    const empty = page.locator("#normal-recovery-empty");
    const alerts = page.locator("#normal-recovery-alerts-ul");
    const anySurface =
      (await strip.isVisible().catch(() => false)) ||
      (await clarity.isVisible().catch(() => false)) ||
      (await empty.isVisible().catch(() => false)) ||
      (await alerts.isVisible().catch(() => false));
    expect(
      anySurface,
      "expected onboarding strip, clarity banner, alerts list, or empty-state copy",
    ).toBe(true);

    await page.goto("/admin/operations/login");
    await expect(page.getByText("مركز التشغيل")).toBeVisible();

    const rt = await page.request.get("/static/cartflow_return_tracker.js");
    expect(rt.ok()).toBe(true);

    const benign = (msg: string) =>
      /tailwind is not defined/i.test(msg) ||
      /Refused to execute script/i.test(msg);

    expect(
      pageErrors.filter((e) => !benign(e)),
      pageErrors.join("\n"),
    ).toEqual([]);
  });
});
