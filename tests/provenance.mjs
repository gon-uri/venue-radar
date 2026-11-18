import assert from 'node:assert/strict';

// Regressions for ADR-055: an estimated milestone names what it rests on, the
// confirmed date in the last edition that had it, linked to that source. It
// appears in the expanded schedule only, so collapsed rows and cards keep
// their height, and never on confirmed milestones.
export async function checkProvenance(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const freeze = () => page.evaluate(() => { Date.now = () => Date.parse('2026-11-18T12:00:00Z'); applyFilters(); });
  const row = page.locator('[data-deadline-group][data-edition="neurips-2027"]');
  const abstract = row.locator('[data-deadline-row][data-deadline-type="abstract"]');
  const basis = abstract.locator('.deadline-basis');
  for (const [width, height] of [[1440, 900], [390, 844], [320, 700]]) {
    await page.setViewportSize({width, height});
    await page.goto(base);
    await freeze();
    if (width <= 760) await row.locator('.mobile-info-toggle').click();
    const collapsed = await row.evaluate(element => element.getBoundingClientRect().height);
    assert(!(await basis.isVisible()), `Collapsed rows hide the provenance line at ${width}px`);
    await row.locator('.deadline-toggle').click();
    assert(await basis.isVisible(), `Expanded schedule shows it at ${width}px`);
    assert.equal(await basis.innerText(), 'Last edition: May 4, 2026');
    assert.equal(await basis.locator('a').getAttribute('href'), 'https://neurips.cc/Conferences/2026/Dates');
    // The estimate marker is not repeated inside the label.
    assert.doesNotMatch(await row.locator('.deadline-milestone').allInnerTexts().then(texts => texts.join('|')), /Estimated/);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `No overflow at ${width}px`);
    if (width > 760) {
      await row.locator('.deadline-toggle').click();
      assert.equal(await row.evaluate(element => element.getBoundingClientRect().height), collapsed, 'Collapsing restores the row height');
    }
  }
  // Confirmed milestones carry no provenance line (ICML's 2027 call is out).
  assert.equal(await page.locator('[data-edition="icml-2027"] [data-deadline-type="full_paper"] .deadline-basis').count(), 0);
  // An estimated meeting cites the last confirmed meeting.
  assert.match(await page.locator('[data-edition="neurips-2027"] [data-deadline-type="conference_start"] .deadline-basis')
    .evaluate(element => element.textContent), /^Last edition: December \d+, 2026$/);
  // Without JavaScript every provenance line is visible.
  const fallback = await page.context().browser().newPage({javaScriptEnabled: false, viewport: {width: 1440, height: 900}});
  try {
    await fallback.goto(base);
    assert(await fallback.locator('[data-edition="neurips-2027"] [data-deadline-type="abstract"] .deadline-basis').isVisible());
  } finally {
    await fallback.close();
  }
  console.log('Provenance passed: last-edition date on estimates only, expanded rows only, linked source, no overflow at 1440/390/320px, no-JS.');
}
