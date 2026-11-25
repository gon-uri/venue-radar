import assert from 'node:assert/strict';

// Regressions for ADR-066 (design review fixes, 2026-11-25).
export async function checkReviewFixes(page, url) {
  const base = url.split('#')[0].split('?')[0];
  const ida = page.locator('#deadlines-body [data-deadline-group][data-edition="ida-2027"]');

  // 1. The sticky rail ends with the tables; it never covers the community section.
  await page.setViewportSize({width: 1280, height: 900});
  await page.goto(base);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  const rail = await page.locator('.controls').boundingBox();
  const community = await page.locator('#community').boundingBox();
  assert(rail.y + rail.height <= community.y + 1, 'The rail stops above the community section');

  // 2. Expanded rows read from the top.
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(base);
  await ida.locator('.deadline-toggle').click();
  const rowTop = (await ida.boundingBox()).y;
  assert((await ida.locator('td[data-label="Conference"] a').boundingBox()).y - rowTop < 24, 'The name sits at the top of an expanded row');
  assert.equal(await page.locator('.deadline-clock').first().evaluate(node => getComputedStyle(node, '::before').content), 'none');

  // 4. The rank pair stays on one line at 1200px.
  await page.setViewportSize({width: 1200, height: 900});
  const pair = await ida.locator('.rank-pair').boundingBox();
  assert(pair.height < 30, 'ICORE / CCF stays on one line');

  // 3. Small tablets: two topics plus "+N", and the rate word is not split.
  await page.setViewportSize({width: 768, height: 1024});
  assert.equal(await ida.locator('.topic-tags').evaluate(node => getComputedStyle(node, '::after').content), '"+2"');
  const rate = ida.locator('td[data-label="Accept. rate"] strong');
  assert.equal(await rate.evaluate(node => { const r = document.createRange(); r.selectNodeContents(node); return r.getClientRects().length; }), 1, 'The rate word stays whole');

  // 8. Topic families: one chevron, no left marker.
  await page.setViewportSize({width: 1440, height: 900});
  assert(await page.locator('.topic-family > summary').evaluateAll(nodes => nodes.every(node => getComputedStyle(node).display === 'flex')));

  // Community: four buttons, one primary; comments follow the page theme.
  assert.equal(await page.locator('.community-links .community-button').count(), 4);
  assert.equal(await page.locator('.community-links .community-button.is-primary').count(), 1);
  assert.equal(await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; return giscusTheme(); }), 'transparent_dark');
  assert.equal(await page.evaluate(() => { document.documentElement.dataset.theme = 'light'; return giscusTheme(); }), 'light');
  await page.evaluate(() => { delete document.documentElement.dataset.theme; });

  // 5. Phones: an open card shows the schedule once, without the inner toggle.
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base);
  await ida.locator('.mobile-info-toggle').click();
  assert.equal(await ida.locator('.deadline-toggle:visible').count(), 0);
  assert(!(await ida.locator('.next-step').isVisible()));
  const chip = await ida.locator('td[data-label="Size"] .meta-pill').boundingBox();
  assert(chip.width < 60, 'The size chip keeps its own width');
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  console.log('Review fixes passed: rail/footer, top-aligned rows, ranks, tablet topics, topic chevrons, community buttons, giscus theme, phone cards.');
}
