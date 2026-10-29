import assert from 'node:assert/strict';

// Regressions for ADR-039: cutoff clock and local time, mobile next step,
// stable focus across re-renders, normalized search, empty states, successor
// links, the calendar menu, the tablet table and the no-JS conference table.
export async function checkVenueFeatures(page, url) {
  await page.setViewportSize({width: 1440, height: 1000});
  await page.evaluate(() => { Date.now = () => Date.parse('2026-10-06T12:00:00Z'); });
  await page.locator('#tab-deadlines').click();
  await page.locator('#clear-filters').click();
  await page.locator('#open-only').check();
  const row = id => page.locator(`[data-deadline-group][data-edition="${id}"]`);

  // Confirmed exact cutoffs show their recorded clock; estimates never do.
  const mlsysSummary = row('mlsys-2027').locator('[data-deadline-row]:visible');
  // MLSys: CFP says 20:00 UTC, homepage 12:00 PDT; the earliest instant is stored with a note.
  assert.equal(await mlsysSummary.locator('.deadline-clock').innerText(), '12:00 UTC-7');
  assert.equal(await mlsysSummary.locator('.cutoff-note-mark').innerText(), '*');
  const [markBox, clockBox] = await Promise.all([mlsysSummary.locator('.cutoff-note-mark'), mlsysSummary.locator('.deadline-clock')]
    .map(locator => locator.boundingBox()));
  assert(Math.abs(markBox.y - clockBox.y) < 4 && markBox.x > clockBox.x, 'The asterisk stays on the clock line');
  assert.match(await mlsysSummary.locator('.deadline-note').innerText(), /^(Note:\s*)?\* .*Earliest instant stored\.$/);
  assert.equal(await row('icml-2027').locator('.deadline-clock').count(), 0, 'Estimated rows have no clock');
  assert.equal(await row('ifac-sysid-2027').locator('[data-deadline-row]:visible .deadline-clock').count(), 0,
    'Date-only cutoffs have no clock');
  assert.match(await row('aamas-2027').locator('[data-deadline-row]:visible .deadline-clock').innerText(), /^23:59 AoE$/);

  // Re-rendering never detaches the focused control.
  const toggle = row('aamas-2027').locator('.deadline-toggle');
  await toggle.focus();
  await page.keyboard.press('Enter');
  assert(await toggle.evaluate(button => document.activeElement === button), 'Milestone toggle keeps focus');
  await page.evaluate(() => applyFilters());
  assert(await toggle.evaluate(button => document.activeElement === button), 'Minute refresh keeps focus');
  await page.keyboard.press('Enter');

  // Search folds accents, requires every word and matches short words at word starts.
  await page.locator('#clear-filters').click();
  const visibleIds = () => page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.map(r => r.dataset.edition));
  const search = async query => page.evaluate(q => { document.querySelector('#search').value = q; applyFilters(); }, query);
  await search('Montréal');
  const accented = await visibleIds();
  await search('montreal');
  assert.deepEqual(accented, await visibleIds());
  assert(accented.includes('aaai-2027'));
  await search('control lisbon');
  assert.deepEqual(await visibleIds(), await (async () => { await search('lisbon control'); return visibleIds(); })());
  assert(await page.evaluate(() => matchesSearch(' aies 2027 ', ['ai']) && !matchesSearch(' fairness ', ['ai'])));
  await search('');

  // An empty filtered view explains hidden closed rows and offers to show them.
  await page.locator('#open-only').check();
  await search('aistats 2027');
  assert(await page.locator('#deadlines-empty').isVisible());
  assert.match(await page.locator('#deadlines-empty').innerText(), /1 matching conference is closed/);
  assert(await page.locator('#show-hidden').isVisible());
  await page.locator('#deadlines-empty').getByRole('button', {name: 'Show it'}).click();
  assert(!(await page.locator('#open-only').isChecked()));
  assert(await page.locator('#open-only').evaluate(input => document.activeElement === input), 'Focus stays on a stable control');
  assert(await row('aistats-2027').isVisible());
  assert(!(await page.locator('#deadlines-empty').isVisible()));
  const successor = row('aistats-2027').locator('[data-successor-link]');
  assert(await successor.isVisible(), 'Closed editions link their tracked successor');
  assert.match(await successor.innerText(), /^Next: AISTATS 2028 · ~Sep 2027 \(est\.\)$/);
  // The successor row is hidden by the "2027" search; following the link reveals it.
  assert(!(await row('aistats-2028').isVisible()));
  await successor.click();
  assert(await row('aistats-2028').isVisible(), 'Successor link reveals a filtered-out successor');
  assert(await row('aistats-2028').locator('td a').first().evaluate(link => document.activeElement === link));
  await search('');
  await page.locator('#open-only').check();

  // Active filter badge counts restrictions inside the panel.
  if (!(await page.locator('#filter-details').evaluate(details => details.open))) {
    await page.locator('#filter-details > summary').click();
  }
  await page.locator('[data-filter-group="size"][value="xxl"]').check();
  assert.equal(await page.locator('#filter-count').innerText(), '1 active');
  await page.locator('#clear-filters').click();
  assert(await page.locator('#filter-count').isHidden());
  await page.locator('#open-only').check();

  // Calendar menu: aggregate feeds, pickers and the per-row series shortcut.
  const menu = page.locator('#calendar-menu');
  await menu.locator('summary').click();
  assert(await menu.evaluate(details => details.open));
  const seriesActions = menu.locator('#feed-series').locator('xpath=..').locator('[data-feed-actions]');
  await menu.locator('#feed-series').selectOption('series/iclr.ics');
  assert.equal(await seriesActions.locator('[data-feed-webcal]').getAttribute('href'), 'webcal://gon-uri.github.io/venue-radar/series/iclr.ics');
  assert.equal(await seriesActions.locator('[data-feed-download]').getAttribute('href'), 'series/iclr.ics');
  await page.keyboard.press('Escape');
  assert(!(await menu.evaluate(details => details.open)));
  // Restored form state (back/forward) is re-applied to the links on pageshow.
  await page.evaluate(() => {
    document.querySelector('#feed-series').value = 'series/aistats.ics';
    window.dispatchEvent(new Event('pageshow'));
  });
  assert.equal(await seriesActions.locator('[data-feed-download]').getAttribute('href'), 'series/aistats.ics');
  // Keyboard focus leaving the open menu closes it; Escape works from anywhere.
  await menu.locator('summary').focus();
  await page.keyboard.press('Enter');
  assert(await menu.evaluate(details => details.open));
  await page.locator('#search').focus();
  assert(!(await menu.evaluate(details => details.open)), 'Menu closes when focus leaves it');
  await menu.locator('summary').click();
  await page.evaluate(() => document.body.focus());
  await page.keyboard.press('Escape');
  assert(!(await menu.evaluate(details => details.open)), 'Escape closes the menu from outside');
  await page.locator('#tab-conferences').click();
  const seriesShortcut = page.locator('#upcoming-conferences-body [data-edition="neurips-2027"] [data-subscribe-series]');
  assert.match(await seriesShortcut.getAttribute('aria-label'), /^Series feed: /);
  await seriesShortcut.click();
  assert(await menu.evaluate(details => details.open));
  assert.equal(await menu.locator('#feed-series').inputValue(), 'series/neurips.ics');
  await page.keyboard.press('Escape');
  assert(await seriesShortcut.evaluate(link => document.activeElement === link), 'Escape returns focus to the row');
  assert.equal(await menu.locator('#feed-series option[value="series/lod.ics"]').textContent(), 'AIS (formerly LOD)');
  await page.locator('#tab-deadlines').click();

  // Mobile cards show the counted-down action under Time left.
  await page.setViewportSize({width: 390, height: 844});
  const nextStep = row('mlsys-2027').locator('[data-next-step]');
  assert(await nextStep.isVisible());
  assert.match(await nextStep.innerText(), /October 30, 2026, 12:00 UTC-7\*/);
  assert.match(await nextStep.innerText(), /Research and industrial paper submission/);
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'Mobile next step fits');
  await page.locator('#open-only').uncheck();
  const statusCell = row('aistats-2027').locator('td[data-label="Submission status"]');
  const pill = await statusCell.locator('[data-submission-status]').boundingBox();
  const next = await statusCell.locator('[data-successor-link]').boundingBox();
  assert(Math.abs(next.x - pill.x) < 2 && next.y > pill.y, 'Mobile successor link sits under the status pill');
  await page.locator('#open-only').check();
  await page.setViewportSize({width: 1440, height: 1000});
  assert(!(await nextStep.isVisible()), 'Desktop uses the Next milestone column instead');

  // Tablet: headers, names and status pills wrap between words, never inside
  // them (the previous build split "Size" and 78 cells at 768px).
  for (const width of [768, 820, 900]) {
    await page.setViewportSize({width, height: 1024});
    const splits = await page.locator(
      '#panel-deadlines th, #panel-deadlines .submission-status:visible, #panel-deadlines td[data-label="Conference"] a',
    ).evaluateAll(elements => elements.filter(element => {
      const range = document.createRange();
      range.selectNodeContents(element);
      return range.getClientRects().length > element.textContent.trim().split(/\s+/).length;
    }).map(element => element.textContent.trim()));
    assert.deepEqual(splits, [], `No mid-word breaks at ${width}px`);
  }
  await page.setViewportSize({width: 1440, height: 1000});

  // Without JavaScript the conference table (dates and locations) is visible.
  const fallback = await page.context().browser().newPage({javaScriptEnabled: false, viewport: {width: 1440, height: 1000}});
  await fallback.goto(url);
  assert(await fallback.locator('#panel-conferences').isVisible());
  assert(await fallback.locator('#upcoming-conferences-body [data-edition="neurips-2026"] td[data-label="Dates"]').isVisible());
  assert(await fallback.locator('.noscript-note').isVisible());
  assert(!(await fallback.locator('.submission-status').first().isVisible()), 'No stale "Checking..." status');
  assert(!(await fallback.locator('#panel-deadlines th', {hasText: 'Time left'}).isVisible()), 'No empty live columns');
  await fallback.locator('#calendar-menu > summary').click();
  assert(await fallback.locator('[data-feed-download]').first().isVisible());
  assert.equal(await fallback.locator('[data-copy-feed]:visible').count(), 0, 'No inert Copy buttons without JS');
  await fallback.close();

  await page.locator('#clear-filters').click();
  await page.locator('#open-only').check();
  await page.evaluate(() => { Date.now = () => Date.parse('2026-10-06T12:00:00Z'); applyFilters(); });
  console.log('Venue features passed: cutoff clocks, focus, search, empty states, successors, calendar menu, mobile, tablet and no-JS.');
}
