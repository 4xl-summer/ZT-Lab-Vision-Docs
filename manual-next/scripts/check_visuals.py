"""Check recorded real-image runs, figure sources and referenced assets."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib, json, math, re, struct, sys

root = Path(__file__).resolve().parents[1]
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
manifest = read(root / 'assets/visuals/manifest.json')
data = read(root / 'assets/measurement/measurements.json')
receipt = read(root / 'content/visual-verification.json')
pages = {p['path']: p for p in read(root / 'content/pages.json')}
errors = []

def fail(message):
    errors.append(message)

def re_has_table(value):
    return bool(re.search(r'<table(?:\s|>)', value, re.IGNORECASE))

def dimensions(path):
    blob = path.read_bytes()
    if len(blob) < 24 or blob[:8] != b'\x89PNG\r\n\x1a\n' or blob[12:16] != b'IHDR':
        raise ValueError('Expected PNG with IHDR ' + str(path))
    width, height = struct.unpack('>II', blob[16:24])
    if not width or not height:
        raise ValueError('Invalid PNG dimensions ' + str(path))
    return width, height

def check_svg(path, ident):
    try:
        svg = ET.parse(path).getroot()
        if not svg.tag.endswith('svg'):
            fail(ident + ': invalid SVG root')
        if any(e.tag.endswith('script') for e in svg.iter()):
            fail(ident + ': script in static SVG')
        if '<?xml-stylesheet' in path.read_text(encoding='utf-8'):
            fail(ident + ': external font stylesheet in static SVG')
    except (OSError, ET.ParseError, UnicodeError) as exc:
        fail(ident + ': cannot parse SVG: ' + str(exc))

def check_drawio(path, ident):
    try:
        xml = ET.parse(path)
        cells = list(xml.iter('mxCell'))
        ids = {e.attrib['id'] for e in cells if 'id' in e.attrib}
        if not cells or len(ids) != len(cells):
            fail(ident + ': invalid or duplicate editable cell IDs')
        for edge in cells:
            if edge.attrib.get('edge') == '1' and (
                edge.attrib.get('source') not in ids or edge.attrib.get('target') not in ids
            ):
                fail(ident + ': broken editable connector')
    except (OSError, ET.ParseError) as exc:
        fail(ident + ': cannot parse draw.io source: ' + str(exc))

# Legacy Infographic assets and the discarded generic layout must not remain
# active in the current manifest or page bodies. Archived files are not scanned.
def check_legacy(value, where):
    if isinstance(value, str):
        normalized = value.replace('\\', '/')
        if 'assets/visuals/infographic/' in normalized:
            fail(where + ': active legacy infographic reference')
        if 'list-row-simple-horizontal-arrow' in normalized:
            fail(where + ': discarded generic arrow template')
    elif isinstance(value, dict):
        for key, item in value.items():
            check_legacy(item, where + '.' + str(key))
    elif isinstance(value, list):
        for item in value:
            check_legacy(item, where)

check_legacy(manifest, 'manifest')
for path, page in pages.items():
    check_legacy(page.get('body', ''), path)

expected_representation = {
    'concept': 'diagram', 'plot': 'plot', 'table': 'table',
    'reuse': 'reuse', 'drawio': 'drawio',
}
for d in manifest['diagrams']:
    ident = d['id']
    kind = d.get('kind')
    if kind not in expected_representation:
        fail(ident + ': unsupported visual kind ' + str(kind))
        continue
    if d.get('representation') != expected_representation[kind]:
        fail(ident + ': representation does not match kind')
    if not isinstance(d.get('renderer'), str) or not d['renderer'].strip():
        fail(ident + ': missing renderer')
    for key in ('source', 'page'):
        if not d.get(key) or not (root / d[key]).is_file():
            fail(ident + ': missing ' + key)
    if d.get('page') not in pages:
        fail(ident + ': missing explanation record')
    elif not d.get('anchor') or d['anchor'] not in re.findall(r'\bid="([^"]+)"', pages[d['page']]['body']):
        fail(ident + ': missing inline explanation anchor')
    for target in d.get('targets', []):
        if target not in pages:
            fail(ident + ': missing target ' + target)

    image = d.get('image')
    if kind == 'table':
        if image and not (root / image).is_file():
            fail(ident + ': optional table image is missing')
        if not isinstance(d.get('html'), str) or not re_has_table(d['html']):
            fail(ident + ': missing native HTML table')
        if not str(d.get('source', '')).endswith('.html.txt'):
            fail(ident + ': table source must be .html.txt')
    elif not image or not (root / image).is_file():
        fail(ident + ': missing image')
    elif kind == 'plot':
        if Path(image).suffix.lower() != '.png':
            fail(ident + ': plot image must be PNG')
        else:
            try:
                width, height = dimensions(root / image)
                if 'width' in d and d['width'] != width:
                    fail(ident + ': PNG width differs from manifest')
                if 'height' in d and d['height'] != height:
                    fail(ident + ': PNG height differs from manifest')
            except (OSError, ValueError, struct.error) as exc:
                fail(ident + ': ' + str(exc))
    else:
        if Path(image).suffix.lower() != '.svg':
            fail(ident + ': concept/draw.io image must be SVG')
        else:
            check_svg(root / image, ident)

    if kind in ('drawio', 'reuse'):
        source = d.get('source', '')
        if not source.endswith('.drawio'):
            fail(ident + ': editable draw.io source required')
        elif (root / source).is_file():
            check_drawio(root / source, ident)

if data['version'] != 1 or data['sdk_revision'] != receipt['sdk_revision']:
    fail('Measurement schema or SDK revision differs')
photo_pages = read(root / 'content/feature-photo-examples.json')['examples']
if {p['case'] for p in photo_pages} != {c['id'] for c in data['cases']}:
    fail('Functional photo examples do not cover every recorded case')
for row in photo_pages:
    page = pages.get(row['page'])
    if not page or page.get('parent') != row['parent']:
        fail(row['case'] + ': missing functional example or parent')
        continue
    if page.get('measurement_case') != row['case'] or not page.get('measurement_lab'):
        fail(row['case'] + ': example component metadata differs')
    if f'data-case-id="{row["case"]}"' not in page['body'] or 'data-embedded="true"' not in page['body']:
        fail(row['case'] + ': missing fixed-case viewer')
    if 'mlab-case-list' in page['body'] or 'class="mlab-cases"' in page['body']:
        fail(row['case'] + ': cross-function case menu remains')
    if row['principle'] not in pages:
        fail(row['case'] + ': functional principle absent')
seen = set()
for c in data['cases']:
    if c['id'] in seen:
        fail('Duplicate case ' + c['id'])
    seen.add(c['id'])
    try:
        if dimensions(root / 'assets/measurement' / c['image']['original']) != (c['image']['width'], c['image']['height']):
            fail(c['id'] + ': original image dimensions differ')
    except (OSError, ValueError, struct.error) as exc:
        fail(c['id'] + ': ' + str(exc))
    for step in c['steps']:
        if step.get('image') and not (root / 'assets/measurement' / step['image']).is_file():
            fail(c['id'] + ': missing step image')
    for plot in c.get('plots', []):
        if not (root / 'assets/measurement' / plot['image']).is_file():
            fail(c['id'] + ': missing plot')
    for m in c['metrics']:
        if isinstance(m['value'], (int, float)) and not math.isfinite(m['value']):
            fail(c['id'] + ': nonfinite metric')
    for api in c['api_links']:
        if api['path'].split('#')[0] not in pages:
            fail(c['id'] + ': API target absent')
    if not c['source'].get('url') or not c['source'].get('license'):
        fail(c['id'] + ': source attribution missing')
    if not c['verification'].get('method'):
        fail(c['id'] + ': independent comparison method absent')
    if receipt['cases'].get(c['id']) != 'pass':
        fail(c['id'] + ': no passing run receipt')
for relative, expected in receipt['files_sha256'].items():
    path = root / relative
    if not path.is_file():
        fail(relative + ': recorded asset absent')
        continue
    blob = path.read_bytes()
    if path.suffix in ['.py', '.cjs', '.js', '.css', '.json', '.svg', '.txt', '.drawio']:
        blob = blob.replace(b'\r\n', b'\n')
    if hashlib.sha256(blob).hexdigest() != expected:
        fail(relative + ': differs from recorded output')
print(f'Visual QA: {len(manifest["diagrams"])} visuals, {len(data["cases"])} image cases, {len(receipt["files_sha256"])} source/output hashes')
for error in errors:
    print('FAIL', error)
if errors:
    sys.exit(1)
print('PASS — visual assets, editable sources, real inputs, measurements and passing-run hashes')
