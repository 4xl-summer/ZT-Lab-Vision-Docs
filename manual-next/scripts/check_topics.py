"""Check the independent-topic graph and preserved example fragments."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import collections, hashlib, html, json, re, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[1]
read=lambda name:json.loads((root/'content'/name).read_text(encoding='utf-8'))
records=read('pages.json');pages={p['path']:p for p in records}
redirects=read('topic-redirects.json');mapping=read('topic-mapping.json')
errors=[];families=collections.defaultdict(list)
for p in records:
    if p.get('parent'):
        families[p['parent']].append(p['path'])
        if p['parent'] not in pages:errors.append(p['path']+': parent absent')
        trail={p['path']};current=p
        while current.get('parent') in pages:
            parent=current['parent']
            if parent in trail:
                errors.append(p['path']+': cyclic topic hierarchy');break
            trail.add(parent);current=pages[parent]
    if p.get('topic_leaf'):
        if not p.get('parent') or not p.get('topic_anchor'):errors.append(p['path']+': topic metadata absent')
        elif p['topic_anchor'] not in re.findall(r'\bid=["\']([^"\']+)',p['body']):errors.append(p['path']+': original topic anchor absent')
for old,new in redirects.items():
    origin,sep,fragment=old.partition('#');target=urlsplit(new).path
    if not sep or not fragment or origin not in pages:errors.append(old+': invalid original topic address')
    if target not in pages:errors.append(old+': redirected topic absent')
for row in mapping:
    page=pages.get(row['child'])
    if not page:
        errors.append(row['child']+': teaching topic absent');continue
    if page.get('parent')!=row['parent'] or page.get('topic_anchor')!=row['anchor']:errors.append(row['child']+': source mapping differs')
    target=redirects.get(row['parent']+'#'+row['anchor'],'').split('#')[0]
    if target!=row['child']:errors.append(row['child']+': legacy link points elsewhere')
    hashes={hashlib.sha256(html.unescape(c).encode()).hexdigest()for c in re.findall(r'<pre><code[^>]*>(.*?)</code></pre>',page['body'],re.S)}
    if set(row['original_code_sha256'])-hashes:errors.append(row['child']+': original code changed or missing')

retired_file=root/'content/retired-topics.json'
if retired_file.exists():
    moves=json.loads((root/'content/page-moves.json').read_text(encoding='utf-8'))['moves']
    retired=json.loads(retired_file.read_text(encoding='utf-8'))['topics']
    active_children={row['child'] for row in mapping}
    for row in retired:
        path=row['child']
        if path in pages or path in active_children:errors.append(path+': removed related API topic is active')
        if path not in moves:errors.append(path+': removed topic has no legacy destination')
        if row['original_code_sha256']:errors.append(path+': removed topic contained original executable examples')

receipt_path=root/'content/topic-layout-verification.json'
if not receipt_path.exists():errors.append('layout receipt: missing independent-topic screen verification')
if receipt_path.exists():
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    measured={m['path']:m for m in receipt['measurements']}
    leaves={p['path']:p for p in records if p.get('topic_leaf')}
    if set(measured)!=set(leaves):errors.append('layout receipt: independent-topic coverage differs')
    for path,p in leaves.items():
        m=measured.get(path)
        if not m:continue
        if m['body_sha256']!=hashlib.sha256(p['body'].encode()).hexdigest():errors.append(path+': layout receipt is stale')
        if m['height']<receipt['minimum_primary_height_px'] or m['overflow']:errors.append(path+': insufficient primary content or horizontal overflow')
    for path,expected in receipt['stylesheets_sha256'].items():
        normalized=(root/path).read_bytes().replace(b'\r\n',b'\n')
        if hashlib.sha256(normalized).hexdigest()!=expected:errors.append(path+': layout stylesheet changed after measurement')
    print(f'Layout receipt: {len(measured)} leaves, viewport {receipt["viewport"]["width"]} × {receipt["viewport"]["height"]}, primary body ≥ {receipt["minimum_primary_height_px"]} px')

print(f'Topic QA: {len(mapping)} teaching topics, {sum(bool(p.get("topic_leaf"))for p in records)} independent leaves, {len(redirects)} legacy destinations')
for error in errors:print('FAIL',error)
if errors:sys.exit(1)
print('PASS — topic hierarchy, original anchors, redirects and source example preservation')
