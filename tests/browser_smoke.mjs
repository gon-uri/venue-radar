import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
import {checkSubmissionBehavior} from './submission_behavior.mjs';
import {checkMobileCards} from './mobile_cards.mjs';
import {checkDynamicsNeuroscience} from './dynamics_neuroscience.mjs';

// Painted bounds avoid mistaking font line-box centering for optical alignment.
async function visibleCenter(locator) {
  const png = await locator.screenshot();
  const ratio = await locator.page().evaluate(async src => {
    const image = new Image();
    image.src = src;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let top = canvas.height;
    let bottom = -1;
    for (let y = 0; y < canvas.height; y++) {
      for (let x = 0; x < canvas.width; x++) {
        const i = 4 * (y * canvas.width + x);
        if (pixels[i + 3] > 128 && Math.min(pixels[i], pixels[i + 1], pixels[i + 2]) < 245) {
          top = Math.min(top, y);
          bottom = Math.max(bottom, y);
        }
      }
    }
    if (bottom < 0) throw new Error('Blank brand image or title');
    return (top + bottom + 1) / (2 * canvas.height);
  }, `data:image/png;base64,${png.toString('base64')}`);
  const box = await locator.boundingBox();
  return box.y + box.height * ratio;
}

const url = process.argv[2] || pathToFileURL(path.resolve('docs/index.html')).href;
const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);
const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
const errors = [];
const fontRequests = [];
page.on('pageerror', error => errors.push(error.message));
page.on('request', request => {
  if (request.resourceType() === 'font' && !request.url().startsWith('data:')) fontRequests.push(request.url());
});
await page.addInitScript(() => { Date.now = () => Date.parse('2026-10-06T12:00:00Z'); });
// Local checks do not authenticate, create Discussions, or exercise Giscus.
await page.route('https://giscus.app/**', route => route.abort());

try {
  const output = process.env.SCREENSHOT_DIR;
  const widths = [1440, 1051, 1050, 768, 390, 320];
  if (output) await fs.mkdir(output, {recursive: true});
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  assert(await page.evaluate(() => [...document.fonts].some(font => font.family === 'Audiowide' && font.status === 'loaded')));
  assert.match(await page.locator('h1').evaluate(title => getComputedStyle(title).fontFamily), /Audiowide/);
  assert.equal(await page.locator('h1').evaluate(title => getComputedStyle(title).fontWeight), '400');
  assert.equal(await page.locator('h1').evaluate(title => getComputedStyle(title).fontSynthesis), 'none');
  assert(await page.locator('body, td').evaluateAll(elements => elements.every(element => !getComputedStyle(element).fontFamily.includes('Audiowide'))));
  assert.equal(await page.title(), 'Venue Radar | Scientific Conference Calendar');
  assert.equal(await page.locator('#tab-conferences').innerText(), 'Conferences & Map');
  assert.equal(await page.locator('.subhead').innerText(), 'Find your next conference in machine learning and AI, or explore related opportunities in neuroscience, healthcare, complex systems, and control.');
  assert(await page.locator('td[data-label="Conference"] > a').evaluateAll(names =>
    names.length > 0 && names.every(name =>
      getComputedStyle(name).fontWeight === '600' &&
      getComputedStyle(name).fontSize === getComputedStyle(name.parentElement).fontSize
    )), 'Conference names in both tables must be semibold at their existing size');
  for (const width of widths) {
    await page.setViewportSize({width, height: width > 760 ? 1000 : 844});
    await page.goto(url);
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('#filter-details').evaluate(details => details.open), width > 760, `Filter default at ${width}px`);
    assert.equal(await page.locator('#search').isVisible(), width > 760);
    assert(await page.locator('#clear-filters').isVisible());
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `Default layout must fit at ${width}px`);
    if (output) await page.screenshot({path: path.join(output, `default-filters-${width}.png`)});
  }
  await checkMobileCards(page, url, output);
  await page.locator('#filter-details > summary').click();
  assert(await page.locator('#open-only').isChecked(), 'Submission options must be selected on first load');
  assert.equal(await page.locator('[data-deadline-group]:visible').count(), 93);
  assert(await page.locator('[data-deadline-group]:visible').evaluateAll(rows =>
    rows.every(row => ['open', 'scheduled', 'opportunity', 'estimated'].includes(stateByRow.get(row).kind))));
  const repository = 'https://github.com/gon-uri/venue-radar';
  const shareLink = page.getByRole('link', {name: 'Share on X', exact: true});
  const shareUrl = new URL(await shareLink.getAttribute('href'));
  assert.equal(shareUrl.origin + shareUrl.pathname, 'https://x.com/intent/tweet');
  assert.equal(shareUrl.searchParams.get('url'), 'https://gon-uri.github.io/venue-radar/');
  assert.equal(shareUrl.searchParams.get('text'), 'Check out Venue Radar, a new conference calendar for ML, AI, neuroscience, and related fields. Search and filter submission deadlines, compare ICORE/CCF rankings, and check historical acceptance rates.');
  assert(shareUrl.searchParams.get('text').length + 24 <= 280);
  const starLink = page.getByRole('link', {name: 'Star the repo', exact: true});
  assert.equal(await starLink.getAttribute('href'), repository);
  for (const link of [shareLink, starLink]) {
    assert.equal(await link.getAttribute('target'), '_blank');
    assert.equal(await link.getAttribute('rel'), 'noopener noreferrer');
    assert.equal(await link.locator('svg').count(), 1);
  }
  const faviconUrl = await page.locator('link[rel="icon"]').getAttribute('href');
  assert(faviconUrl.startsWith('data:image/svg+xml;base64,'));
  const faviconPixels = await page.evaluate(async src => {
    const image = new Image();
    image.src = src;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 32;
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0, 32, 32);
    const pixels = context.getImageData(0, 0, 32, 32).data;
    return {corner: [...pixels.slice(0, 4)], colored: [...pixels].filter((value, i) => i % 4 !== 3 && value < 200).length};
  }, faviconUrl);
  assert.deepEqual(faviconPixels.corner, [255, 255, 255, 255]);
  assert(faviconPixels.colored > 100, 'Radar favicon must render at browser-tab size');
  assert.equal(await page.getByRole('link', {name: 'Request a conference', exact: true}).getAttribute('href'), `${repository}/issues/new?template=conference-request.yml`);
  assert.equal(await page.getByRole('link', {name: 'GitHub discussions', exact: true}).getAttribute('href'), `${repository}/discussions`);
  assert.equal(await page.getByRole('link', {name: 'Find Venue Radar useful? Star the repository', exact: true}).getAttribute('href'), repository);
  assert.equal(await page.getByRole('link', {name: 'Code: MIT', exact: true}).getAttribute('href'), `${repository}/blob/main/LICENSE`);
  assert.equal(await page.getByRole('link', {name: 'Original content: CC BY 4.0', exact: true}).getAttribute('href'), `${repository}/blob/main/CONTENT-LICENSE.md`);
  assert.equal(await page.locator('footer .author').innerText(), 'Created and maintained by Gonzalo Uribarri.');
  assert(!(await page.locator('footer').innerText()).includes('Assistant Professor'));
  assert.equal(await page.getByRole('link', {name: 'University profile', exact: true}).getAttribute('href'), 'https://www.su.se/profiles/g/gour8957');
  assert.equal(await page.getByRole('heading', {name: 'On the map', exact: true}).count(), 0);
  assert.deepEqual((await page.locator('.header-actions a').allTextContents()).map(text => text.trim()), ['Share on X', 'Star the repo', 'All events (.ics)']);
  assert(await page.locator('a[download]').evaluateAll(links => links.length > 0 && links.every(link => {
    const path = link.getAttribute('href');
    return path.endsWith('.ics') && !path.startsWith('/') && !path.includes(':');
  })), 'Calendar downloads must resolve relative to the renamed project site');
  await page.evaluate(() => loadCommunityComments());
  const commentClient = page.locator('.giscus script');
  assert.equal(await commentClient.getAttribute('data-repo'), 'gon-uri/venue-radar');
  assert.equal(await commentClient.getAttribute('data-repo-id'), 'R_kgDOTQKmZg');
  assert.equal(await commentClient.getAttribute('data-category-id'), 'DIC_kwDOTQKmZs4DHLTi');
  assert.equal(await commentClient.getAttribute('data-mapping'), 'specific');
  assert.equal(await commentClient.getAttribute('data-term'), 'Venue Radar community');
  const openStatuses = page.locator('#panel-deadlines .status-open');
  const openLabels = await openStatuses.allTextContents();
  assert(openLabels.includes('Open abstract submissions'));
  assert(openLabels.includes('Open paper submissions'));
  assert(await openStatuses.evaluateAll(labels => labels.every(label =>
    getComputedStyle(label, '::before').content === 'none' &&
    getComputedStyle(label).fontWeight === '700' &&
    getComputedStyle(label).color === 'rgb(21, 91, 45)'
  )), 'Open submission statuses must keep bold green text without leading dots');
  await checkSubmissionBehavior(page);
  const filterSummary = page.locator('#filter-details > summary');
  assert(!(await page.locator('#filter-details').evaluate(details => details.open)));
  assert(await page.locator('#clear-filters').isVisible());
  assert.equal(await filterSummary.locator('span:last-child').innerText(), 'Filters & search');
  assert.equal(await filterSummary.evaluate(summary => getComputedStyle(summary).fontSize), '20px');
  assert.equal(await filterSummary.evaluate(summary => getComputedStyle(summary).columnGap), '14px');
  assert.equal(await page.locator('.filter-disclosure-icon').evaluate(icon => getComputedStyle(icon).fontSize), '20px');
  assert.equal(await page.locator('.filter-disclosure-icon').getAttribute('aria-hidden'), 'true');
  assert.equal(await page.locator('input:not(#open-only), select').evaluateAll(controls => controls.filter(control => !control.closest('#filter-details')).length), 0);
  assert(await page.locator('#clear-filters').evaluate(button => !button.closest('#filter-details') && !!button.closest('.filter-section')));
  assert(await page.getByLabel('Show submission options only', {exact: true}).isVisible());
  assert(await page.locator('#open-only').evaluate(input => !input.closest('#filter-details') && !!input.closest('.tab-toolbar')));
  assert(Number.parseFloat(await page.locator('.open-toggle').evaluate(label => getComputedStyle(label).fontSize)) >= 15);
  assert.deepEqual(await page.locator('#open-only').evaluate(input => [input.clientWidth, input.clientHeight]), [19, 19]);
  const tabsBox = await page.locator('.table-tabs').boundingBox();
  const opportunitiesBox = await page.locator('.open-toggle').boundingBox();
  assert(opportunitiesBox.x > tabsBox.x + tabsBox.width && Math.abs(opportunitiesBox.y + opportunitiesBox.height / 2 - tabsBox.y - tabsBox.height / 2) < 1);
  await filterSummary.click();
  assert.notEqual(await page.locator('.filter-disclosure-icon').evaluate(icon => getComputedStyle(icon).transform), 'none');
  await filterSummary.focus();
  await page.keyboard.press('Enter');
  assert(!(await page.locator('#filter-details').evaluate(details => details.open)));
  await page.keyboard.press('Enter');
  assert(await page.locator('#filter-details').evaluate(details => details.open));
  assert.equal(await page.getByRole('link', {name: 'ICORE Rank', exact: true}).getAttribute('href'), 'https://portal.core.edu.au/conf-ranks/');
  const ccfPage = 'https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-31/870181.shtml';
  assert.equal(await page.getByRole('link', {name: 'CCF Rank', exact: true}).getAttribute('href'), ccfPage);
  assert(await page.locator('.rank-link-ccf').evaluateAll(links => links.every(link => link.href === 'https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-31/870181.shtml')));
  assert.equal(await page.locator('.calendar-caption').innerText(), 'Download calendar');
  assert(await page.locator('header').evaluate(header => header.querySelector('.calendar-action').getBoundingClientRect().right > header.querySelector('.brand-line').getBoundingClientRect().right));
  assert.equal(await page.locator('.brand-mark').evaluate(image => image.clientWidth), 82);
  assert.equal(await page.locator('h1').evaluate(title => getComputedStyle(title).fontSize), '42px');
  assert.notEqual(await page.locator('#tab-deadlines').evaluate(tab => getComputedStyle(tab).backgroundColor), await page.locator('#tab-conferences').evaluate(tab => getComputedStyle(tab).backgroundColor));
  assert((await page.locator('.topic-filter').boundingBox()).width <= 360);
  assert.equal(await page.locator('.topic-filter > legend').innerText(), 'Topics & Subtopics');
  assert.deepEqual(await page.locator('.topic-family summary label span').allTextContents(), [
    'ML & Data Science', 'NLP, Agents & Retrieval', 'Vision & Multimedia',
    'RL, Robotics & Control', 'Complex Systems, Time Series & Signals',
    'Healthcare & Biometrics', 'Neuroscience & Neurotechnology',
    'Responsible & Trustworthy AI',
  ]);
  assert(await page.locator('.topic-family > summary').evaluateAll(summaries => summaries.every(summary => getComputedStyle(summary).display === 'list-item' && summary.title === 'Expand or collapse subtopics')));
  assert.equal(await page.locator('#time-series-shortcut').count(), 0);
  assert(await page.locator('.topic-tree').evaluate(tree => tree.scrollHeight <= tree.clientHeight), 'All eight collapsed families must fit without scrolling');
  await page.locator('.topic-family summary').first().click({position: {x: 8, y: 10}});
  assert(await page.locator('.topic-tree').evaluate(tree => tree.scrollHeight > tree.clientHeight), 'Expanded subtopics must scroll within the box');
  await page.locator('.topic-family summary').first().click({position: {x: 8, y: 10}});
  const searchLabel = await page.locator('.search-control .control-label').boundingBox();
  const acceptanceLabel = await page.locator('.filter-group').filter({has: page.locator('[data-filter-group="acceptance"]')}).locator('legend').boundingBox();
  assert(searchLabel.x > acceptanceLabel.x + acceptanceLabel.width);
  assert(Math.abs(searchLabel.y - acceptanceLabel.y) < 1, 'Search and filter headings must align vertically');
  assert.deepEqual(await page.locator('[data-filter-group="size"]').evaluateAll(inputs => inputs.map(i => i.value)), ['s', 'm', 'l', 'xl', 'xxl']);
  assert.equal(await page.locator('#panel-deadlines .row-calendar-button').count(), 0);
  await page.locator('#search').fill('mlsys');
  await page.locator('[data-filter-group="size"][value="L" i]').check();
  await filterSummary.click();
  await page.locator('#clear-filters').click();
  assert(!(await page.locator('#filter-details').evaluate(details => details.open)), 'Clear filters must not open the collapsed panel');
  assert.equal(await page.locator('#search').inputValue(), '');
  assert.equal(await page.locator('[data-filter-group]:checked, [data-family-toggle]:checked').count(), 0);
  assert(!(await page.locator('#open-only').isChecked()), 'Clear filters removes the optional submission restriction too');
  assert(await page.locator('#clear-filters').evaluate(button => document.activeElement === button));
  await filterSummary.click();
  const sysid = page.locator('[data-deadline-group][data-edition="ifac-sysid-2027"]');
  const timeEstimate = sysid.locator('[data-label="Time left"] [data-time-estimate]');
  assert(await timeEstimate.isVisible());
  assert.equal(await timeEstimate.innerText(), '(time est.)');
  assert(!(await sysid.locator('[data-label="Next milestone"]').innerText()).includes('(time est.)'));
  assert.match(await sysid.locator('[data-deadline-row]:visible time').getAttribute('title'), /exact hour\/timezone unannounced/);
  await sysid.locator('.deadline-toggle').click();
  assert(!(await sysid.locator('[data-label="Next milestone"]').innerText()).includes('(time est.)'));
  assert(await timeEstimate.isVisible());
  await sysid.locator('.deadline-toggle').click();
  assert(!(await page.locator('[data-deadline-group][data-edition="aistats-2027"] [data-time-estimate]').isVisible()));
  assert(!(await page.locator('[data-deadline-group][data-edition="icml-2027"] [data-time-estimate]').isVisible()));
  assert((await page.locator('[data-deadline-group][data-edition="icml-2027"] [data-label="Next milestone"]').innerText()).includes('(est.)'));
  await page.evaluate(() => {
    Date.now = () => Date.parse('2027-06-01T12:00:00Z');
    applyFilters();
  });
  assert(!(await timeEstimate.isVisible()));
  assert((await sysid.locator('[data-label="Next milestone"]').innerText()).includes('Conference starts'));
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-10-06T12:00:00Z');
    applyFilters();
  });
  assert(await timeEstimate.isVisible());
  const toggle = page.locator('[data-deadline-group]:visible .deadline-toggle').first();
  await toggle.click();
  assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
  await toggle.click();
  await filterSummary.click();
  await page.locator('#open-only').check();
  for (const [date, id, expected] of [
    ['2026-10-07', 'www-2027', true],
    ['2026-10-13', 'naacl-2027', false],
    ['2026-10-13', 'coling-2027', false],
    ['2026-10-20', 'ecir-2027', true],
    ['2026-11-03', 'ecir-2027', false],
    ['2026-12-05', 'rss-2027', false],
  ]) {
    await page.evaluate(date => {
      Date.now = () => Date.parse(`${date}T12:00:00Z`);
      applyFilters();
    }, date);
    assert.equal(await page.locator(`[data-deadline-group][data-edition="${id}"]`).isVisible(), expected, `${id} eligibility on ${date}`);
  }
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-10-06T12:00:00Z');
    applyFilters();
  });
  const opportunities = await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.map(r => r.dataset.edition));
  assert(!opportunities.includes('acc-2027'));
  assert(opportunities.includes('ieee-cdc-2027'));
  assert(opportunities.includes('netsci-2027'));
  assert(opportunities.includes('aamas-2027'), 'Blue Sky Ideas remains a distinct submission opportunity');
  assert(opportunities.includes('automl-2027'));
  assert(opportunities.includes('probml-2027'));
  assert(opportunities.includes('mlsys-2027'));
  for (const id of ['corl-2026', 'log-2026', 'satml-2027', 'wacv-2027', 'bmvc-2026', '3dv-2027', 'acm-mm-2026']) assert(!opportunities.includes(id));
  for (const id of ['eurogp-2027', 'kr-2027', 'icaps-2027', 'cvpr-2027', 'eccv-2028', 'euvip-2027', 'fg-2027', 'iccv-2027', 'icmr-2027', 'ijcb-2027', 'acm-mm-2027']) assert(opportunities.includes(id));
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-07-01T12:00:00Z');
    applyFilters();
  });
  assert(await page.locator('[data-deadline-group][data-edition="wacv-2027"]').isVisible(), 'WACV round 2 survives the closed first round');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-08-23T12:00:00Z');
    applyFilters();
  });
  assert(!(await page.locator('[data-deadline-group][data-edition="wacv-2027"]').isVisible()), 'WACV round 2 enrollment gates its later paper cutoff');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-10-11T12:00:00Z');
    applyFilters();
  });
  assert.equal(await page.locator('[data-edition="mlsys-2027"] [data-submission-status]').innerText(), 'Open paper submissions');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-11-06T12:00:00Z');
    applyFilters();
  });
  assert(!(await page.locator('[data-deadline-group][data-edition="aamas-2027"]').isVisible()), 'Expired Blue Sky registration closes its paper route');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2027-02-10T12:00:00Z');
    applyFilters();
  });
  assert(await page.locator('[data-deadline-group][data-edition="interspeech-2027"]').isVisible(), 'Show & Tell remains after main papers close');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2027-03-11T12:00:00Z');
    applyFilters();
  });
  assert(!(await page.locator('[data-deadline-group][data-edition="interspeech-2027"]').isVisible()), 'Paper updates and camera-ready do not reopen submissions');
  await page.evaluate(() => {
    Date.now = () => Date.parse('2026-10-06T12:00:00Z');
    applyFilters();
  });
  await filterSummary.click();

  await page.locator('#tab-conferences').click();
  assert(!(await page.locator('#open-only').isVisible()));
  assert.equal(await page.locator('#map-count').innerText(), '107 confirmed editions in 86 cities');
  assert.equal(await page.locator('.city-marker').count(), 86);
  assert.equal(await page.locator('#panel-conferences [data-submission-status]').count(), 0);
  await page.locator('#conference-map').scrollIntoViewIfNeeded();
  const montreal = page.locator('.city-marker[title^="Montreal"]');
  await montreal.focus();
  await page.keyboard.press('Enter');
  assert.match(await page.locator('.city-popup').innerText(), /AISTATS 2027/);
  await page.locator('.leaflet-popup-close-button').click();
  await page.locator('.map-city-link').filter({hasText: 'Montreal'}).click();
  await page.locator('.leaflet-popup-close-button').click();
  await montreal.hover();
  assert.match(await page.locator('.city-popup').innerText(), /COSYNE 2027/);

  await page.locator('#clear-filters').click();

  await page.locator('#search').fill('graph kernels');
  const logConference = page.locator('#upcoming-conferences-body [data-edition="log-2026"]');
  assert(await logConference.isVisible(), 'Search must include the sourced scope summary');
  assert.equal(await logConference.locator('[data-label="Topics"] .tag').count(), 4);
  assert.equal(await page.locator('.city-marker').count(), 1, 'Scope search must also filter the map');
  await page.locator('#tab-deadlines').click();
  assert(await page.locator('[data-deadline-group][data-edition="log-2026"]').isVisible());
  await page.locator('#clear-filters').click();
  const probabilityInput = page.locator('[data-topic-family][value="probabilistic-causal-uncertainty-ml"]');
  await probabilityInput.evaluate(input => input.closest('details').open = true);
  await probabilityInput.check();
  const automlDeadline = page.locator('[data-deadline-group][data-edition="automl-2027"]');
  assert(await automlDeadline.isVisible(), 'Additional curated tags must participate in topic filtering');
  assert.equal(await automlDeadline.locator('[data-label="Topics"] .tag').count(), 4);
  assert(!(await automlDeadline.locator('[data-label="Topics"]').innerText()).includes('Probabilistic'));
  await page.locator('#tab-conferences').click();
  assert(await page.locator('#upcoming-conferences-body [data-edition="automl-2027"]').isVisible());
  await page.locator('#clear-filters').click();
  await probabilityInput.evaluate(input => input.closest('details').open = false);
  await page.locator('#search').fill('bayesian optimization');
  assert(await page.locator('#upcoming-conferences-body [data-edition="automl-2027"]').isVisible());
  await page.locator('#clear-filters').click();

  await page.locator('[data-filter-group="ccf"][value="B"]').check();
  const ccfMatches = page.locator('#upcoming-conferences-body [data-conference-row]:visible');
  assert(await ccfMatches.evaluateAll(rows => rows.length > 0 && rows.every(row => row.dataset.ccf === 'B')));
  assert((await page.locator('.city-marker').count()) > 0 && (await page.locator('.city-marker').count()) < 80);
  await page.locator('[data-filter-group="icore"][value="Unranked"]').check();
  assert(await ccfMatches.evaluateAll(rows => rows.length > 0 && rows.every(row => row.dataset.ccf === 'B' && row.dataset.icore === 'Unranked')));
  assert(await ccfMatches.evaluateAll(rows => rows.some(row => row.dataset.edition === 'icassp-2027')));
  await page.locator('#tab-deadlines').click();
  assert(await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.length > 0 && rows.every(row => row.dataset.ccf === 'B' && row.dataset.icore === 'Unranked')));
  await page.locator('#clear-filters').click();
  await page.locator('[data-filter-group="ccf"][value="Unranked"]').check();
  assert(await page.locator('[data-deadline-group]:visible').evaluateAll(rows => rows.length > 0 && rows.every(row => row.dataset.ccf === 'Unranked')));
  await page.locator('#clear-filters').click();
  await page.locator('#tab-conferences').click();
  for (const [family, topic, expected] of [
    ['ml-ai', 'evolutionary-computation-optimization', 'gecco-2027'],
    ['neuroscience', 'cognitive-science-computational-cognition', 'cogsci-2027'],
    ['ml-ai', 'ml-systems-infrastructure', 'mlsys-2027'],
    ['ml-ai', 'knowledge-representation-reasoning', 'kr-2027'],
    ['rl-control', 'planning-search', 'icaps-2027'],
    ['signals-vision', 'computer-graphics-visualization', 'acm-siggraph-2027'],
    ['signals-vision', 'multimedia-learning-retrieval', 'icmr-2027'],
    ['healthcare', 'biometrics-human-sensing', 'fg-2027'],
    ['healthcare', 'biometrics-human-sensing', 'ijcb-2027'],
    ['language-agents-retrieval', 'autonomous-agents-multiagent-systems', 'aamas-2027'],
    ['language-agents-retrieval', 'llm-agents-tool-use', 'colm-2027'],
    ['language-agents-retrieval', 'information-retrieval-search', 'sigir-2027'],
    ['language-agents-retrieval', 'recommender-systems', 'recsys-2027'],
    ['dynamics-control', 'graphs-graph-learning', 'log-2026'],
  ]) {
    const disclosure = page.locator('.topic-family').filter({has: page.locator(`[data-family-toggle="${family}"]`)});
    await disclosure.evaluate(details => details.open = true);
    await page.locator(`[data-topic-family="${family}"][value="${topic}"]`).check();
    assert(await page.locator(`#upcoming-conferences-body [data-edition="${expected}"]`).isVisible(), `${topic} must include ${expected}`);
    await page.locator('#clear-filters').click();
    await disclosure.evaluate(details => details.open = false);
  }
  const familySummary = page.locator('.topic-family summary').first();
  await familySummary.focus();
  await page.keyboard.press('Enter');
  await page.locator('[data-topic-family="ml-ai"]').first().check();
  assert(await page.locator('[data-family-toggle="ml-ai"]').evaluate(input => input.indeterminate));
  await page.locator('#clear-filters').click();
  await familySummary.focus();
  await page.keyboard.press('Enter');
  await page.locator('[data-family-toggle="dynamics-control"]').check();
  await page.locator('[data-family-toggle="ml-ai"]').check();
  await page.locator('#topic-match').selectOption('all');
  const intersection = await page.locator('#upcoming-conferences-body [data-conference-row]:visible').evaluateAll(rows => rows.map(r => r.dataset.edition));
  assert(intersection.includes('log-2026'));
  assert(!intersection.includes('l4dc-2027'));
  assert(!intersection.includes('netsci-2027'));
  await page.locator('#clear-filters').click();
  await page.locator('[data-family-toggle="ml-ai"]').check();
  assert(!(await page.locator('#upcoming-conferences-body [data-edition="miccai-2027"]').isVisible()));
  await page.locator('#clear-filters').click();
  const machineLearning = page.locator('[data-topic-family="ml-ai"][value="deep-representation-learning"]');
  await machineLearning.evaluate(input => input.closest('details').open = true);
  await machineLearning.check();
  assert(await page.locator('#upcoming-conferences-body [data-edition="miccai-2027"]').isVisible());
  await page.locator('#clear-filters').click();
  await machineLearning.evaluate(input => input.closest('details').open = false);
  const timeSeriesInput = page.locator('[data-topic-family="dynamics-control"][value="time-series-sequential-data"]');
  await timeSeriesInput.evaluate(input => input.closest('details').open = true);
  await timeSeriesInput.check();
  for (const id of ['itise-2027', 'fmts-neurips-2026', 'recsys-2027']) {
    assert(await page.locator(`#upcoming-conferences-body [data-edition="${id}"]`).isVisible());
  }
  assert(!(await page.locator('#upcoming-conferences-body [data-edition="acl-2027"]').isVisible()));
  await page.locator('#clear-filters').click();
  assert(!(await timeSeriesInput.isChecked()));
  await timeSeriesInput.evaluate(input => input.closest('details').open = false);
  await page.locator('#search').fill('no-such-conference-xyz');
  assert.equal(await page.locator('.city-marker').count(), 0);
  assert(await page.locator('#map-empty').isVisible());
  await page.locator('#clear-filters').click();

  if (output) {
    const iconPreview = await browser.newPage({viewport: {width: 200, height: 96}});
    await iconPreview.setContent(`<body style="margin:0;display:flex;align-items:center;gap:16px;background:white;height:96px;padding:0 12px;box-sizing:border-box"><img src="${faviconUrl}" width="16" height="16"><img src="${faviconUrl}" width="32" height="32"><img src="${faviconUrl}" width="64" height="64"></body>`);
    await iconPreview.locator('img').evaluateAll(images => Promise.all(images.map(image => image.decode())));
    await iconPreview.screenshot({path: path.join(output, 'favicon-sizes.png')});
    await iconPreview.close();
  }
  await page.getByRole('button', {name: 'Reset world view'}).click();
  await filterSummary.click();
  for (const width of widths) {
    await page.setViewportSize({width, height: width > 760 ? 1000 : 844});
    await page.evaluate(() => scrollTo(0, 0));
    assert.equal(await page.locator('.brand-mark').evaluate(image => image.clientWidth), width > 760 ? 82 : 66);
    assert.equal(await page.locator('h1').evaluate(title => getComputedStyle(title).fontSize), width > 760 ? '42px' : '34px');
    assert(await page.locator('.brand-line').evaluate(brand => {
      const title = brand.querySelector('h1');
      const range = document.createRange();
      range.selectNodeContents(title);
      const text = range.getBoundingClientRect();
      const container = brand.getBoundingClientRect();
      const logo = brand.querySelector('img').getBoundingClientRect();
      return text.left >= logo.right && text.right <= container.right && text.top >= container.top && text.bottom <= container.bottom;
    }), `Enlarged brand must fit at ${width}px`);
    const logoCenter = await visibleCenter(page.locator('.brand-mark'));
    const titleCenter = await visibleCenter(page.locator('h1'));
    assert(Math.abs(titleCenter - logoCenter) < 2, `Visible logo and title centers must align at ${width}px`);
    assert(await page.locator('.subhead').evaluate(subtitle => {
      const range = document.createRange();
      range.selectNodeContents(subtitle);
      const box = subtitle.getBoundingClientRect();
      const brand = document.querySelector('.brand-line').getBoundingClientRect();
      return box.top >= brand.bottom && [...range.getClientRects()].every(text =>
        text.left >= box.left && text.right <= box.right &&
        text.top >= box.top && text.bottom <= box.bottom);
    }), `Selected introduction must fit below the brand at ${width}px`);
    if (output && (width === 1440 || width === 320)) {
      await page.locator('.brand-line').screenshot({path: path.join(output, `brand-${width}.png`)});
    }
    await page.waitForFunction(() => conferenceMap.getSize().x === document.querySelector('#conference-map').clientWidth);
    await page.waitForFunction(() => conferenceMap.getBounds().getEast() - conferenceMap.getBounds().getWest() > 330);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `Map overflow at ${width}px`);
    assert(await page.locator('td[data-label="Conference"] > a:visible').evaluateAll(names => names.every(name => {
      const range = document.createRange();
      range.selectNodeContents(name);
      const cell = name.closest('td').getBoundingClientRect();
      return [...range.getClientRects()].every(text =>
        text.left >= cell.left && text.right <= cell.right &&
        text.top >= cell.top && text.bottom <= cell.bottom);
    })), `Conference table names must fit their cells at ${width}px`);
    assert(await page.locator('.leaflet-overlay-pane svg path').count() > 0);
    if (width > 760) {
      assert(await page.locator('th:visible').evaluateAll(headings => headings.every(heading => {
        const range = document.createRange();
        range.selectNodeContents(heading);
        const text = range.getBoundingClientRect();
        const cell = heading.getBoundingClientRect();
        return text.left >= cell.left - 1 && text.right <= cell.right + 1;
      })), `Conference header overlap at ${width}px`);
    }
    if (output) {
      await page.locator('#conference-map').scrollIntoViewIfNeeded();
      await page.screenshot({path: path.join(output, `map-${width}.png`)});
    }
    await page.locator('#tab-deadlines').click();
    await page.locator('#open-only').check();
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `Deadline overflow at ${width}px`);
    assert(await page.locator('td[data-label="Conference"] > a:visible').evaluateAll(names => names.every(name => {
      const range = document.createRange();
      range.selectNodeContents(name);
      const cell = name.closest('td').getBoundingClientRect();
      return [...range.getClientRects()].every(text =>
        text.left >= cell.left && text.right <= cell.right &&
        text.top >= cell.top && text.bottom <= cell.bottom);
    })), `Deadline table names must fit their cells at ${width}px`);
    assert(await timeEstimate.isVisible());
    assert(await timeEstimate.evaluate(note => {
      const range = document.createRange();
      range.selectNodeContents(note);
      const text = range.getBoundingClientRect();
      const cell = note.closest('td').getBoundingClientRect();
      return text.left >= cell.left && text.right <= cell.right;
    }), `Time estimate must fit its cell at ${width}px`);
    if (width > 760) {
      assert(await page.locator('th:visible').evaluateAll(headings => headings.every(heading => {
        const range = document.createRange();
        range.selectNodeContents(heading);
        const text = range.getBoundingClientRect();
        const cell = heading.getBoundingClientRect();
        return text.left >= cell.left - 1 && text.right <= cell.right + 1;
      })), `Deadline header overlap at ${width}px`);
    }
    if (output) {
      if (width === 1440) {
        await page.locator('[data-deadline-group][data-edition="cosyne-2027"]').screenshot({path: path.join(output, 'open-abstract-status.png')});
        await page.locator('[data-deadline-group][data-edition="isbi-2027"]').screenshot({path: path.join(output, 'open-paper-status.png')});
        for (const id of ['aamas-2027', 'mlsys-2027', 'ida-2027']) {
          await page.locator(`[data-deadline-group][data-edition="${id}"]`).screenshot({path: path.join(output, `submission-${id}.png`)});
        }
      }
      if (width === 1440 || width === 320) await sysid.screenshot({path: path.join(output, `time-estimate-${width}.png`)});
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({path: path.join(output, `deadlines-${width}.png`)});
    }
    await page.locator('#open-only').uncheck();
    assert(!(await page.locator('#filter-details').evaluate(details => details.open)));
    assert(await page.locator('#open-only').isVisible());
    assert(await page.locator('#clear-filters').isVisible());
    await filterSummary.click();
    assert(await page.locator('#clear-filters').isVisible());
    assert(await page.locator('.topic-family summary label span').evaluateAll(labels => labels.every(label => {
      const range = document.createRange();
      range.selectNodeContents(label);
      const rects = [...range.getClientRects()];
      const family = label.closest('summary').getBoundingClientRect();
      return rects.length === 1 && rects[0].right <= family.right - 8;
    })), `Topic family labels must fit on one line at ${width}px`);
    const headingBox = await filterSummary.boundingBox();
    const clearBox = await page.locator('#clear-filters').boundingBox();
    assert(Math.abs(headingBox.y + headingBox.height / 2 - clearBox.y - clearBox.height / 2) < 1, `Disclosure and Clear filters must align at ${width}px`);
    assert(headingBox.x + headingBox.width < clearBox.x, `Clear filters must not overlap the heading at ${width}px`);
    assert(await page.locator('.topic-tree').evaluate(tree => tree.scrollHeight <= tree.clientHeight), `All eight collapsed families must fit at ${width}px`);
    assert(await page.locator('.header-actions a').evaluateAll(links => links.every(link => {
      const box = link.getBoundingClientRect();
      return box.left >= 0 && box.right <= innerWidth;
    })), `Header actions must fit at ${width}px`);
    assert(await page.locator('.calendar-action').evaluate(action => {
      const button = action.querySelector('a').getBoundingClientRect();
      const caption = action.querySelector('span').getBoundingClientRect();
      return caption.top >= button.bottom && caption.left >= button.left && caption.right <= button.right;
    }), `Download caption must fit below its button at ${width}px`);
    assert(await page.locator('.header-actions').evaluate(actions => {
      const links = [...actions.querySelectorAll('a')].map(link => link.getBoundingClientRect());
      return links.at(-1).right >= Math.max(...links.map(link => link.right)) - 1 &&
        (innerWidth <= 760 || links.every(link => Math.abs(link.top - links[0].top) < 1));
    }), `Download must be rightmost and desktop buttons aligned at ${width}px`);
    assert(await page.locator('.table-tabs button').evaluateAll(tabs => tabs.every(tab => {
      const range = document.createRange();
      range.selectNodeContents(tab);
      const text = range.getBoundingClientRect();
      const box = tab.getBoundingClientRect();
      return text.left >= box.left && text.right <= box.right && text.top >= box.top && text.bottom <= box.bottom;
    })), `Tab labels must fit at ${width}px`);
    if (output) await page.locator('header').screenshot({path: path.join(output, `header-${width}.png`)});
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), `Expanded filter overflow at ${width}px`);
    if (width > 760) {
      const searchBox = await page.locator('.search-control .control-label').boundingBox();
      const rateBox = await page.locator('.filter-group').filter({has: page.locator('[data-filter-group="acceptance"]')}).locator('legend').boundingBox();
      assert(searchBox.x > rateBox.x + rateBox.width && Math.abs(searchBox.y - rateBox.y) < 1, `Search alignment at ${width}px`);
    }
    if (output) await page.screenshot({path: path.join(output, `filters-${width}.png`)});
    await filterSummary.click();
    await page.locator('#tab-conferences').click();
  }
  await checkDynamicsNeuroscience(page);
  assert.deepEqual(fontRequests, [], 'The title font must not require a network request');
  assert.deepEqual(errors, []);
  console.log(`Browser smoke passed: ${opportunities.length} opportunities, ${intersection.length} cross-family matches; ${widths.join('/')}px.`);
} finally {
  await browser.close();
}
