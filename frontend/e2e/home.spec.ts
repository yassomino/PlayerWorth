import { expect, test } from "@playwright/test";
test("live homepage, search, navigation and responsive layout", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /THE GAME/ })).toBeVisible();
  await expect(page.getByText("€9.68M")).toBeVisible();
  await expect(page.getByText("Igor Thiago")).toBeVisible();
  await expect(page.getByText("William Saliba")).toBeVisible();
  await page.getByRole("combobox").fill("haaland");
  await expect(page.getByRole("option")).toContainText("Erling Haaland");
  const profilePath = await page
    .getByRole("option", { name: /Erling Haaland/ })
    .getAttribute("href");
  expect(profilePath).toMatch(/^\/players\/\d+$/);
  await page.screenshot({
    path: `../.local/home-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("combobox").press("ArrowDown");
  await page.getByRole("combobox").press("Enter");
  await expect(page).toHaveURL(new RegExp(`${profilePath}$`));
  await expect(
    page.getByRole("heading", { name: "Erling Haaland" }),
  ).toBeVisible();
  for (const [route, label, content] of [
    ["/models", /Model Lab/, ".lab-importance li"],
    ["/rankings", /Rankings/, ".rankings-table"],
  ] as const) {
    await page
      .getByRole("contentinfo")
      .getByRole("link", { name: label })
      .click();
    await expect(page).toHaveURL(new RegExp(`${route}$`));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator(content).first()).toBeVisible();
  }
  if (testInfo.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu" }).click();
    await expect(
      page.getByRole("navigation").getByRole("link", { name: "Players" }),
    ).toBeVisible();
  }
  expect(errors).toEqual([]);
});
