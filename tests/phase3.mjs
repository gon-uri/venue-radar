import assert from 'node:assert/strict';

// Regressions for ADR-059 (identity v2, phase 3): horizon bars, "/" search,
// theme toggle, rail collapse, phone filter sheet and the Agenda layout.
export async function checkPhase3(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-14T12:00:00Z'); applyFilters(); });
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await page.evaluate(() => { try { localStorage.clear(); } catch (error) {} });
  await page.goto(base);
  await freeze();

  // Horizon bars: every open row carries a 0..1 share and the bar is drawn.
  const horizons = await page.locator('[data-deadline-group]:visible .time-left-cell').evaluateAll(cells =>
    cells.map(cell => [cell.dataset.horizon, getComputedStyle(cell, '::after').content]));
  assert(horizons.length > 0 && horizons.every(([value, content]) => Number(value) >= 0 && Number(value) <= 1 && content === '""'));

  // "/" focuses search unless the reader is typing.
  await page.locator('body').click({position: {x: 5, y: 5}});
  await page.keyboard.press('/');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'search');
  await page.keyboard.type('icml');
  await page.keyboard.press('/');
  assert.equal(await page.locator('#search').inputValue(), 'icml/', 'Typing "/" inside search stays text');
  await page.locator('#search').fill('');
  await page.locator('#search').dispatchEvent('input');

  // Theme toggle: system -> light -> dark -> system, remembered.
  const toggle = page.locator('#theme-toggle');
  const body = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.emulateMedia({colorScheme: 'light'});
  await toggle.click();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'light');
  await toggle.click();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark');
  assert.equal(await body(), 'rgb(16, 28, 31)');
  await page.reload();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark', 'The choice survives a reload');
  await page.emulateMedia({colorScheme: 'dark'});
  await toggle.click();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), undefined);
  assert.equal(await body(), 'rgb(16, 28, 31)', 'System choice follows the dark OS setting');
  await page.emulateMedia({colorScheme: 'light'});
  assert.equal(await body(), 'rgb(247, 251, 251)');
  assert.match(await toggle.getAttribute('aria-label'), /^Colour theme: follows your system\. Switch to light$/);

  // Rail collapse (1200px+): strip, count, remembered.
  await page.goto(`${base}?families=neuroscience`);
  await freeze();
  const rail = page.locator('#rail-toggle');
  assert.equal(await rail.getAttribute('aria-expanded'), 'true');
  await rail.click();
  assert.equal(await rail.getAttribute('aria-expanded'), 'false');
  assert(await page.locator('#search').isHidden(), 'A collapsed rail hides its controls');
  assert.equal(await page.locator('#rail-count').innerText(), '1');
  const strip = await page.locator('.controls').boundingBox();
  assert(strip.width <= 60, 'The collapsed rail is a thin strip');
  await page.reload();
  assert.equal(await rail.getAttribute('aria-expanded'), 'false', 'Collapse is remembered');
  await rail.click();
  assert(await page.locator('#search').isVisible());
  await page.setViewportSize({width: 1100, height: 900});
  assert(await rail.isHidden(), 'No collapse button below the rail width');

  // Phone filter sheet: dialog, focus, live count, Escape and Close.
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base);
  await freeze();
  const summary = page.locator('#filter-details > summary');
  await summary.focus();
  await page.keyboard.press('Enter');
  const sheet = page.locator('#filter-details > .filter-content');
  await page.waitForFunction(() => document.querySelector('#filter-details > .filter-content').getAttribute('role') === 'dialog');  // toggle fires async
  assert.equal(await page.evaluate(() => document.activeElement.classList.contains('sheet-close')), true);
  const box = await sheet.boundingBox();
  assert(box.x <= 0 && box.width >= 389 && box.height >= 843, 'The sheet covers the screen');
  assert.match(await page.locator('.sheet-apply').innerText(), /^Show \d+ conferences?$/);
  const before = await page.locator('.sheet-apply').innerText();
  await page.locator('[data-family-toggle="neuroscience"]').check();
  await page.waitForFunction(text => document.querySelector('.sheet-apply').textContent !== text, before);
  await page.keyboard.press('Escape');
  assert(!(await page.locator('#filter-details').evaluate(element => element.open)));
  assert.equal(await page.evaluate(() => document.activeElement.parentElement.id), 'filter-details', 'Focus returns to More filters');
  await summary.click();
  await page.locator('.sheet-apply').click();
  assert(!(await page.locator('#filter-details').evaluate(element => element.open)));
  assert(!(await page.evaluate(() => document.body.classList.contains('sheet-open'))));

  // Agenda: switch, link, headings in time order, remembered, no overflow.
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    await page.setViewportSize({width, height});
    await page.goto(base);
    await freeze();
    await page.locator('.view-switch [data-view="agenda"]').click();
    await page.waitForFunction(() => location.search.includes('view=agenda'));
    const headings = await page.locator('.agenda-group th').allTextContents();
    assert.deepEqual(headings, ['This week', 'Next 30 days', 'Later'], `Agenda headings at ${width}px`);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `Agenda overflow at ${width}px`);
    if (width > 760) {
      const first = page.locator('[data-deadline-group]:visible').first();
      assert.match(await first.evaluate(row => getComputedStyle(row, '::before').content), /^"\d{1,2}\\a ?[A-Z][a-z]{2}"$/i);
    }
    await page.reload();
    assert.equal(await page.locator('.agenda-group').count(), 3, 'The agenda view survives a reload');
    await page.locator('.view-switch [data-view="table"]').click();
    assert.equal(await page.locator('.agenda-group').count(), 0);
  }
  await page.evaluate(() => { try { localStorage.clear(); } catch (error) {} });
  await page.setViewportSize({width: 1440, height: 1000});
  console.log('Phase 3 passed: horizon bars, "/" search, theme toggle, rail collapse, phone sheet and agenda (1440/390px).');
}
