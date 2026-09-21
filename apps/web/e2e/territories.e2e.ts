import { expect, test } from "@playwright/test";

test("shows the example communes served by the API", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("cell", { name: "Annecy" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "01053" })).toBeVisible();
  await expect(page.getByText("12 territoires — page 1 sur 3")).toBeVisible();
});

test("keeps the search in the URL after a reload", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("searchbox", { name: "Rechercher une commune" })
    .fill("lyon");

  await expect(page).toHaveURL(/q=lyon/);
  await expect(page.getByText("1 territoire — page 1 sur 1")).toBeVisible();

  await page.reload();

  await expect(page.getByRole("cell", { name: "Lyon" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Annecy" })).toBeHidden();
});

test("paginates on the server and follows the browser history", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Suivant" }).click();

  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByRole("cell", { name: "Grenoble" })).toBeVisible();

  await page.goBack();

  await expect(page.getByRole("cell", { name: "Annecy" })).toBeVisible();
});
