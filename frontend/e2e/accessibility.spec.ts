import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

test("open search results have valid accessible options", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("combobox").fill("haaland");
  await expect(
    page.getByRole("option", { name: /Erling Haaland/ }),
  ).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});

async function waitForContent(page: Page, route: string) {
  const selector =
    route === "/models"
      ? ".lab-importance li"
      : route === "/rankings"
        ? ".rankings-table"
        : route === "/players/582"
          ? ".pp-simulator"
          : route === "/"
            ? ".ranking-row"
            : "h1";
  await expect(page.locator(selector).first()).toBeVisible();
  await expect(page.locator(".skeleton")).toHaveCount(0);
  await page.evaluate(() => document.fonts.ready);
}

for (const route of [
  "/",
  "/players/582",
  "/models",
  "/rankings",
  "/missing-page",
]) {
  test(`accessible landmarks and contrast: ${route}`, async ({ page }) => {
    await page.goto(route);
    await waitForContent(page, route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}

test("mobile navigation closes with Escape and returns focus", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu" }).click();
  const home = page
    .getByRole("navigation")
    .getByRole("link", { name: "Home", exact: true });
  await expect(home).toBeVisible();
  await home.focus();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Menu" })).toBeFocused();
  await expect(home).not.toBeVisible();
});

test("all routes fit required viewport widths", async ({ page }, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop",
    "Width matrix runs once in Chromium",
  );
  test.setTimeout(120_000);
  for (const width of [320, 360, 390, 430, 768, 1024, 1280, 1440, 1920, 2560]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ["/", "/players/582", "/models", "/rankings"]) {
      await page.goto(route);
      await waitForContent(page, route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${route} at ${width}px`,
      ).toBe(true);
      await page.screenshot({
        path: `../.local/session15-${route.replaceAll("/", "-") || "home"}-${width}.png`,
        fullPage: true,
      });
    }
  }
});
