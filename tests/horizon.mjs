import assert from 'node:assert/strict';

// Regressions for ADR-051: "Due within" time-range buttons on Upcoming Deadlines.
export async function checkHorizon(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const NOW = Date.parse('2026-11-14T12:00:00Z');
  const freeze = () => page.evaluate((now) => { Date.now = () => now; applyFilters(); }, NOW);
  const button = days => page.locator(`[data-within="${days}"]`);
  const count = async () => Number((await page.locator('#result-count').innerText()).split(' ')[0]);
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await freeze();

  assert.equal(await button(0).getAttribute('aria-pressed'), 'true', 'Any is the default');
  const any = await count();
  assert(await page.locator('#show-hidden').isVisible(), 'Any keeps the closed/unannounced link');
  const sizes = {};
  for (const days of [30, 90, 180]) {
    await button(days).click();
    assert.equal(await button(days).getAttribute('aria-pressed'), 'true');
    assert.equal(await button(0).getAttribute('aria-pressed'), 'false');
    await page.waitForFunction((d) => location.search.includes(`within=${d}`), days);
    sizes[days] = await count();
    // Every visible row's next submission action falls inside the window.
    assert(await page.evaluate(({days, now}) => [...document.querySelectorAll('[data-deadline-group]')]
      .filter(row => !row.hidden).every(row => {
        const time = stateByRow.get(row).milestone?.time;
        return Number.isFinite(time) && time <= now + days * 86400000;
      }), {days, now: NOW}), `Rows respect the ${days}-day window`);
    // A range covers upcoming submission steps only, so the link that reveals
    // closed or unannounced editions is not offered while it is active.
    assert(await page.locator('#show-hidden').isHidden(), `No closed/unannounced link inside a ${days}-day window`);
  }
  assert(sizes[30] < sizes[90] && sizes[90] < sizes[180] && sizes[180] < any, JSON.stringify({...sizes, any}));
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));

  // The range survives a reload through the link; Clear filters resets it.
  await page.goto(`${base}?within=30`);
  await freeze();
  assert.equal(await button(30).getAttribute('aria-pressed'), 'true');
  assert.equal(await count(), sizes[30]);
  await page.locator('#clear-filters').click();
  assert.equal(await button(0).getAttribute('aria-pressed'), 'true');
  assert(!(await page.evaluate(() => location.search.includes('within'))));
  for (const value of ['7', '090', '%2B90', '0x1e', '%2030']) {
    await page.goto(`${base}?within=${value}`);
    await freeze();
    assert.equal(await button(0).getAttribute('aria-pressed'), 'true', `within=${value} is not an exact value, so it means Any`);
  }

  // A shared link to a row outside the window still shows it.
  await page.goto(`${base}?within=30#icml-2027`);
  await freeze();
  await page.evaluate(() => followHash());
  assert(await page.locator('[data-deadline-group][data-edition="icml-2027"]').isVisible(), 'Deep link overrides the window');
  assert.equal(await button(0).getAttribute('aria-pressed'), 'true');

  // Buttons belong to the Upcoming Deadlines tab only, and fit on a phone.
  await page.goto(base);
  await page.locator('#tab-conferences').click();
  assert(!(await page.locator('.horizon').isVisible()));
  await page.locator('#tab-deadlines').click();
  assert(await page.locator('.horizon').isVisible());
  for (const width of [390, 320]) {
    await page.setViewportSize({width, height: 844});
    await page.goto(base);
    const rows = await page.locator('.horizon button').evaluateAll(buttons => new Set(buttons.map(b => Math.round(b.getBoundingClientRect().top))).size);
    assert.equal(rows, 1, `The four buttons share one row at ${width}px`);
    assert(await page.locator('.horizon button').evaluateAll(buttons => buttons.every(b => b.getBoundingClientRect().height >= 36)));
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  }
  // Choosing a range never moves the table under the pointer.
  for (const width of [1400, 1200, 1100, 768, 320]) {
    await page.setViewportSize({width, height: 900});
    await page.goto(base);
    await freeze();
    const top = () => page.locator('#deadlines-body').evaluate(body => Math.round(body.getBoundingClientRect().top));
    const before = await top();
    await button(30).click();
    assert.equal(await top(), before, `No table jump at ${width}px`);
  }
  // Without JavaScript the buttons would do nothing, so they are not shown.
  const fallback = await page.context().browser().newPage({javaScriptEnabled: false, viewport: {width: 1280, height: 900}});
  try {
    await fallback.goto(base);
    assert(!(await fallback.locator('.horizon').isVisible()), 'No inert time-range buttons without JavaScript');
  } finally {
    await fallback.close();
  }
  await page.setViewportSize({width: 1440, height: 900});
  console.log(`Time range passed: Any ${any}, 6 months ${sizes[180]}, 90 days ${sizes[90]}, 30 days ${sizes[30]}; link, clear, deep link, tab and phone layout.`);
}
