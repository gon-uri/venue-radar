import assert from 'node:assert/strict';
import path from 'node:path';

async function visibleLabels(row) {
  return row.locator('td:visible').evaluateAll(cells => cells.map(cell => cell.dataset.label || 'More info'));
}

async function checkMobilePresentation(row) {
  assert(await row.evaluate(row => {
    // Colours resolve through the theme tokens (ADR-057), so the check holds in light and dark.
    const token = name => {
      const probe = document.createElement('i');
      probe.style.color = `var(${name})`;
      document.body.append(probe);
      const value = getComputedStyle(probe).color;
      probe.remove();
      return value;
    };
    const card = getComputedStyle(row);
    const header = getComputedStyle(row.querySelector('[data-label="Conference"]'));
    const labels = [...row.querySelectorAll('td[data-label]')];
    return card.marginBottom === '14px' && card.borderTopWidth === '1px' &&
      card.borderTopColor === token('--line-strong') && header.backgroundColor === token('--raised') &&
      labels.every(cell => {
        const label = getComputedStyle(cell, '::before');
        return label.fontSize === '13px' && label.fontWeight === '700' && label.color === token('--muted');
      });
  }), 'Mobile cards need readable labels, card-coloured headers, stronger borders and clear spacing');
}

async function checkDisclosure(row, collapsedLabels) {
  // Check the resting style regardless of where a prior click left the pointer.
  await row.page().mouse.move(0, 0);
  assert.deepEqual(await visibleLabels(row), [...collapsedLabels, 'More info']);
  await checkMobilePresentation(row);
  const button = row.locator('.mobile-info-toggle');
  assert.equal(await button.getAttribute('aria-expanded'), 'false');
  assert.equal(await button.locator('[data-mobile-info-label]').innerText(), 'More info');
  assert(await button.evaluate(button => {
    const cells = button.getAttribute('aria-controls').split(' ').map(id => document.getElementById(id));
    const box = button.getBoundingClientRect();
    const card = button.closest('tr').getBoundingClientRect();
    return cells.length === 5 && cells.every(cell => cell?.closest('tr') === button.closest('tr')) &&
      box.height >= 44 && box.width >= 44 && box.width < 60 && box.right <= card.right && box.bottom <= card.bottom + 1 &&
      box.left >= 0 && box.right <= innerWidth;
  }), 'Every card needs its own controlled details and a 44px chevron in its corner (ADR-049)');
}

export async function checkMobileCards(page, url, output) {
  for (const width of [760, 390, 320]) {
    await page.setViewportSize({width, height: 844});
    await page.goto(url);
    await page.evaluate(() => document.fonts.ready);
    const filters = page.locator('#filter-details');
    const summary = filters.locator(':scope > summary');
    assert(!(await filters.evaluate(details => details.open)), `Mobile filters start closed at ${width}px`);
    assert(await page.locator('#search').isVisible(), 'Search stays visible on phones (ADR-049)');
    assert(await page.locator('#clear-filters').isVisible());
    assert(await page.locator('#open-only').isChecked());
    await summary.focus();
    await page.keyboard.press('Enter');
    await page.setViewportSize({width: 1440, height: 1000});
    assert(await filters.evaluate(details => details.open), 'Resize must preserve an explicitly opened filter');
    await page.setViewportSize({width, height: 844});
    assert(await filters.evaluate(details => details.open));
    await summary.click();

    const deadlines = page.locator('[data-deadline-group]:visible');
    const first = page.locator('[data-deadline-group][data-edition="ifac-sysid-2027"]');
    const other = page.locator('[data-deadline-group]:visible:not([data-edition="ifac-sysid-2027"])').first();
    assert.equal(await deadlines.locator('.mobile-detail:visible').count(), 0);
    await checkDisclosure(first, ['Conference', 'Submission status', 'Time left']);
    const collapsedHeight = (await first.boundingBox()).height;
    if (output) await first.screenshot({path: path.join(output, `mobile-deadline-collapsed-${width}.png`)});
    const toggle = first.locator('.mobile-info-toggle');
    await toggle.click();
    assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
    assert.equal(await toggle.locator('[data-mobile-info-label]').innerText(), 'Less info');
    assert.equal(await first.locator('.mobile-detail:visible').count(), 5);
    await checkMobilePresentation(first);
    assert.equal(await other.locator('.mobile-detail:visible').count(), 0, 'Cards expand independently');
    assert((await first.boundingBox()).height > collapsedHeight + 100);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    if (output) await first.screenshot({path: path.join(output, `mobile-deadline-expanded-${width}.png`)});
    await first.locator('.deadline-toggle').click();
    assert.equal(await first.locator('[data-deadline-row]:visible').count(), await first.locator('[data-deadline-row]').count());
    await toggle.focus();
    await page.keyboard.press('Space');
    await checkDisclosure(first, ['Conference', 'Submission status', 'Time left']);
    assert(await toggle.evaluate(button => document.activeElement === button), 'Collapsing retains keyboard focus');
    await page.keyboard.press('Enter');
    assert.equal(await first.locator('[data-deadline-row]:visible').count(), await first.locator('[data-deadline-row]').count(), 'Nested milestone expansion survives card collapse');
    await first.locator('.deadline-toggle').click();
    await page.evaluate(() => {
      search.value = 'coling';
      applyFilters();
    });
    assert(!(await first.isVisible()));
    await page.evaluate(() => {
      search.value = '';
      applyFilters();
    });
    assert.equal(await first.locator('.mobile-detail:visible').count(), 5, 'Filtering preserves expansion');
    await page.setViewportSize({width: 1440, height: 1000});
    assert.equal(await first.locator('.mobile-detail:visible').count(), 5);
    assert.equal(await other.locator('.mobile-detail:visible').count(), 5, 'Desktop always shows all metadata');
    assert.equal(await page.locator('.mobile-row-disclosure:visible').count(), 0);
    assert(await filters.evaluate(details => details.open), 'The 1200px+ rail shows the filters (ADR-058)');
    await page.setViewportSize({width, height: 844});
    await page.waitForFunction(() => !document.querySelector('#filter-details').open);  // collapsed again on the phone
    assert.equal(await first.locator('.mobile-detail:visible').count(), 5);
    await toggle.click();

    await page.locator('#tab-conferences').click();
    const conferences = page.locator('#upcoming-conferences-body [data-conference-row]:visible');
    const conference = conferences.first();
    const neighbor = conferences.nth(1);
    assert.equal(await conferences.locator('.mobile-detail:visible').count(), 0);
    await checkDisclosure(conference, ['Conference', 'Dates', 'Location']);
    if (output) await conference.screenshot({path: path.join(output, `mobile-conference-collapsed-${width}.png`)});
    await conference.locator('.mobile-info-toggle').focus();
    await page.keyboard.press('Enter');
    assert.equal(await conference.locator('.mobile-detail:visible').count(), 5);
    await checkMobilePresentation(conference);
    assert(await conference.locator('.row-calendar-button').isVisible());
    assert.equal(await neighbor.locator('.mobile-detail:visible').count(), 0);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    if (output) await conference.screenshot({path: path.join(output, `mobile-conference-expanded-${width}.png`)});
    await page.locator('#tab-deadlines').click();
    await page.locator('#tab-conferences').click();
    assert.equal(await conference.locator('.mobile-detail:visible').count(), 5, 'Tab switching preserves expansion');
    await conference.locator('.mobile-info-toggle').click();
    await checkDisclosure(conference, ['Conference', 'Dates', 'Location']);
    await page.locator('#past-conferences-section').evaluate(details => details.open = true);
    const past = page.locator('#past-conferences-body [data-conference-row]:visible').first();
    await checkDisclosure(past, ['Conference', 'Dates', 'Location']);
    await past.locator('.mobile-info-toggle').click();
    assert.equal(await past.locator('.mobile-detail:visible').count(), 5);
  }

  const fallback = await page.context().browser().newPage({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
  try {
    await fallback.goto(url);
    const row = fallback.locator('[data-deadline-group]').first();
    assert.equal(await row.locator('.mobile-detail:visible').count(), 5, 'Without JavaScript, all metadata stays accessible');
    assert.equal(await row.locator('.mobile-info-toggle:visible').count(), 0, 'No inert mobile controls in the fallback');
  } finally {
    await fallback.close();
  }
  await page.setViewportSize({width: 761, height: 1000});
  await page.goto(url);
  assert(!(await page.locator('#filter-details').evaluate(details => details.open)), 'More filters starts collapsed on desktop too (ADR-049)');
  assert.equal(await page.locator('.mobile-row-disclosure:visible').count(), 0);
  assert(await page.locator('[data-filter-row]').evaluateAll(rows => rows.every(row =>
    getComputedStyle(row).marginBottom === '0px' &&
    getComputedStyle(row.querySelector('[data-label="Conference"]')).backgroundColor === 'rgba(0, 0, 0, 0)'
  )), 'Mobile card styling must not affect desktop rows');
  await page.setViewportSize({width: 1440, height: 1000});
  console.log('Mobile cards passed: independent disclosures, keyboard/resize/filter persistence, past editions, and no-JS fallback.');
}
