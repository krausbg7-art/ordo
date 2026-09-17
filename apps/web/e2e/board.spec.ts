import path from "node:path";
import { expect, test } from "@playwright/test";

// Сценарий из задания: загрузил файл → подтвердил задачи → перетащил
// карточку в «Готово». Используем .ics-фикстуру: события сразу становятся
// предложениями без обращения к ИИ, поэтому сценарий детерминирован и не
// требует настроенных ключей моделей.
const ICS_FIXTURE = path.resolve(__dirname, "../../../tests/fixtures/vstrechi.ics");

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

test("загрузка файла → подтверждение предложения → карточка в «Готово»", async ({ page }) => {
  const email = uniqueEmail("e2e");

  await page.goto("/register");
  await page.fill("input[type=email]", email);
  await page.fill("input[type=password]", "supersecret123");
  await page.click("button[type=submit]");
  await page.waitForURL("**/today");

  // 1. Загрузил файл
  await page.goto("/files");
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByText("или нажмите, чтобы выбрать").click();
  const chooser = await fileChooserPromise;
  await chooser.setFiles(ICS_FIXTURE);

  await expect(page.getByText("Встреча с инвестором")).toBeVisible({ timeout: 15_000 });

  // 2. Подтвердил задачу
  await page.getByRole("button", { name: "Добавить на доску" }).click();
  await expect(page.getByText("Встреча с инвестором")).toHaveCount(0, { timeout: 10_000 });

  // 3. Перетащил карточку в «Готово»
  await page.goto("/board");
  const card = page.getByRole("button", { name: /Встреча с инвестором/ });
  await expect(card).toBeVisible({ timeout: 10_000 });

  const columns = page.locator(".serif.text-xl");
  const doneColumn = columns.filter({ hasText: "Готово" }).first();

  const cardBox = await card.boundingBox();
  const doneBox = await doneColumn.boundingBox();
  if (!cardBox || !doneBox) throw new Error("Не удалось определить координаты для drag-and-drop");

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(cardBox.x + cardBox.width / 2 + 20, cardBox.y - 5, { steps: 5 });
  await page.mouse.move(doneBox.x + 40, doneBox.y + 80, { steps: 10 });
  await page.mouse.up();

  const doneColumnContainer = doneColumn.locator("xpath=ancestor::div[contains(@class,'min-h-[420px]')]");
  await expect(doneColumnContainer.getByText("Встреча с инвестором")).toBeVisible({ timeout: 10_000 });
});
