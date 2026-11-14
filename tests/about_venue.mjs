import assert from 'node:assert/strict';

// Regressions for ADR-050: venue facts in an expanded row. The archival track
// is visible there; the scope summary is a closed "About this venue" toggle.
export async function checkAboutVenue(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-14T12:00:00Z'); applyFilters(); });
  const row = page.locator('[data-deadline-group][data-edition="icml-2027"]');
  const about = row.locator('.about-venue');
  const details = about.locator('.about-details');
  for (const [width, height] of [[1440, 900], [390, 844]]) {
    await page.setViewportSize({width, height});
    await page.goto(base);
    await freeze();
    if (width <= 760) await row.locator('.mobile-info-toggle').click();
    assert(!(await about.isVisible()), `Hidden until the row is expanded at ${width}px`);
    await row.locator('.deadline-toggle').click();
    assert(await about.isVisible());
    assert.match(await about.locator('.about-archival').innerText(), /^Archival track: Main track full papers · PMLR/);
    assert(!(await details.evaluate(element => element.open)), 'The scope summary starts closed');
    assert(!(await details.locator('p').isVisible()));
    await details.locator('summary').click();
    assert(await details.evaluate(element => element.open));
    assert.match(await details.locator('p').innerText(), /Methodological and theoretical machine learning/);
    assert.match(await details.locator('p').innerText(), /\(from the 2026 call\)$/);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `No overflow at ${width}px`);
  }
  // Keyboard: the toggle is a native disclosure.
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await freeze();
  await row.locator('.deadline-toggle').click();
  await details.locator('summary').focus();
  await page.keyboard.press('Enter');
  assert(await details.evaluate(element => element.open), 'Enter opens About this venue');
  // A non-archival venue names its track, never maintainer shorthand.
  const cosyne = page.locator('[data-deadline-group][data-edition="cosyne-2028"] .about-archival');
  assert.match(await cosyne.evaluate(element => element.textContent), /^Non-archival: /);
  assert.doesNotMatch(await cosyne.evaluate(element => element.textContent), /none/);
  // Without JavaScript the block is shown for every row.
  const fallback = await page.context().browser().newPage({javaScriptEnabled: false, viewport: {width: 1440, height: 900}});
  try {
    await fallback.goto(base);
    assert(await fallback.locator('[data-edition="icml-2027"] .about-venue').isVisible(), 'No-JS keeps venue facts reachable');
  } finally {
    await fallback.close();
  }
  console.log('About this venue passed: hidden until expanded, archival line, closed scope toggle, keyboard, non-archival wording, phone and no-JS.');
}
