// Render the README banners from the current logo and the real Audiowide font:
// the white banner, and a transparent dark-mode banner whose logo swaps only
// the border color and leaves the calendar interior see-through. Optional
// maintainer tool; it needs Playwright and an existing browser.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import zlib from 'node:zlib';
import {chromium} from 'playwright';

const root = path.resolve(process.argv[2] || '.');
const logoFile = await fs.readFile(path.join(root, 'assets/venue-radar.png'));
const font = (await fs.readFile(path.join(root, 'assets/vendor/audiowide-latin.woff2'))).toString('base64');
const PALETTE = {border: '38,50,56', blue: '56,166,176', red: '200,92,98', white: '255,255,255'};
const DARK_TEXT = [230, 237, 243];  // #E6EDF3, GitHub's dark-theme text color

// Minimal 8-bit RGBA PNG reader/writer (zlib only), so pixels are exact.
function decodePng(buffer) {
  let offset = 8, width, height, header;
  const data = [];
  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('ascii', offset + 4, offset + 8);
    const body = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') header = body;
    if (type === 'IDAT') data.push(body);
    offset += 12 + length;
  }
  width = header.readUInt32BE(0);
  height = header.readUInt32BE(4);
  assert.deepEqual([...header.subarray(8, 13)], [8, 6, 0, 0, 0], 'logo must be 8-bit RGBA, not interlaced');
  const raw = zlib.inflateSync(Buffer.concat(data));
  const stride = width * 4;
  const pixels = Buffer.alloc(stride * height);
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let x = 0; x < stride; x++) {
      const a = x >= 4 ? pixels[y * stride + x - 4] : 0;
      const b = y ? pixels[(y - 1) * stride + x] : 0;
      const c = x >= 4 && y ? pixels[(y - 1) * stride + x - 4] : 0;
      const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      const predictor = [0, a, b, (a + b) >> 1, pa <= pb && pa <= pc ? a : pb <= pc ? b : c][filter];
      pixels[y * stride + x] = (line[x] + predictor) & 255;
    }
  }
  return {width, height, pixels};
}

function encodePng({width, height, pixels}) {
  const chunk = (type, body) => {
    const head = Buffer.alloc(8);
    head.writeUInt32BE(body.length);
    head.write(type, 4, 'ascii');
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(zlib.crc32(Buffer.concat([head.subarray(4), body])) >>> 0);
    return Buffer.concat([head, body, crc]);
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width);
  header.writeUInt32BE(height, 4);
  header.set([8, 6, 0, 0, 0], 8);
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) pixels.copy(raw, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', header),
    chunk('IDAT', zlib.deflateSync(raw, {level: 9})), chunk('IEND', Buffer.alloc(0))]);
}

// Dark logo: border -> light text color; white interior (added by
// recolor_logo.mjs) -> transparent, as in the source; alpha otherwise unchanged.
const mark = decodePng(logoFile);
const darkPixels = Buffer.from(mark.pixels);
const darkColors = new Set();
for (let i = 0; i < darkPixels.length; i += 4) {
  if (!darkPixels[i + 3]) continue;
  const rgb = [...darkPixels.subarray(i, i + 3)].join(',');
  assert(Object.values(PALETTE).includes(rgb), `logo pixel outside the four brand colors: ${rgb}`);
  if (rgb === PALETTE.white) {
    assert.equal(darkPixels[i + 3], 255, 'the white interior is opaque');
    darkPixels.set([0, 0, 0, 0], i);
    continue;
  }
  if (rgb === PALETTE.border) darkPixels.set(DARK_TEXT, i);
  darkColors.add([...darkPixels.subarray(i, i + 3)].join(','));
  assert.equal(darkPixels[i + 3], mark.pixels[i + 3], 'foreground alpha must stay unchanged');
}
assert.deepEqual([...darkColors].sort(), [DARK_TEXT.join(','), PALETTE.blue, PALETTE.red].sort());
const darkLogo = encodePng({...mark, pixels: darkPixels});

const launch = {headless: true};
if (process.env.CHROME_BIN) launch.executablePath = process.env.CHROME_BIN;
const browser = await chromium.launch(launch);

async function renderBanner({logo, background, color, output}) {
  const page = await browser.newPage({viewport: {width: 1400, height: 175}});
  await page.route('**/*', route => route.abort());
  await page.setContent(`<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><style>
      @font-face {font-family: Audiowide; font-weight: 400; font-style: normal;
        src: url(data:font/woff2;base64,${font}) format('woff2');}
      html {background: ${background};}
      body {margin: 0; background: ${background}; color: ${color};}
      .brand {display: flex; align-items: center; gap: 19.5px; padding: 26px;
        width: 1400px; height: 175px; box-sizing: border-box;}
      img {width: 123px; height: 123px; object-fit: contain; flex: 0 0 auto;}
      h1 {margin: 0; font-family: Audiowide, sans-serif; font-size: 63px;
        font-weight: 400; font-synthesis: none; line-height: 1.15;
        letter-spacing: 0; transform: translateY(3px);}
    </style></head><body><div class="brand">
      <img src="data:image/png;base64,${logo.toString('base64')}" alt="">
      <h1>Venue Radar</h1>
    </div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  assert(await page.evaluate(() => [...document.fonts].some(face => face.family === 'Audiowide' && face.status === 'loaded')));
  assert(await page.locator('img').evaluate(image => image.complete && image.naturalWidth === 256));
  assert(await page.locator('h1').evaluate(title => title.scrollWidth <= title.clientWidth));
  const file = path.join(root, output);
  await fs.mkdir(path.dirname(file), {recursive: true});
  await page.screenshot({path: file, omitBackground: background === 'transparent'});
  await page.close();
  console.log(`Generated ${file}`);
}

try {
  await renderBanner({logo: logoFile, background: '#fff', color: '#263238',
    output: 'assets/branding/venue-radar-banner.png'});
  await renderBanner({logo: darkLogo, background: 'transparent', color: '#e6edf3',
    output: 'assets/branding/venue-radar-banner-dark.png'});
} finally {
  await browser.close();
}
