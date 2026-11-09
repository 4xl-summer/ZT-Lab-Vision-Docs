// npm install --prefix manual-next/tools/visuals
// node manual-next/scripts/render_infographics.cjs [diagram-id ...]
'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const { createRequire } = require('node:module');
const root = path.resolve(__dirname, '..');
const localRequire = createRequire(path.join(root, 'tools/visuals/package.json'));
const { renderToString } = localRequire('@antv/infographic/ssr');
(async () => {
  const manifest = JSON.parse(await fs.readFile(path.join(root, 'assets/visuals/manifest.json'), 'utf8'));
  const requested = process.argv.slice(2);
  const diagrams = manifest.diagrams.filter(d => d.kind === 'infographic');
  for (const id of requested) if (!diagrams.some(d => d.id === id)) throw new Error('Unknown diagram: ' + id);
  for (const diagram of diagrams.filter(d => !requested.length || requested.includes(d.id))) {
    let svg = await renderToString(diagram.syntax, { width: 1200, height: 680, padding: 32 });
    svg = svg.replace(/<\?xml-stylesheet.*?\?>\s*/g, '').replace('font-family="Alibaba PuHuiTi"', 'font-family="Segoe UI, Malgun Gothic, Noto Sans KR, Arial, sans-serif"');
    await fs.writeFile(path.join(root, diagram.image), svg, 'utf8');
    console.log(diagram.id);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
