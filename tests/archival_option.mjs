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

  // The Conference cell holds only the name and star (owner, 2026-11-05); the
  // tag sits under the submission status, or under the dates in Conferences.
  const tag = id => row(id).locator('td[data-label="Submission status"] .archival-tag');
  assert.equal(await page.locator('[data-filter-row] td[data-label="Conference"] .archival-tag').count(), 0);
  assert.equal(await tag('neurips-2027').textContent(), 'Archival option (est.)');
  assert.equal(await tag('aaai-2027').textContent(), 'Archival option');
  assert.equal(await tag('cosyne-2027').textContent(), 'Non-archival');
  assert.equal(await page.locator('#conference-aaai-2027 td[data-label="Dates"] .archival-tag').textContent(), 'Archival option');
  assert.equal(await page.locator('[data-filter-row][data-archival=""] .archival-tag').count(), 0, 'No tag when not checked yet');
  assert.equal(await page.locator('#panel-deadlines th').count(), 8, 'No new column');

  // Instant tooltip on hover and keyboard focus, never a native title.
  assert.equal(await page.locator('.archival-tag[title]').count(), 0);
  await tag('cvpr-2027').hover();
  const bubble = page.locator('#tip-bubble');
  assert(await bubble.isVisible(), 'Hover opens the tip at once');
  assert.match(await bubble.textContent(), /may need to choose it/);
  await tag('neurips-2027').hover();
  assert.match(await bubble.textContent(), /\(est\.\) means it is based on the previous edition/);
  await page.mouse.move(5, 5);
  assert(!(await bubble.isVisible()), 'Leaving closes it');
  await tag('cvpr-2027').focus();
  assert.match(await bubble.textContent(), /Check which track/);
  await page.keyboard.press('Escape');
  assert(!(await bubble.isVisible()));

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
  // On a phone the tag shows on the collapsed card, and a tap opens the tip on screen.
  await freeze();
  const value = tag('cvpr-2027');
  await value.scrollIntoViewIfNeeded();
  assert(await value.isVisible(), 'Visible without expanding the card');
  await value.click();
  const box = await page.locator('#tip-bubble').boundingBox();
  assert(box && box.x >= 0 && box.x + box.width <= 390, 'The tapped tip fits a phone screen');
  console.log('Archival option passed: tag under status or dates, instant tips (hover, focus, tap), filter, archival=1 link, not-checked count, clear and phone layout.');
}
