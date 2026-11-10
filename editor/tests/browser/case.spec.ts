// The low-profile cases are made by the dev server's make (vite.config.ts), so
// this runs against Vite's dev server.
import { test, expect, type Page } from '@playwright/test';
import { rebuilt } from './helpers';

const shown = (page: Page) => page.evaluate(() => (window as any).rosebearEditor.getCase());

for (const [id, label] of [
  ['shell', 'Low-profile shell on Swung in'],
  ['wells', 'Low-profile shell with wells'],
  ['lowpro', 'Low-profile'],
  ['frame', 'Low-profile frame'],
] as const)
  test(`the ${label} case shows for both halves, and the frame comes back`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await rebuilt(page);
    expect(await shown(page)).toMatchObject({ case: 'capybara', frameVisible: true });

    await page.getByLabel('Case').selectOption(id);
    for (const half of ['right', 'left']) {
      await page.getByLabel('Half').selectOption(half);
      await expect(page.locator('#view-state')).toContainText('not your edits', {
        timeout: 60000,
      });
      await expect(page.locator('#subtitle')).toContainText(label);
      const c = await shown(page);
      expect(c).toMatchObject({ case: id, frameVisible: false, lowproVisible: true });
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
    expect(await shown(page)).toMatchObject({ frameVisible: true, lowproVisible: false });
    await expect(page.locator('#stl')).toBeVisible();
    expect(errors).toEqual([]);
  });

test("Wiring and pads shows and hides a low-profile case's wires", async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await rebuilt(page);
  const wires = async () => (await shown(page)).pieces.filter((p: any) => p.kind === 'wires');

  await page.getByLabel('Case').selectOption('shell');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
  await expect(page.getByLabel('Wiring and pads')).toBeHidden();
  expect(await wires()).toHaveLength(0);

  await page.getByLabel('Case').selectOption('frame');
  await expect(page.locator('#subtitle')).toContainText('Low-profile frame');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
  expect((await wires()).map((p: any) => p.name)).toContain('wire RX');
  expect((await wires()).every((p: any) => p.visible)).toBe(true);
  await page.getByLabel('Wiring and pads').uncheck();
  expect((await wires()).some((p: any) => p.visible)).toBe(false);

  await page.getByLabel('Case').selectOption('lowpro');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
  expect((await wires()).map((p: any) => p.name)).toContain('wire RX');
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

const showWells = async (page: Page) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByLabel('Case').selectOption('wells');
  await expect(page.locator('#view-state')).toContainText('not your edits', { timeout: 60000 });
};

test('Paint draws on a low-profile case', async ({ page }) => {
  let saved: any;
  await page.route('**/__marks', (r) => {
    if (r.request().method() !== 'POST') return r.fulfill({ json: [] });
    saved = JSON.parse(r.request().postData()!);
    return r.fulfill({ json: {} });
  });
  await showWells(page);
  await page.locator('#mk-paint').click();
  const box = (await page.locator('#viewport canvas').boundingBox())!,
    x = box.x + box.width / 2,
    y = box.y + box.height / 2;
  await page.mouse.move(x - 50, y);
  await page.mouse.down();
  for (let i = 0; i <= 10; i++) await page.mouse.move(x - 50 + i * 10, y);
  await page.mouse.up();
  await page.locator('#mk-save').click();
  await expect.poll(() => saved?.hits.on).toContain('wells body');
});

/** How many of the canvas's pixels are the low-profile body's warm tan. */
const tan = async (page: Page) => {
  const png = (await page.locator('#viewport canvas').screenshot()).toString('base64');
  return page.evaluate(async (png) => {
    const img = await createImageBitmap(await (await fetch('data:image/png;base64,' + png)).blob()),
      c = new OffscreenCanvas(img.width, img.height).getContext('2d')!;
    c.drawImage(img, 0, 0);
    const d = c.getImageData(0, 0, img.width, img.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] > 100 && d[i] > 1.3 * d[i + 2]) n++;
    return n;
  }, png);
};

test("Chassis opacity sees through a low-profile case's body", async ({ page }) => {
  await showWells(page);
  // The body alone: the bottom section and some components are warm too.
  await page.getByLabel('Bottom section').uncheck();
  await page.getByLabel('Tiles and components').uncheck();
  const solid = await tan(page);
  expect(solid).toBeGreaterThan(10000);
  await page.locator('#opacity').fill('0.1');
  expect(await tan(page)).toBeLessThan(solid / 4);
});
