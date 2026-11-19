// Renders branding/source/logo.svg into every PNG size Chromium's Windows
// build needs, plus the "logo + Bastion" wordmark images.
//
// Usage: node branding/render.js
// Requires: Playwright with Chromium (npm i playwright && npx playwright install chromium)
// Output: branding/generated/*.png  (then run: python branding/make_ico.py)

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = __dirname;
const OUT = path.join(ROOT, 'generated');
const svg = fs.readFileSync(path.join(ROOT, 'source', 'logo.svg'), 'utf8');
const svgDataUrl = 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');

const LOGO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 176, 256, 512, 600];

const WORDMARKS = [
  // name, width, height, text color
  ['product_logo_name_22', 97, 22, '#1F2933'],
  ['product_logo_name_22_white', 97, 22, '#FFFFFF'],
  ['product_logo_name_22@2x', 194, 44, '#1F2933'],
  ['product_logo_name_22_white@2x', 194, 44, '#FFFFFF'],
];

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });

  for (const size of LOGO_SIZES) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(
      `<html><body style="margin:0;background:transparent">` +
      `<img src="${svgDataUrl}" width="${size}" height="${size}" style="display:block"></body></html>`);
    await page.locator('img').screenshot({
      path: path.join(OUT, `logo_${size}.png`), omitBackground: true });
  }

  for (const [name, w, h, color] of WORDMARKS) {
    await page.setViewportSize({ width: w, height: h });
    const fontPx = Math.round(h * 0.68);
    await page.setContent(`
      <html><body style="margin:0;background:transparent">
      <div id="m" style="width:${w}px;height:${h}px;display:flex;align-items:center;gap:${Math.round(h * 0.18)}px;
                          font-family:'Inter','Segoe UI',sans-serif;font-weight:600;font-size:${fontPx}px;
                          letter-spacing:0.01em;color:${color};white-space:nowrap">
        <img src="${svgDataUrl}" width="${h}" height="${h}">
        <span>Bastion</span>
      </div></body></html>`);
    await page.locator('#m').screenshot({ path: path.join(OUT, `${name}.png`), omitBackground: true });
  }

  await browser.close();
  console.log('Rendered PNGs into', OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
