"""Check recorded real-image runs, figure sources and referenced assets."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib,html,json,math,re,struct,sys
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
manifest=read(root/'assets/visuals/manifest.json')
data=read(root/'assets/measurement/measurements.json')
receipt=read(root/'content/visual-verification.json')
pages={p['path']:p for p in read(root/'content/pages.json')}
errors=[]
def fail(message):errors.append(message)
def dimensions(path):
    blob=path.read_bytes()
    if blob[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Expected PNG '+str(path))
    return struct.unpack('>II',blob[16:24])
for d in manifest['diagrams']:
    for key in ['image','source','page']:
        if not(root/d[key]).is_file():fail(d['id']+': missing '+key)
    if d['page']not in pages:fail(d['id']+': missing explanation record')
    for target in d['targets']:
        if target not in pages:fail(d['id']+': missing target '+target)
    svg=ET.parse(root/d['image']).getroot()
    if not svg.tag.endswith('svg'):fail(d['id']+': invalid SVG')
    if any(e.tag.endswith('script')for e in svg.iter()):fail(d['id']+': script in static SVG')
    if '<?xml-stylesheet' in(root/d['image']).read_text(encoding='utf-8'):fail(d['id']+': external font stylesheet in static SVG')
    if d['kind']=='drawio':
        xml=ET.parse(root/d['source']);ids={e.attrib['id']for e in xml.iter('mxCell')}
        for edge in xml.iter('mxCell'):
            if edge.attrib.get('edge')=='1'and(edge.attrib.get('source')not in ids or edge.attrib.get('target')not in ids):fail(d['id']+': broken editable connector')
if data['version']!=1 or data['sdk_revision']!=receipt['sdk_revision']:fail('Measurement schema or SDK revision differs')
seen=set()
for c in data['cases']:
    if c['id']in seen:fail('Duplicate case '+c['id'])
    seen.add(c['id'])
    if dimensions(root/'assets/measurement'/c['image']['original'])!=(c['image']['width'],c['image']['height']):fail(c['id']+': original image dimensions differ')
    for step in c['steps']:
        if step.get('image')and not(root/'assets/measurement'/step['image']).is_file():fail(c['id']+': missing step image')
    for plot in c.get('plots',[]):
        if not(root/'assets/measurement'/plot['image']).is_file():fail(c['id']+': missing plot')
    for m in c['metrics']:
        if isinstance(m['value'],(int,float))and not math.isfinite(m['value']):fail(c['id']+': nonfinite metric')
    for a in c['api_links']:
        if a['path'].split('#')[0]not in pages:fail(c['id']+': API target absent')
    if not c['source'].get('url')or not c['source'].get('license'):fail(c['id']+': source attribution missing')
    if not c['verification'].get('method'):fail(c['id']+': independent comparison method absent')
    if receipt['cases'].get(c['id'])!='pass':fail(c['id']+': no passing run receipt')
for relative,expected in receipt['files_sha256'].items():
    path=root/relative
    if not path.is_file():fail(relative+': recorded asset absent');continue
    blob=path.read_bytes()
    if path.suffix in ['.py','.cjs','.js','.css','.json','.svg','.txt','.drawio']:blob=blob.replace(b'\r\n',b'\n')
    if hashlib.sha256(blob).hexdigest()!=expected:fail(relative+': differs from recorded output')
print(f'Visual QA: {len(manifest["diagrams"])} real renderer SVGs, {len(data["cases"])} image cases, {len(receipt["files_sha256"])} source/output hashes')
for error in errors:print('FAIL',error)
if errors:sys.exit(1)
print('PASS — editable sources, figures, real inputs, measurements and passing-run hashes')
