"""Guard the source and document routes verified in a real browser."""
from pathlib import Path
import hashlib,json,re,sys
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
receipt=read(root/'content/navigation-verification.json')
pages=read(root/'content/pages.json')
errors=[]
for name,expected in receipt['source_sha256'].items():
    path=root/name
    if not path.is_file():errors.append(name+': tested source absent');continue
    blob=path.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(blob).hexdigest()!=expected:errors.append(name+': differs from browser-verified source')
required={'partial_content','sidebar_scroll','sidebar_expansion','refresh','back_forward','deep_address','search','anchor','photo_lifecycle','mobile_navigation','request_race','native_fallback'}
checks=receipt['checks']
if required-set(checks):errors.append('Required browser scenario absent')
for name,result in checks.items():
    if result.get('status')!='pass':errors.append(name+': browser verification did not pass')
for p in pages:
    text=(root/p['path']).read_text(encoding='utf-8')
    scripts=re.findall(r'<script\b[^>]*\bsrc="([^"]+)"',text)
    matching=[s for s in scripts if '/manual-navigation.js?'in s]
    if len(matching)!=1:errors.append(p['path']+': navigation module missing or duplicated');continue
    if scripts.index(matching[0])<=next((i for i,s in enumerate(scripts)if'/manual.js?'in s),len(scripts)):
        errors.append(p['path']+': shell module must initialize before navigation')
    if p.get('measurement_lab'):
        widget=next((i for i,s in enumerate(scripts)if'/measurement-lab.js?'in s),len(scripts))
        if widget>=scripts.index(matching[0]):errors.append(p['path']+': direct measurement page initialization order differs')
print(f'Navigation QA: {len(pages)} direct document routes, {len(checks)} browser checks, {len(receipt["source_sha256"])} tested source hashes')
for error in errors:print('FAIL',error)
if errors:sys.exit(1)
print('PASS — persistent shell, browser evidence and direct-load module order')
