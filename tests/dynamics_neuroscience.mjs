import assert from 'node:assert/strict';

// Resolve a theme token to the computed colour, so checks follow the tokens (ADR-057).
async function tokenColor(page, name) {
  return page.evaluate(token => {
    const probe = document.createElement('i');
    probe.style.color = `var(${token})`;
    document.body.append(probe);
    const value = getComputedStyle(probe).color;
    probe.remove();
    return value;
  }, name);
}


export async function checkDynamicsNeuroscience(page) {
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(() => { Date.now = () => Date.parse('2026-10-08T12:00:00Z'); applyFilters(); });
  await page.locator('#clear-filters').click();
  await page.locator('#tab-deadlines').click();
  await page.locator('#open-only').check();
  const row = id => page.locator(`[data-deadline-group][data-edition="${id}"]`);
  const lac = row('dynamics-days-lac-2026');
  assert(await lac.isVisible());
  assert.equal(await lac.locator('[data-submission-status]').innerText(),'Submission opportunity');
  assert.equal(await lac.locator('[data-deadline-row]:visible').getAttribute('data-deadline-type'),'abstract');
  assert.equal(await lac.locator('[data-submission-status]').evaluate(s=>getComputedStyle(s).color),await tokenColor(page, '--open'));
  assert.equal(await row('areadne-2028').locator('[data-submission-status]').innerText(),'Submission opportunity (estimated)');
  assert(!(await row('iccn-2026').isVisible()),'No invented ICCN submission opportunity');
  assert(!(await row('nodycon-2026').isVisible()),'Past meetings stay out of deadlines');
  await page.locator('#open-only').uncheck();
  assert(await row('iccn-2026').isVisible());
  assert.equal(await row('iccn-2026').locator('[data-submission-status]').innerText(),'Deadline unannounced');
  assert(!(await row('nodycon-2026').isVisible()));
  await page.locator('#tab-conferences').click();
  assert(await page.locator('.city-marker[title^="Rochester, New York"]').isVisible());
  assert.equal(await page.locator('.city-marker[title*="ICCN 2026"]').count(),0);
  if (!(await page.locator('#filter-details').evaluate(d=>d.open))) {
    await page.locator('#filter-details > summary').click();
  }
  await page.locator('#search').fill('neuromorphic');
  assert(await page.locator('#upcoming-conferences-body [data-edition="nice-2027"]').isVisible());
  await page.locator('#clear-filters').click();
  await page.locator('#search').fill('NODYCON');
  await page.locator('#past-conferences-section').evaluate(details => details.open = true);
  assert(await page.locator('#past-conferences-body [data-edition="nodycon-2026"]').isVisible());
  await page.locator('#clear-filters').click();
  await page.locator('#tab-deadlines').click();
  await page.locator('#open-only').check();
  await page.evaluate(() => { Date.now = () => Date.parse('2026-10-06T12:00:00Z'); applyFilters(); });
  console.log('New-series browser checks passed: abstract routes, estimates, unknown deadlines, archives, scope search and Rochester identity.');
}
