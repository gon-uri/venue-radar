import assert from 'node:assert/strict';

// Regressions for ADR-047: archival tags on rows, one filter kept in the link
// as archival=1, and series without a researched value hidden but counted as
// "not checked yet" (never treated as No).
export async function checkArchivalOption(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-05T12:00:00Z'); applyFilters(); });
  const row = id => page.locator(`[data-deadline-group][data-edition="${id}"]`);
  await page.setViewportSize({width: 1440, height: 1000});
  await page.goto(base);
  await freeze();

  // Tags: confirmed, estimated from an earlier call, and non-archival.
  assert.equal(await row('neurips-2027').locator('.archival-tag').textContent(), 'Archival option (est.)');
  assert.equal(await row('aaai-2027').locator('.archival-tag').textContent(), 'Archival option');
  assert.match(await row('aaai-2027').locator('.archival-tag').getAttribute('title'), /may need to choose it/);
  assert.equal(await row('cosyne-2027').locator('.archival-tag').textContent(), 'Non-archival');
  assert.equal(await page.locator('[data-filter-row][data-archival=""] .archival-tag').count(), 0, 'No tag when not checked yet');

  // The filter keeps Yes and Yes (est.), hides No, and is shared in the link.
  await page.locator('[data-filter-group="archival"]').check();
  await page.waitForFunction(() => location.search.includes('archival=1'));
  assert(await row('neurips-2027').isVisible());
  assert(!(await row('cosyne-2027').isVisible()), 'Non-archival series are hidden');
  assert.equal(await page.locator('#filter-count').textContent(), '1 active');
  await page.goto(`${base}?archival=1&tab=conferences`);
  await freeze();
  assert(await page.locator('[data-filter-group="archival"]').isChecked(), 'archival=1 restores the filter');
  const unchecked = await page.locator('#upcoming-conferences-body [data-conference-row][data-archival=""]').count();
  if (unchecked) assert.match(await page.locator('#result-count').textContent(), /not checked yet (is|are) hidden/);
  assert.equal(await page.locator('[data-conference-row][data-archival="0"]:visible').count(), 0);

  // Clear filters removes it; the note stays readable on a phone.
  await page.locator('#clear-filters').click();
  assert(!(await page.locator('[data-filter-group="archival"]').isChecked()));
  await page.setViewportSize({width: 390, height: 900});
  await page.goto(base);
  await page.evaluate(() => { document.querySelector('#filter-details').open = true; });
  const note = await page.locator('.archival-note').boundingBox();
  assert(note && note.width > 200 && note.x + note.width <= 390, 'The archival note fits a phone screen');
  console.log('Archival option passed: tags, estimate labels, filter, archival=1 link, not-checked count, clear and phone layout.');
}
