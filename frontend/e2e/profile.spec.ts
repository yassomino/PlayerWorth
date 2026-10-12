import { expect, test } from "@playwright/test";

test("live profile, seasons, unsaved simulator and responsive chart", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/");
  await page.getByRole("combobox").fill("haaland");
  await page.getByRole("option", { name: /Erling Haaland/ }).click();
  await expect(
    page.getByRole("heading", { name: "Erling Haaland" }),
  ).toBeVisible();
  await expect(page.getByTestId("model-estimate")).toHaveAttribute(
    "title",
    "€148,951,056.00",
  );
  await expect(page.locator(".pp-observed")).toContainText("€200M");
  await expect(page.locator(".pp-observed")).toContainText(
    "below observed value",
  );
  await expect(page.locator(".recharts-line-curve")).toBeVisible();
  await page.getByText("View recorded values as a table").click();
  await expect(page.locator(".pp-chart-data tbody tr")).toHaveCount(4);
  await page.getByLabel("Goals", { exact: true }).fill("20");
  await page.getByLabel("Assists", { exact: true }).fill("12");
  const response = page.waitForResponse(
    (response) =>
      response.url().includes("/simulate") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: /Update estimate/ }).click();
  const payload = await (await response).json();
  expect(payload.prediction_id).toBeNull();
  expect(payload.simulation.predicted_value_eur).toBe(73917992);
  await expect(page.getByTestId("simulated-value")).toHaveAttribute(
    "title",
    "€73,917,992.00",
  );
  await expect(page.locator(".pp-simulation-warning")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../.local/profile-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Reset to season stats" }).click();
  await expect(page.getByLabel("Goals", { exact: true })).toHaveValue("27");
  await expect(page.getByTestId("simulated-value")).toHaveAttribute(
    "title",
    "€148,951,056.00",
  );
  await page
    .getByLabel("Selected season", { exact: true })
    .selectOption("2024/25");
  await expect(page.getByLabel("Goals", { exact: true })).toHaveValue("22");
  await expect(page.getByLabel("Minutes", { exact: true })).toHaveValue("2743");
  await expect(page).toHaveURL(/season=2024%2F25/);
  await page.reload();
  await expect(page.getByLabel("Selected season", { exact: true })).toHaveValue(
    "2024/25",
  );
  await expect(page.getByLabel("Goals", { exact: true })).toHaveValue("22");
  await page.goBack();
  await expect(page.getByLabel("Selected season", { exact: true })).toHaveValue(
    "2025/26",
  );
  await expect(page.getByLabel("Goals", { exact: true })).toHaveValue("27");
  expect(errors).toEqual([]);
});

test("missing player has a clear recovery route", async ({ page }) => {
  await page.goto("/players/999999999");
  await expect(
    page.getByRole("heading", { name: "Player not found" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Back to PlayerWorth/ }),
  ).toBeVisible();
});
