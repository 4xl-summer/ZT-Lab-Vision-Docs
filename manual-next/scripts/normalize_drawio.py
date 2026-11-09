"""Keep exported draw.io images readable inside both manual themes."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'assets/visuals/manifest.json').read_text(encoding='utf-8'))
for diagram in manifest['diagrams']:
    if diagram['kind']!='drawio':continue
    path=root/diagram['image'];svg=path.read_text(encoding='utf-8')
    svg=re.sub(r'color-scheme:\s*light dark','color-scheme: light; --ge-adaptive-fg: #17324d; --ge-adaptive-bg: #ffffff',svg)
    svg=svg.replace('background: transparent; background-color: transparent;','background: #ffffff; background-color: #ffffff;')
    path.write_text(svg,encoding='utf-8')
    print(diagram['id'])
