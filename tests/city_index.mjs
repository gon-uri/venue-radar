import assert from 'node:assert/strict';

// Regressions for ADR-061: the city index beside the map (regions, busiest
// first, filter box, marker highlight) and its collapsed phone list.
export async function checkCityIndex(page, url) {
  const base = url.split('#')[0].split('?')[0];
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(`${base}?tab=conferences`);
  await page.waitForFunction(() => document.querySelectorAll('.map-city-link').length > 0);
  const map = await page.locator('#conference-map').boundingBox();
  const index = await page.locator('#city-index').boundingBox();
  assert(index.x >= map.x + map.width && Math.abs(index.y - map.y) < 2 && Math.abs(index.height - map.height) < 2, 'The index sits beside the map, same height');
  assert(await page.locator('#city-index-toggle').isHidden(), 'No toggle on desktop');
  const heads = await page.locator('.city-group-head').allTextContents();
  const order = ['Europe', 'North America', 'Asia', 'South America', 'Oceania', 'Africa'];
  const names = heads.map(text => text.replace(/\s+\d+$/, ''));
  assert.deepEqual(names, order.filter(name => names.includes(name)), 'Regions follow the fixed order');
  const total = Number((await page.locator('#map-count').innerText()).match(/in (\d+) cit/)[1]);
  assert.equal(await page.locator('.map-city-link').count(), total, 'One row per mapped city');
  assert.equal(heads.reduce((sum, text) => sum + Number(text.match(/(\d+)$/)[1]), 0), total);
  for (const group of await page.locator('.city-group').all()) {
    const counts = (await group.locator('.city-count').allTextContents()).map(Number);
    assert.deepEqual(counts, [...counts].sort((a, b) => b - a), 'Busiest cities first within a region');
  }
  // Hover highlights the marker; a click opens its popup as before.
  const montreal = page.locator('.map-city-link').filter({hasText: 'Montreal'});
  await montreal.hover();
  await page.waitForFunction(() => document.querySelectorAll('.city-marker.is-hot').length === 1);  // hovering highlights its marker
  await montreal.click();
  assert.match(await page.locator('.city-popup').innerText(), /Montreal/);
  await page.locator('.leaflet-popup-close-button').click();
  // The filter box narrows the list (accent-insensitive) without filtering the page.
  const rows = await page.locator('[data-conference-row]:visible').count();
  await page.locator('#city-filter').fill('linkoping');
  assert.deepEqual(await page.locator('.map-city-link:visible .city-name').allTextContents(), ['Linköping']);
  assert.equal(await page.locator('[data-conference-row]:visible').count(), rows, 'The city filter is local to the index');
  await page.locator('#city-filter').fill('zzzz');
  assert(await page.locator('#city-index-empty').isVisible());
  await page.locator('#city-filter').fill('');
  await page.locator('#city-filter').dispatchEvent('input');
  // Page filters still drive the index.
  await page.goto(`${base}?tab=conferences&families=neuroscience`);
  await page.waitForFunction(() => document.querySelectorAll('.map-city-link').length > 0);
  const filtered = Number((await page.locator('#map-count').innerText()).match(/in (\d+) cit/)[1]);
  assert.equal(await page.locator('.map-city-link').count(), filtered);
  assert(filtered < total);
  // Phone: collapsed under the map, "Show N host cities".
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(`${base}?tab=conferences`);
  await page.waitForFunction(() => document.querySelectorAll('.map-city-link').length > 0);
  const toggle = page.locator('#city-index-toggle');
  assert.match(await toggle.innerText(), new RegExp(`^Show ${total} host cities`));
  assert(await page.locator('#city-filter').isHidden());
  await toggle.click();
  assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
  assert(await page.locator('#city-filter').isVisible());
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  await page.setViewportSize({width: 1440, height: 1000});
  console.log(`City index passed: beside the map, ${heads.length} regions in order, busiest first, hover/click, local filter, page filters, phone toggle.`);
}
