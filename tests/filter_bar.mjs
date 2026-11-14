import assert from 'node:assert/strict';

// Regressions for ADR-049: an always-visible bar (search, family chips,
// archival chip) above a collapsed "More filters" panel, and compact phone cards.
export async function checkFilterBar(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-14T12:00:00Z'); applyFilters(); });
  const details = page.locator('#filter-details');
  const chip = family => page.locator(`[data-chip-family="${family}"]`);
  const visibleRows = () => page.locator('[data-deadline-group]:visible').count();
  await page.setViewportSize({width: 1280, height: 720});
  await page.goto(base);
  await freeze();

  // Content first: deadline rows are on screen at a laptop size.
  const first = await page.locator('[data-deadline-group]:visible').first().boundingBox();
  assert(first.y + first.height < 720, 'A complete deadline row fits in a 1280x720 viewport');
  assert(!(await details.evaluate(element => element.open)));
  assert.deepEqual(await page.locator('.chip').allTextContents(),
    ['ML & Data', 'NLP & Agents', 'Vision', 'RL & Control', 'Complex Systems', 'Healthcare', 'Neuroscience',
      'Responsible AI', 'Archival option']);
  assert.equal(new Set(await page.locator('.chip').evaluateAll(chips => chips.map(c => Math.round(c.getBoundingClientRect().top)))).size, 1,
    'The chips fit on one line at 1280px');

  // A chip is the same filter as its family toggle, shared in the link.
  const all = await visibleRows();
  await chip('neuroscience').click();
  assert.equal(await chip('neuroscience').getAttribute('aria-pressed'), 'true');
  assert(await page.locator('[data-family-toggle="neuroscience"]').isChecked());
  await page.waitForFunction(() => location.search.includes('families=neuroscience'));
  const neuro = await visibleRows();
  assert(neuro > 0 && neuro < all);
  assert(await page.locator('#filter-count').isHidden(), 'Visible chips are not counted in the More filters badge');
  await chip('neuroscience').click();
  assert.equal(await chip('neuroscience').getAttribute('aria-pressed'), 'false');
  assert.equal(await visibleRows(), all);

  // Archival chip mirrors the archival box.
  await page.locator('[data-chip-archival]').click();
  assert(await page.locator('[data-filter-group="archival"]').isChecked());
  await page.waitForFunction(() => location.search.includes('archival=1'));
  await page.locator('[data-chip-archival]').click();
  assert(!(await page.locator('[data-filter-group="archival"]').isChecked()));

  // Some subtopics of a family: the chip shows as partly pressed and the
  // hidden selection is counted on the collapsed panel.
  await page.goto(`${base}?topics=computational-neuroscience`);
  await freeze();
  assert(await details.evaluate(element => element.open), 'A link using a hidden filter opens More filters');
  assert.equal(await chip('neuroscience').getAttribute('aria-pressed'), 'mixed');
  assert.equal(await page.locator('#filter-count').innerText(), '1 active');
  await page.locator('#clear-filters').click();
  assert.equal(await chip('neuroscience').getAttribute('aria-pressed'), 'false');
  assert(await page.evaluate(() => document.activeElement.id === 'search'), 'Clear filters returns focus to search');

  // Phone: search and chips visible, icon-only header buttons, compact cards.
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base);
  await freeze();
  assert(await page.locator('#search').isVisible());
  for (const name of ['Share on X', 'Star the repo']) {
    const link = page.getByRole('link', {name, exact: true});
    const box = await link.boundingBox();
    assert(box.width >= 44 && box.height >= 44, `${name} keeps a 44px target`);
  }
  const card = page.locator('[data-deadline-group]:visible').first();
  const [status, tag] = await Promise.all([card.locator('[data-submission-status]').boundingBox(),
    card.locator('td[data-label="Submission status"] .archival-tag').boundingBox()]);
  assert(Math.abs(status.y + status.height / 2 - (tag.y + tag.height / 2)) < 6, 'The archival tag sits beside the status');
  const toggle = card.locator('.mobile-info-toggle');
  const toggleBox = await toggle.boundingBox();
  assert(toggleBox.width >= 44 && toggleBox.height >= 44 && toggleBox.width < 60, 'More info is a 44px chevron');
  assert.equal(await toggle.getAttribute('aria-label'), `More info for ${(await card.locator('td[data-label="Conference"] a').innerText()).trim()}`);
  const heights = await page.locator('[data-deadline-group]:visible').evaluateAll(rows =>
    rows.slice(0, 15).map(row => row.getBoundingClientRect().height).sort((a, b) => a - b));
  assert(heights[7] < 175, `Median phone card ${heights[7]}px stays compact`);
  await toggle.click();
  assert(await card.locator('td[data-label="Topics"]').isVisible(), 'The chevron still expands the card');
  await toggle.click();

  // Nothing readable or tappable sits under the corner chevron, on either tab.
  const overlaps = () => page.evaluate(() => {
    const hits = [];
    const intersects = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
    document.querySelectorAll('[data-filter-row]').forEach((row) => {
      if (row.hidden || !row.offsetParent) return;
      const chevron = row.querySelector('.mobile-info-toggle')?.getBoundingClientRect();
      if (!chevron || !chevron.width) return;
      row.querySelectorAll('td:not(.mobile-row-disclosure)').forEach((cell) => {
        if (!cell.offsetParent) return;
        const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
          if (!node.textContent.trim() || !node.parentElement.offsetParent) continue;
          const range = document.createRange();
          range.selectNodeContents(node);
          if ([...range.getClientRects()].some((rect) => rect.width && intersects(rect, chevron))) hits.push(row.dataset.edition);
        }
        cell.querySelectorAll('.archival-tag, a, button').forEach((item) => {
          const rect = item.getBoundingClientRect();
          if (rect.width && intersects(rect, chevron)) hits.push(row.dataset.edition);
        });
      });
    });
    return [...new Set(hits)];
  });
  for (const width of [320, 390, 760]) {
    await page.setViewportSize({width, height: 844});
    await page.goto(base);
    await freeze();
    assert.deepEqual(await overlaps(), [], `Deadline cards keep text clear of the chevron at ${width}px`);
    await page.locator('#tab-conferences').click();
    await page.locator('#past-conferences-section').evaluate(details => { details.open = true; });
    assert.deepEqual(await overlaps(), [], `Conference cards keep text clear of the chevron at ${width}px`);
  }

  // The chip row scrolls sideways on phones, so the focus ring is drawn inside the chip.
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base);
  await chip('ml-ai').focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.dataset.chipFamily), 'language-agents-retrieval');
  assert(await page.evaluate(() => {
    const active = document.activeElement;
    const style = getComputedStyle(active);
    return parseFloat(style.outlineOffset) < 0 && style.outlineStyle !== 'none';
  }), 'Phone chip focus ring is fully visible');

  // "All selected families" restricts nothing until two families are chosen.
  await page.setViewportSize({width: 1280, height: 720});
  await page.goto(`${base}?match=all`);
  await freeze();
  assert(await page.locator('#filter-count').isHidden(), 'Match alone is not an active filter');
  await page.goto(`${base}?match=all&families=neuroscience,healthcare`);
  await freeze();
  assert.equal(await page.locator('#filter-count').innerText(), '1 active');
  await page.locator('#clear-filters').click();
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  console.log('Filter bar passed: content first at 1280x720, chips mirror families and archival, mixed state, badge, link auto-open, phone cards and header.');
}
