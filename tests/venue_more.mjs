import assert from 'node:assert/strict';

// Regressions for ADR-040: deep links and URL state, evidence line and
// correction form, starred series, status guide and spoken countdowns,
// host-zone date-only cutoffs, sticky headers, compact cards, previews, sprite.
export async function checkMoreFeatures(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-10-06T12:00:00Z'); applyFilters(); });
  const row = id => page.locator(`[data-deadline-group][data-edition="${id}"]`);
  await page.setViewportSize({width: 1440, height: 1000});

  // Deep links: series key -> next edition; closed edition -> revealed; past -> archive.
  await page.goto(`${base}#neurips`);
  await freeze();
  await page.evaluate(() => followHash());
  assert(await row('neurips-2027').isVisible(), '#neurips opens the next NeurIPS edition');
  assert(await row('neurips-2027').locator('td a').first().evaluate(link => document.activeElement === link));
  await page.goto(`${base}#aistats-2027`);
  await freeze();
  await page.evaluate(() => followHash());
  assert(await row('aistats-2027').isVisible(), 'A linked closed edition is shown');
  assert(!(await page.locator('#open-only').isChecked()));
  // A past edition opens inside the archive.
  await page.goto(`${base}#ts4h-2025`);
  await freeze();
  await page.evaluate(() => followHash());
  assert(await page.locator('#past-conferences-section').evaluate(details => details.open), 'The archive opens');
  assert(await page.locator('#conference-ts4h-2025').isVisible(), 'A past edition is shown');
  // Starred only never hides a linked edition.
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));
  await page.goto(`${base}?starred=1#neurips-2027`);
  await freeze();
  await page.evaluate(() => followHash());
  assert(await row('neurips-2027').isVisible(), 'A linked edition is shown under Starred only');
  assert(!(await page.locator('#starred-only').isChecked()));
  // A malformed escape does not stop initialization (minute refresh, comments).
  const errors = [];
  const onError = error => errors.push(error.message);
  page.on('pageerror', onError);
  await page.goto(`${base}#neurips-2027%`);
  assert.equal(await page.evaluate(() => typeof commentObserver), 'object');
  page.off('pageerror', onError);
  assert.deepEqual(errors, []);
  // Parameters the page does not own survive (Giscus returns with ?giscus=<session>).
  await page.goto(`${base}?giscus=abc&size=s`);
  await freeze();
  assert.match(await page.evaluate(() => location.search), /giscus=abc/);
  assert(await page.locator('[data-filter-group="size"][value="s"]').isChecked());
  // Element-id hashes (old successor hrefs) become the edition hash; a past one opens the archive.
  await page.goto(`${base}#deadline-ts4h-2025`);
  await freeze();
  assert.equal(await page.evaluate(() => location.hash), '#ts4h-2025');
  assert(await page.locator('#conference-ts4h-2025').isVisible());
  // Back restores the controls from the URL after a link rewrote the entry.
  await page.goto(`${base}?q=neurips`);
  await page.evaluate(() => { location.hash = '#aistats-2027'; });
  await page.waitForFunction(() => document.querySelector('#search').value === '');
  await page.goBack();
  await page.waitForFunction(() => document.querySelector('#search').value === 'neurips');
  // A followed link leaves the address bar once the view changes, so a reload keeps the new filters.
  await page.goto(`${base}#icml-2027`);
  await freeze();
  if (!(await page.locator('#filter-details').evaluate(details => details.open))) await page.locator('#filter-details > summary').click();
  await page.locator('[data-filter-group="size"][value="s"]').check();
  assert.equal(await page.evaluate(() => location.hash), '');
  await page.reload();
  await freeze();
  assert(await page.locator('[data-filter-group="size"][value="s"]').isChecked(), 'A reload keeps the newer filters');

  // Filters live in the query string and survive a reload.
  await page.goto(base);
  await freeze();
  if (!(await page.locator('#filter-details').evaluate(details => details.open))) await page.locator('#filter-details > summary').click();
  await page.locator('[data-filter-group="size"][value="xxl"]').check();
  await page.locator('#search').fill('vision');
  const query = await page.evaluate(() => location.search);
  assert.match(query, /size=xxl/);
  assert.match(query, /q=vision/);
  const visible = await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.map(r => r.dataset.edition));
  await page.goto(`${base}${query}`);
  await freeze();
  assert.equal(await page.locator('#search').inputValue(), 'vision');
  assert(await page.locator('[data-filter-group="size"][value="xxl"]').isChecked());
  assert.deepEqual(await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.map(r => r.dataset.edition)), visible);
  await page.locator('#clear-filters').click();
  assert.equal(await page.evaluate(() => location.search), '?all=1', 'Clear filters keeps only the unchecked submission toggle');
  await page.locator('#open-only').check();
  assert.equal(await page.evaluate(() => location.search), '');

  // Evidence line: sources, review date, copy link and a prefilled correction form.
  await row('aamas-2027').locator('.deadline-toggle').click();
  const evidence = row('aamas-2027').locator('.evidence-line');
  assert(await evidence.isVisible());
  assert.match(await evidence.innerText(), /Call for papers/);
  assert.match(await evidence.innerText(), /Checked [A-Z][a-z]{2} \d+, 20\d\d/);
  assert(await evidence.locator('[data-copy-link]').isVisible());
  const report = new URL(await evidence.getByRole('link', {name: 'Report outdated info'}).getAttribute('href'));
  assert.equal(report.searchParams.get('template'), 'correction.yml');
  assert.equal(report.searchParams.get('edition'), 'aamas-2027');
  await row('aamas-2027').locator('.deadline-toggle').click();
  await row('icml-2027').locator('.deadline-toggle').click();
  assert.match(await row('icml-2027').locator('.evidence-line').innerText(), /Previous call.*Dates estimated/s);
  await row('icml-2027').locator('.deadline-toggle').click();
  // A row without a schedule toggle shows its evidence line directly.
  await page.locator('#open-only').uncheck();
  assert.equal(await row('iccn-2026').locator('.deadline-toggle').count(), 0);
  assert(await row('iccn-2026').locator('.evidence-line').isVisible(), 'Unannounced rows keep their correction link');
  await page.locator('#open-only').check();

  // Starred series: per browser, keyed by series, with a filter and feed shortcuts.
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));
  await page.goto(base);
  await freeze();
  assert(await page.locator('.starred-toggle').isHidden(), 'No starred filter before starring');
  const star = row('neurips-2027').locator('[data-star]');
  await star.click();
  assert.equal(await star.getAttribute('aria-pressed'), 'true');
  assert.equal(await star.getAttribute('aria-label'), 'Star NeurIPS', 'aria-pressed carries the state, not the name');
  assert(!(await page.locator('symbol#icon-star').evaluate(symbol => symbol.hasAttribute('fill'))), 'The sprite lets a pressed star fill');
  assert.notEqual(await star.locator('svg').evaluate(svg => getComputedStyle(svg).fill), 'none');
  assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem('venue-radar:starred'))), ['neurips']);
  await page.locator('#starred-only').check();
  const starredRows = await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.map(r => r.dataset.seriesSlug));
  assert(starredRows.length > 0 && starredRows.every(slug => slug === 'neurips'));
  await page.locator('#calendar-menu > summary').click();
  assert(await page.locator('[data-starred-feeds]').isVisible());
  await page.keyboard.press('Escape');
  await page.locator('#starred-only').uncheck();
  await star.click();
  assert(await page.locator('.starred-toggle').isHidden());
  await page.evaluate(() => localStorage.removeItem('venue-radar:starred'));

  // Status guide and spoken countdowns.
  assert.equal(await page.locator('.status-guide > summary').innerText(), 'What do the statuses mean?');
  assert.equal(await row('mlsys-2027').locator('[data-time-left]').getAttribute('aria-hidden'), 'true');
  assert.match(await row('mlsys-2027').locator('[data-time-left-sr]').textContent(), /^\d+ days? \d+ hours? left$/);
  assert.match(await row('bci-winter-2027').locator('[data-time-left-sr]').textContent(), /left, exact hour unannounced$/);

  // A published day without an hour ends at 23:59 in the host city (Jeongseon).
  const bciTime = row('bci-winter-2027').locator('[data-deadline-row][data-deadline-type="full_paper"] time');
  assert.equal(await bciTime.getAttribute('datetime'), '2026-11-15T14:59:00Z');
  assert.match(await bciTime.getAttribute('title'), /exact hour\/timezone unannounced.*23:59 Asia\/Seoul time/);

  // Desktop column labels stay visible while scrolling, without covering keyboard focus.
  assert.equal(await page.locator('#panel-deadlines thead th').first().evaluate(th => getComputedStyle(th).position), 'sticky');
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollPaddingTop), '56px');

  // Compact mobile cards: name and countdown share the first row.
  await page.setViewportSize({width: 390, height: 844});
  const card = row('mlsys-2027');
  const [name, left, status] = await Promise.all(['Conference', 'Time left', 'Submission status']
    .map(label => card.locator(`td[data-label="${label}"]`).boundingBox()));
  assert(Math.abs(name.y - left.y) < 2 && left.x > name.x, 'Countdown sits beside the name');
  assert(status.y >= name.y + name.height - 2, 'Status sits below the name');
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  // The deep-link highlight shows on compact cards too.
  await card.evaluate(tr => tr.classList.add('is-linked'));
  assert.equal(await card.locator('td[data-label="Conference"]').evaluate(td => getComputedStyle(td).backgroundColor), 'rgb(255, 247, 223)');
  await card.evaluate(tr => tr.classList.remove('is-linked'));
  await page.setViewportSize({width: 1440, height: 1000});

  // Link previews and the shared icon sprite.
  assert.equal(await page.locator('meta[property="og:image"]').getAttribute('content'),
    'https://raw.githubusercontent.com/gon-uri/venue-radar/main/assets/branding/social-card.png');
  assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://gon-uri.github.io/venue-radar/');
  assert.equal(await page.locator('symbol#icon-chevron-down').count(), 1);
  assert(await page.locator('.mobile-info-toggle use').first().evaluate(use => use.getAttribute('href') === '#icon-chevron-down'));

  await page.goto(base);
  await freeze();
  console.log('More features passed: deep links, URL state, evidence, correction form, starred, status guide, host-zone cutoffs, sticky header, compact cards, previews and sprite.');
}
