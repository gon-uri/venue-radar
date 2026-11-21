// Render the README banners from the Ping tile mark (assets/venue-radar.svg)
// and the embedded Sora font (ADR-057): a white banner, and a transparent
// banner for GitHub's dark themes whose ripples are cut in GitHub's dark
// canvas colour. Optional maintainer tool; it needs Playwright and an
// existing browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';

const root = path.resolve(process.argv[2] || '.');
const mark = await fs.readFile(path.join(root, 'assets/venue-radar.svg'), 'utf8');
const sora = (await fs.readFile(path.join(root, 'assets/vendor/sora-latin-600.woff2'))).toString('base64');
const GITHUB_DARK_CANVAS = '#0d1117';

const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);

async function renderBanner({background, cut, tile, blip, color, output}) {
  // A taller viewport plus a clip avoids headless Chrome's short-viewport artefacts.
  const page = await browser.newPage({viewport: {width: 1400, height: 400}});
  await page.route('**/*', route => route.abort());
  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><style>
      @font-face {font-family: Sora; font-weight: 600; src: url(data:font/woff2;base64,${sora}) format('woff2');}
      :root {--bg: ${cut}; --mark-tile: ${tile}; --mark-blip: ${blip};}
      html, body {margin: 0; background: ${background}; color: ${color};}
      .brand {display: flex; align-items: center; gap: 28px; padding: 26px 30px;
        width: 1400px; height: 175px; box-sizing: border-box;}
      svg {width: 104px; height: 104px; flex: 0 0 auto;}
      h1 {margin: 0; font-family: Sora, sans-serif; font-size: 72px; font-weight: 600;
        font-synthesis: none; letter-spacing: -0.02em; line-height: 1.1;}
    </style></head><body><div class="brand">${mark}<h1>Venue Radar</h1></div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  assert(await page.evaluate(() => [...document.fonts].some(face => face.family === 'Sora' && face.status === 'loaded')));
  assert(await page.locator('h1').evaluate(title => title.scrollWidth <= title.clientWidth));
  const file = path.join(root, output);
  await fs.mkdir(path.dirname(file), {recursive: true});
  await page.screenshot({path: file, clip: {x: 0, y: 0, width: 1400, height: 175}, omitBackground: background === 'transparent'});
  await page.close();
  console.log(`Generated ${file}`);
}

try {
  await renderBanner({background: '#ffffff', cut: '#ffffff', tile: '#0d6064', blip: '#c85c62', color: '#18252a',
    output: 'assets/branding/venue-radar-banner.png'});
  await renderBanner({background: 'transparent', cut: GITHUB_DARK_CANVAS, tile: '#22989d', blip: '#e8787d', color: '#e6edf3',
    output: 'assets/branding/venue-radar-banner-dark.png'});
} finally {
  await browser.close();
}
