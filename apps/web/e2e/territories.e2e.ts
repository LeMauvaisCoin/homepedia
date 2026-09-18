import { expect, test } from "@playwright/test";

test("affiche les communes du jeu d’exemple servies par l’API", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByRole("cell", { name: "Annecy" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "01053" })).toBeVisible();
  await expect(page.getByText("12 territoires — page 1 sur 3")).toBeVisible();
});

test("conserve la recherche dans l’URL après rechargement", async ({
  page,
}) => {
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

test("pagine côté serveur et suit l’historique du navigateur", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Suivant" }).click();

  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByRole("cell", { name: "Grenoble" })).toBeVisible();

  await page.goBack();

  await expect(page.getByRole("cell", { name: "Annecy" })).toBeVisible();
});
