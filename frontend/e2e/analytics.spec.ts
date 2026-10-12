import { expect, test } from "@playwright/test";
import { formatMoney, fullMoney } from "../lib/format";
import type { ModelResponse, RankingResponse } from "../lib/api/types";
const api =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

test("live Model Lab, protocol boundaries and responsive chart", async ({
  page,
  request,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const current = (await (
    await request.get(`${api}/models/current`)
  ).json()) as ModelResponse;
  await page.goto("/");
  await page
    .getByRole("contentinfo")
    .getByRole("link", { name: /Model Lab/ })
    .click();
  await expect(page).toHaveURL(/\/models$/);
  await expect(
    page.getByRole("heading", { name: current.model_name }),
  ).toBeVisible();
  await expect(page.getByLabel("Current registered model")).toContainText(
    `v${current.model_version}`,
  );
  await expect(page.getByLabel("Current registered model")).toContainText(
    formatMoney(current.mae!, 2),
  );
  await expect(
    page.getByRole("heading", {
      name: "Exploratory 2025/26 held-out-season comparison",
    }),
  ).toBeVisible();
  await expect(page.locator(".lab-evolution li")).toHaveCount(6);
  await expect(page.locator(".lab-folds article")).toHaveCount(4);
  await expect(page.locator(".lab-pooled")).toContainText("€9,677,493.91");
  await expect(page.getByText(/then rejected from V1/)).toBeVisible();
  await expect(page.locator(".lab-importance li")).toHaveCount(13);
  await expect(
    page.getByRole("heading", { name: "Premier League only" }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../.local/models-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("live rankings direction, season URL, API order and profile navigation", async ({
  page,
  request,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const above = (await (
    await request.get(`${api}/rankings/undervalued?limit=20`)
  ).json()) as RankingResponse;
  const below = (await (
    await request.get(`${api}/rankings/overvalued?limit=20`)
  ).json()) as RankingResponse;
  await page.goto("/rankings");
  await expect(page.getByLabel("Season", { exact: true })).toHaveValue(
    above.season,
  );
  await expect(page.locator(".rankings-table tbody tr")).toHaveCount(
    above.items.length,
  );
  expect(
    await page.locator(".rankings-player strong").allTextContents(),
  ).toEqual(above.items.map((row) => row.player_name));
  const firstRow = page.locator(".rankings-table tbody tr").first();
  await expect(firstRow.locator(".rankings-delta strong")).toHaveAttribute(
    "title",
    fullMoney(above.items[0].difference_eur),
  );
  await expect(firstRow).toContainText("above observed value");
  await page.getByRole("button", { name: /Model Below Observed/ }).click();
  await expect(firstRow).toContainText(below.items[0].player_name);
  expect(
    await page.locator(".rankings-player strong").allTextContents(),
  ).toEqual(below.items.map((row) => row.player_name));
  await expect(firstRow.locator(".rankings-delta strong")).toHaveAttribute(
    "title",
    fullMoney(below.items[0].difference_eur),
  );
  await expect(firstRow).toContainText("below observed value");
  await page.getByLabel("Season", { exact: true }).selectOption("2024/25");
  const previous = (await (
    await request.get(`${api}/rankings/overvalued?limit=20&season=2024%2F25`)
  ).json()) as RankingResponse;
  await expect(page.locator(".rankings-summary")).toContainText("2024/25");
  await expect(firstRow).toContainText(previous.items[0].player_name);
  await expect(page).toHaveURL(/season=2024%2F25&direction=below/);
  await page.reload();
  await expect(page.getByLabel("Season", { exact: true })).toHaveValue(
    "2024/25",
  );
  await expect(
    page.getByRole("button", { name: /Model Below Observed/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(firstRow).toContainText(previous.items[0].player_name);
  await page.goBack();
  await expect(page.getByLabel("Season", { exact: true })).toHaveValue(
    above.season,
  );
  await expect(firstRow).toContainText(below.items[0].player_name);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../.local/rankings-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  if (testInfo.project.name === "mobile") {
    await expect(
      firstRow.locator(".rankings-mobile-label").first(),
    ).toBeVisible();
    expect(
      await firstRow.evaluate((element) => getComputedStyle(element).display),
    ).toBe("grid");
  }
  await firstRow.getByRole("link").click();
  await expect(page).toHaveURL(
    new RegExp(`/players/${below.items[0].player_id}\\?season=`),
  );
  await expect(
    page.getByRole("heading", { name: below.items[0].player_name }),
  ).toBeVisible();
  await expect(page.getByLabel("Selected season", { exact: true })).toHaveValue(
    below.season,
  );
  expect(errors).toEqual([]);
});
