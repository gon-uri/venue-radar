// Render the 1200x630 link-preview card (Open Graph / X) from the Ping tile
// mark (assets/venue-radar.svg) with the embedded Sora and Inter fonts
// (ADR-057). Optional maintainer tool, like build_readme_banner.mjs; it needs
// Playwright and an existing browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';

const root = path.resolve(process.argv[2] || '.');
const mark = await fs.readFile(path.join(root, 'assets/venue-radar.svg'), 'utf8');
const font = async name => (await fs.readFile(path.join(root, `assets/vendor/${name}.woff2`))).toString('base64');
const [sora, inter] = await Promise.all([font('sora-latin-600'), font('inter-latin-wght')]);
const output = path.join(root, 'assets/branding/social-card.png');
const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);

try {
  const page = await browser.newPage({viewport: {width: 1200, height: 630}});
  await page.route('**/*', route => route.abort());
  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><style>
      @font-face {font-family: Sora; font-weight: 600; src: url(data:font/woff2;base64,${sora}) format('woff2');}
      @font-face {font-family: Inter; font-weight: 100 900; src: url(data:font/woff2;base64,${inter}) format('woff2');}
      :root {--bg: #f7fbfb; --mark-tile: #0d6064; --mark-blip: #c85c62;}
      body {margin: 0; background: var(--bg); color: #18252a; font-family: Inter, system-ui, sans-serif;}
      .card {box-sizing: border-box; width: 1200px; height: 630px; padding: 70px 80px;
        display: flex; flex-direction: column; justify-content: center; gap: 36px;}
      .brand {display: flex; align-items: center; gap: 30px;}
      svg {width: 132px; height: 132px; flex: 0 0 auto;}
      h1 {margin: 0; font-family: Sora, sans-serif; font-size: 88px; font-weight: 600;
        font-synthesis: none; letter-spacing: -0.02em; line-height: 1.05;}
      p {margin: 0; max-width: 980px; font-size: 36px; line-height: 1.35; color: #546369;}
      .chips {display: flex; gap: 14px; flex-wrap: wrap;}
      .chip {display: inline-flex; align-items: center; gap: 12px; padding: 9px 18px; border-radius: 8px;
        font-size: 26px; font-weight: 600; border: 2px solid transparent;}
      .chip::before {content: ""; width: 14px; height: 14px; border-radius: 50%; box-sizing: border-box;}
      .open {background: #dff7eb; color: #106f4c;} .open::before {background: #1a9064;}
      .est {color: #106f4c; border: 2px dashed #106f4c;} .est::before {border: 2.5px dashed currentColor;}
      .feed {background: #eef9fa; color: #0d6064;} .feed::before {background: #0d6064; border-radius: 3px;}
    </style></head><body><div class="card">
      <div class="brand">${mark}<h1>Venue Radar</h1></div>
      <p>Conference deadlines for machine learning, AI, neuroscience, healthcare, complex systems and control.</p>
      <div class="chips"><span class="chip open">Live countdowns</span><span class="chip est">Honest estimates</span>
        <span class="chip feed">Auto-updating calendars</span></div>
    </div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  for (const family of ['Sora', 'Inter']) {
    assert(await page.evaluate(name => [...document.fonts].some(face => face.family === name && face.status === 'loaded'), family));
  }
  assert(await page.locator('.card').evaluate(card => card.scrollHeight <= 630 && card.scrollWidth <= 1200));
  await fs.mkdir(path.dirname(output), {recursive: true});
  await page.screenshot({path: output});
  console.log(`Generated ${output}`);
} finally {
  await browser.close();
}
