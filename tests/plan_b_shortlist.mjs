import assert from 'node:assert/strict';

// Regressions for ADR-064 (Plan B after a rejection) and ADR-065 (shareable
// shortlist link). Both are focus views: one banner, a URL parameter, and a
// "Show all venues" exit that restores the full table.
export async function checkPlanBAndShortlist(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-25T12:00:00Z'); applyFilters(); });
  const visible = () => page.$$eval('[data-deadline-group]:not([hidden])', rows => rows.map(row => row.dataset.edition));
  const banner = page.locator('#focus-banner');
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await freeze();
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));
  await page.reload();
  await freeze();
  const everything = await visible();

  // The Plan B link sits under a future decision, in the expanded schedule only.
  const pakdd = page.locator('[data-deadline-group][data-edition="pakdd-2027"]');
  const planB = pakdd.locator('[data-plan-b]');
  assert(!(await planB.isVisible()), 'Collapsed rows hide the Plan B link');
  await pakdd.locator('.deadline-toggle').click();
  assert.equal(await planB.innerText(), 'If rejected: fitting venues still open after this decision');
  await planB.click();
  assert(await banner.isVisible());
  assert.equal(await banner.locator('[data-focus-text]').innerText(),
    'Plan B for PAKDD 2027: venues in the same field still taking papers at least a day after its decision on Feb 26, 2027.');
  assert.match(page.url(), /[?&]after=pakdd-2027(&|$)/);
  const rows = await visible();
  assert(rows.length >= 10 && rows.length < everything.length, `Plan B narrows the list (${rows.length})`);
  assert(rows.includes('ecml-pkdd-2027') && rows.includes('neurips-2027'), 'Same-field venues open after Feb 26 are listed');
  assert(!rows.some(edition => edition.startsWith('pakdd-')), 'The rejecting series is not its own Plan B');
  // ESWC's only routes after Feb 26 are posters and extended abstracts; UAI
  // closes an hour after the decision. Neither is a Plan B for a paper.
  assert(!rows.includes('eswc-2027') && !rows.includes('uai-2027'));
  // Every listed venue shares a central family with PAKDD (ML & Data Science).
  assert(await page.$$eval('[data-deadline-group]:not([hidden])', items => items.every(row => row.dataset.families.split(' ').includes('ml-ai'))));
  await banner.locator('[data-focus-clear]').click();
  assert(await banner.isHidden());
  assert.deepEqual(await visible(), everything, 'Show all venues restores the list');
  assert.doesNotMatch(page.url(), /after=/);
  // A decision that has passed offers no Plan B.
  assert.equal(await page.locator('[data-plan-b="pakdd-2026"]').count() === 0
    || await page.locator('[data-plan-b="pakdd-2026"]').evaluate(button => button.closest('.plan-b-line').hidden), true);

  // Shortlist: stars produce a link; opening it shows those series only.
  assert(await page.locator('#share-starred').isHidden(), 'No stars, no share button');
  await page.locator('[data-deadline-group][data-edition="pakdd-2027"] [data-star]').click();
  await page.locator('[data-deadline-group] [data-star="neurips"]').first().click();
  assert(await page.locator('#share-starred').isVisible());
  const link = await page.evaluate(() => shortlistUrl());
  assert.equal(link, 'https://gon-uri.github.io/venue-radar/?list=neurips,pakdd');
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));
  await page.goto(`${base}?list=pakdd,neurips,not-a-series`);
  await freeze();
  assert.equal(await banner.locator('[data-focus-text]').innerText(), 'Shared shortlist: 2 series (NeurIPS, PAKDD).');
  assert.deepEqual(new Set(await visible()), new Set(['pakdd-2027', 'neurips-2027']));
  assert.match(page.url(), /[?&]list=neurips,pakdd(&|$)/, 'Unknown series are dropped from the link');
  await banner.locator('[data-focus-star]').click();
  assert.equal(await page.evaluate(() => localStorage.getItem('venue-radar:starred')), '["neurips","pakdd"]');
  assert(await banner.locator('[data-focus-star]').isHidden(), 'Once starred, the offer disappears');
  // The conferences tab follows the same shortlist.
  await page.locator('#tab-conferences').click();
  assert(await page.$$eval('[data-conference-row]:not([hidden])', items => items.every(row => ['pakdd', 'neurips'].includes(row.dataset.seriesSlug))));
  await page.locator('#tab-deadlines').click();
  await page.locator('#clear-filters').click();
  assert(await banner.isHidden(), 'Clear filters ends the focus view');
  assert.doesNotMatch(page.url(), /list=/);

  // ADR-062: the field picker points every subscribe action at that family's feed.
  const menu = page.locator('#calendar-menu');
  await menu.locator('summary').click();
  await menu.locator('#feed-family').selectOption('families/neuroscience.ics');
  const actions = menu.locator('#feed-family').locator('xpath=..').locator('[data-feed-actions]');
  assert.equal(await actions.locator('[data-feed-webcal]').getAttribute('href'), 'webcal://gon-uri.github.io/venue-radar/families/neuroscience.ics');
  assert.equal(await actions.locator('[data-copy-feed]').getAttribute('data-copy-feed'), 'https://gon-uri.github.io/venue-radar/families/neuroscience.ics');
  assert.equal(await menu.locator('#feed-family option').count(), 8);
  await page.keyboard.press('Escape');

  // Phones: the banner wraps without horizontal overflow.
  for (const [width, height] of [[390, 844], [320, 700]]) {
    await page.setViewportSize({width, height});
    await page.goto(`${base}?after=pakdd-2027`);
    await freeze();
    assert(await banner.isVisible());
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `No overflow at ${width}px`);
  }
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));
  await page.setViewportSize({width: 1440, height: 1000});
  console.log(`Plan B and shortlist passed: ${rows.length} Plan B venues for PAKDD 2027, paper routes only, share link, star these, both tabs, phones.`);
}
