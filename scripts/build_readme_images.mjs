// Render the README screenshots from the committed page (docs/index.html).
// Optional maintainer tool, like build_social_card.mjs: it needs Playwright and
// an existing browser, makes no network requests, and pins the page clock to
// noon UTC on data/metadata.yml's last_updated day so reruns on the same data
// match. Run it after a release build when the README should show newer data.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const root = path.resolve(process.argv[2] || '.');
const outDir = path.join(root, 'assets/readme');
const pageUrl = pathToFileURL(path.join(root, 'docs/index.html')).href;
const metadata = await fs.readFile(path.join(root, 'data/metadata.yml'), 'utf8');
const day = metadata.match(/^last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?/m)?.[1];
assert(day, 'data/metadata.yml needs last_updated');
const now = Date.parse(`${day}T12:00:00Z`);
const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);

async function openSite(viewport, deviceScaleFactor, mobile = false) {
  const context = await browser.newContext({
    viewport, deviceScaleFactor, isMobile: mobile, hasTouch: mobile,
    locale: 'en-GB', timezoneId: 'Europe/Stockholm',
  });
  const page = await context.newPage();
  await page.addInitScript(fixed => { Date.now = () => fixed; }, now);
  await page.route(/^https?:/, route => route.abort());  // Giscus and outbound links
  await page.goto(pageUrl);
  await page.waitForFunction(() => document.querySelector('[data-filter-row]'));
  // Show results first: the filter panel is open by default.
  await page.evaluate(() => { document.querySelector('#filter-details').open = false; });
  await page.waitForTimeout(300);
  return page;
}

// Both README images sit on the same light-teal card, so they read as
// deliberate panels in GitHub's dark theme too.
const CARD = `html, body {margin: 0; background: transparent;}
  .card {position: relative; box-sizing: border-box; overflow: hidden; border-radius: 28px;
    background: linear-gradient(135deg, #e3f2f3 0%, #f6fbfb 55%, #fdf1f1 100%);}
  .shot {display: block; background: #fff; border: 1px solid #c9dadb; overflow: hidden;
    box-shadow: 0 24px 60px rgba(14, 93, 98, .18), 0 2px 8px rgba(38, 50, 56, .08);}`;
const src = png => `data:image/png;base64,${png.toString('base64')}`;

async function renderCard(html, width, height) {
  const stage = await browser.newPage({viewport: {width, height}, deviceScaleFactor: 2});
  await stage.route(/^https?:/, route => route.abort());
  await stage.setContent(`<!doctype html><html lang="en"><head><meta charset="utf-8"><style>${CARD}</style></head>
    <body><div class="card" style="width:${width}px;height:${height}px">${html}</div></body></html>`);
  await stage.evaluate(() => Promise.all([...document.images].map(image => image.decode())));
  const png = await stage.locator('.card').screenshot({omitBackground: true});
  return {stage, png};
}

// Re-encode a PNG screenshot as WebP in the browser (no image dependency).
async function writeWebp(page, png, name, quality) {
  const data = await page.evaluate(async ({source, q}) => {
    const image = new Image();
    image.src = source;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    canvas.getContext('2d').drawImage(image, 0, 0);
    return canvas.toDataURL('image/webp', q);
  }, {source: src(png), q: quality});
  assert(data.startsWith('data:image/webp;base64,'), 'this browser cannot encode WebP');
  const file = path.join(outDir, name);
  await fs.writeFile(file, Buffer.from(data.split(',')[1], 'base64'));
  console.log(`Generated ${path.relative(root, file)}`);
}

try {
  await fs.mkdir(outDir, {recursive: true});

  // Desktop: the deadline table at a common laptop width, cut at the bottom of
  // the last row that fits so no row is sliced in half.
  const desktop = await openSite({width: 1280, height: 800}, 2);
  const desktopHeight = await desktop.evaluate(() => {
    const bottoms = [...document.querySelectorAll('tr[data-filter-row]')]
      .filter(row => row.offsetParent).map(row => row.getBoundingClientRect().bottom)
      .filter(bottom => bottom <= innerHeight);
    return Math.ceil(Math.max(...bottoms));
  });
  assert(desktopHeight > 400, 'expected deadline rows in the first desktop screen');
  const desktopPng = await desktop.screenshot({clip: {x: 0, y: 0, width: 1280, height: desktopHeight}});

  // Phone: compact cards, as on a 390px-wide phone.
  const phone = await openSite({width: 390, height: 844}, 3, true);
  const phonePng = await phone.screenshot();

  // Map: Conferences & Map at a narrower desktop width (a taller world), without
  // the zoom/reset buttons, which do nothing in a picture. Attribution stays.
  const atlas = await openSite({width: 1000, height: 700}, 2);
  await atlas.click('#tab-conferences');
  await atlas.waitForFunction(() => document.querySelectorAll('#conference-map .leaflet-marker-icon, #conference-map path.leaflet-interactive').length > 0);
  await atlas.addStyleTag({content: '#conference-map .leaflet-top { display: none; }'});
  await atlas.evaluate(() => document.querySelector('#conference-map').scrollIntoView({block: 'center'}));
  await atlas.waitForTimeout(500);
  const mapPng = await atlas.locator('#conference-map').screenshot();
  const mapBox = await atlas.locator('#conference-map').boundingBox();

  // Hero: the desktop table in a browser frame with the phone in front.
  const hero = await renderCard(`<style>
      .window {position: absolute; left: 40px; top: 40px; width: 960px; border-radius: 14px;}
      .bar {height: 34px; display: flex; align-items: center; gap: 7px; padding: 0 14px; background: #f3f7f7; border-bottom: 1px solid #dfe9ea;}
      .dot {width: 11px; height: 11px; border-radius: 50%; background: #d4dfe0;}
      .url {margin-left: 14px; flex: 1; max-width: 360px; height: 20px; border-radius: 10px; background: #fff; border: 1px solid #dfe9ea;
        font: 500 11px/20px -apple-system, "Segoe UI", system-ui, sans-serif; color: #5b6b70; padding-left: 12px;}
      .window img {display: block; width: 960px;}
      .phone {position: absolute; right: 40px; top: 168px; width: 228px; padding: 8px; border-radius: 38px; background: #263238;
        box-shadow: 0 30px 70px rgba(38, 50, 56, .32), 0 3px 10px rgba(38, 50, 56, .18);}
      .phone img {display: block; width: 228px; border-radius: 31px;}
    </style>
    <div class="window shot"><div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
      <span class="url">gon-uri.github.io/venue-radar</span></div><img src="${src(desktopPng)}" alt=""></div>
    <div class="phone"><img src="${src(phonePng)}" alt=""></div>`,
  // Window: 40px top + 34px bar + the screenshot at 960/1280; the phone ends near 677px.
  1200, Math.max(720, Math.ceil(40 + 34 + desktopHeight * 0.75 + 40)));

  // Map card: same background and frame, at the map's own aspect ratio.
  const mapWidth = 1120;
  const mapHeight = Math.round(mapWidth * mapBox.height / mapBox.width);
  const atlasCard = await renderCard(`<style>
      .shot {position: absolute; left: 40px; top: 36px; width: ${mapWidth}px; border-radius: 14px;}
      .shot img {display: block; width: ${mapWidth}px;}
    </style><div class="shot"><img src="${src(mapPng)}" alt=""></div>`, 1200, mapHeight + 72);

  await writeWebp(hero.stage, hero.png, 'hero.webp', 0.9);
  await writeWebp(atlasCard.stage, atlasCard.png, 'map.webp', 0.9);
} finally {
  await browser.close();
}
