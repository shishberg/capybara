// The low-profile cases are made by the dev server's make (vite.config.ts), so
// this runs against Vite's dev server.
import { test, expect, type Page } from '@playwright/test';
import { rebuilt } from './helpers';

const shown = (page: Page) => page.evaluate(() => (window as any).rosebearEditor.getCase());

for (const [id, label] of [
  ['shell', 'Low-profile shell on Swung in'],
  ['wells', 'Low-profile shell with wells'],
  ['lowpro', 'Low-profile'],
] as const)
  test(`the ${label} case shows for both halves, and the frame comes back`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await rebuilt(page);
    expect(await shown(page)).toMatchObject({ case: 'capybara', modelVisible: true });

    await page.getByLabel('Case').selectOption(id);
    for (const half of ['right', 'left']) {
      await page.getByLabel('Half').selectOption(half);
      await expect(page.locator('#view-state')).toContainText('not your edits', {
        timeout: 60000,
      });
      await expect(page.locator('#subtitle')).toContainText(label);
      const c = await shown(page);
      expect(c).toMatchObject({ case: id, modelVisible: false, lowproVisible: true });
      for (const name of ['body', 'plinth'])
        expect(c.pieces.filter((p: any) => p.name === name && p.visible)).toHaveLength(1);
      expect(c.pieces.some((p: any) => p.kind === 'keycaps')).toBe(true);
      await expect(page.locator('#size')).toContainText(/Size: [\d.]+ W/);
      await expect(page.locator('#stl')).toBeHidden();
      await expect(page.locator('#rebuild')).toBeHidden();
    }

    await page.getByLabel('Keycaps').check();
    const caps = (await shown(page)).pieces.filter((p: any) => p.kind === 'keycaps');
    expect(caps.length).toBeGreaterThan(0);
    expect(caps.every((p: any) => p.visible)).toBe(true);

    await page.getByLabel('Case').selectOption('capybara');
    expect(await shown(page)).toMatchObject({ modelVisible: true, lowproVisible: false });
    await expect(page.locator('#stl')).toBeVisible();
    expect(errors).toEqual([]);
  });

test('a case survives a reload', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByLabel('Case').selectOption('lowpro');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
  await page.reload();
  await expect(page.getByLabel('Case')).toHaveValue('lowpro');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
});
