// Render the 1200x630 link-preview card (Open Graph / X) from the immutable
// logo and the real Audiowide font. Optional maintainer tool, like
// build_readme_banner.mjs; it needs Playwright and an existing browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';

const root = path.resolve(process.argv[2] || '.');
const logo = (await fs.readFile(path.join(root, 'assets/venue-radar.png'))).toString('base64');
const font = (await fs.readFile(path.join(root, 'assets/vendor/audiowide-latin.woff2'))).toString('base64');
const output = path.join(root, 'assets/branding/social-card.png');
const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);

try {
  const page = await browser.newPage({viewport: {width: 1200, height: 630}});
  await page.route('**/*', route => route.abort());
  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><style>
      @font-face {font-family: Audiowide; font-weight: 400; font-style: normal;
        src: url(data:font/woff2;base64,${font}) format('woff2');}
      body {margin: 0; background: #fff; color: #263238; font-family: Inter, "Segoe UI", system-ui, sans-serif;}
      .card {box-sizing: border-box; width: 1200px; height: 630px; padding: 70px 80px;
        display: flex; flex-direction: column; justify-content: center; gap: 34px;
}
      .brand {display: flex; align-items: center; gap: 26px;}
      img {width: 150px; height: 150px; object-fit: contain;}
      h1 {margin: 0; font-family: Audiowide, sans-serif; font-size: 84px; font-weight: 400;
        font-synthesis: none; line-height: 1.1; transform: translateY(4px);}
      p {margin: 0; max-width: 980px; font-size: 36px; line-height: 1.35; color: #3f4f54;}
      .chips {display: flex; gap: 14px; flex-wrap: wrap;}
      .chip {padding: 8px 16px; border-radius: 8px; font-size: 26px; font-weight: 700;}
      .open {background: #d8efdd; color: #155b2d;}
      .est {background: #fff3d7; color: #765321;}
      .feed {background: #edf5f5; color: #0e5d62;}
    </style></head><body><div class="card">
      <div class="brand"><img src="data:image/png;base64,${logo}" alt=""><h1>Venue Radar</h1></div>
      <p>Conference deadlines for machine learning, AI, neuroscience, healthcare, complex systems and control.</p>
      <div class="chips"><span class="chip open">Live countdowns</span><span class="chip est">Honest estimates</span>
        <span class="chip feed">Auto-updating calendars</span></div>
    </div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  assert(await page.evaluate(() => [...document.fonts].some(face => face.family === 'Audiowide' && face.status === 'loaded')));
  assert(await page.locator('.card').evaluate(card => card.scrollHeight <= 630 && card.scrollWidth <= 1200));
  await fs.mkdir(path.dirname(output), {recursive: true});
  await page.screenshot({path: output});
  console.log(`Generated ${output}`);
} finally {
  await browser.close();
}
