import assert from 'node:assert/strict';

// Regressions for ADR-058: from 1200px the filters form a sticky left rail
// beside the tables. The rail reuses the ADR-049 controls (search, family and
// archival boxes, More filters content); below 1200px the bar is unchanged.
export async function checkFilterRail(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const details = page.locator('#filter-details');
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await page.evaluate(() => document.fonts.ready);

  const layout = await page.evaluate(() => {
    const rail = document.querySelector('.controls').getBoundingClientRect();
    const tables = document.querySelector('#tables').getBoundingClientRect();
    return {railRight: rail.right, tablesLeft: tables.left, railTop: rail.top, tablesTop: tables.top,
      sticky: getComputedStyle(document.querySelector('.controls')).position};
  });
  assert(layout.railRight < layout.tablesLeft, 'The rail sits left of the tables');
  assert(Math.abs(layout.railTop - layout.tablesTop) < 2, 'Rail and tables start on the same line');
  assert.equal(layout.sticky, 'sticky');
  assert(await details.evaluate(element => element.open));
  assert(await page.locator('#filter-details > summary').isHidden());
  assert(await page.locator('.qb-chips').isHidden());
  assert(await page.locator('[data-family-toggle="neuroscience"]').isVisible(), 'Family boxes are visible in the rail');
  assert(await page.locator('[data-filter-group="archival"]').isVisible(), 'The archival box is visible in the rail');
  const searchBox = await page.locator('#search').boundingBox();
  const familiesBox = await page.locator('.topic-filter').boundingBox();
  assert(searchBox.y + searchBox.height <= familiesBox.y, 'Search is the first control in the rail');
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));

  // Same filters, URL keys and Clear filters as before.
  const all = await page.locator('[data-deadline-group]:visible').count();
  await page.locator('[data-family-toggle="neuroscience"]').check();
  await page.waitForFunction(() => location.search.includes('families=neuroscience'));
  const neuro = await page.locator('[data-deadline-group]:visible').count();
  assert(neuro > 0 && neuro < all);
  assert.equal(await page.locator('[data-chip-family="neuroscience"]').getAttribute('aria-pressed'), 'true', 'The hidden chip still mirrors the box');
  await page.locator('#clear-filters').click();
  assert(!(await page.locator('[data-family-toggle="neuroscience"]').isChecked()), 'Clear filters clears the rail boxes');
  await page.waitForFunction(() => !location.search.includes('families='));
  assert.equal(await page.evaluate(() => document.activeElement.id), 'search', 'Clear filters returns focus to search');

  // The rail also serves the Conferences & Map tab.
  await page.locator('#tab-conferences').click();
  assert(await page.locator('[data-family-toggle="neuroscience"]').isVisible());
  await page.locator('#tab-deadlines').click();

  // Narrowing below 1200px restores the collapsed ADR-049 panel the rail opened.
  await page.setViewportSize({width: 1100, height: 900});
  await page.waitForFunction(() => !document.querySelector('#filter-details').open);
  assert(await page.locator('.qb-chips').isVisible());
  await page.setViewportSize({width: 1440, height: 900});
  await page.waitForFunction(() => document.querySelector('#filter-details').open);
  console.log('Filter rail passed: 1200px+ rail beside tables, sticky, search first, same filters and Clear, both tabs, resize back to the bar.');
}
