"""Check generated API metadata and that executable documentation matches its receipt."""
from pathlib import Path
import ast, hashlib, html, json, re, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

root = Path(__file__).resolve().parents[1]
pages = json.loads((root / 'content/pages.json').read_text(encoding='utf-8'))
receipt = json.loads((root / 'content/verification.json').read_text(encoding='utf-8'))
catalog = json.loads((root / 'content/unified-catalog.json').read_text(encoding='utf-8'))
errors = []
if re.search(r'(?i)(?:/mnt/w/Source/\.zvision-tools|W:[/\\]Source[/\\]\.zvision-tools|C:[/\\]Users[/\\][^/\\\s<]+)',json.dumps([pages,catalog,receipt],ensure_ascii=False)):
    errors.append('Private work path leaked into public structured content')
paths = [p['path'] for p in pages]
if len(paths) != len(set(paths)): errors.append('Duplicate content page paths')
if len({e['id'] for e in catalog['entries']}) != len(catalog['entries']): errors.append('Duplicate API IDs')
verified = {b['decoded_code_sha256'] for b in receipt['inline'] if b['status'] == 'pass'}
complete_count = 0
for page in pages:
    body = page['body']
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', body): errors.append(page['path'] + ': invalid control character')
    if re.search(r'(?i)(?:/mnt/w/Source/\.zvision-tools|W:[/\\]Source[/\\]\.zvision-tools|C:[/\\]Users[/\\][^/\\\s<]+)', body):
        errors.append(page['path'] + ': private work path leaked')
    for i, m in enumerate(re.finditer(r'<pre><code(?P<attrs>[^>]*)>(?P<raw>.*?)</code></pre>', body, re.S)):
        code = html.unescape(m['raw'])
        lang = re.search(r'language-([^\s"]+)', m['attrs'])
        language = lang[1] if lang else ''
        complete = language == 'rust' and bool(re.search(r'\bfn\s+main\s*\(', code))
        if language == 'csharp':
            complete = bool(re.search(r'\b(?:class\s+Program|using\s+ZVision\s*;)', code))
            if re.search(r'\b(?:model, image, spec|template, searchImage, spec|image는 해당 ROI)', code): complete = False
        if language == 'python':
            try: ast.parse(code)
            except SyntaxError: pass  # An API declaration is not an executable fixture.
            else:
                complete = ('sys.argv[1]' in code or bool(re.search(r'\b(?:from\s+zvision\s+import|import\s+zvision)', code)))
                if re.search(r'\bmask\s*=\s*image\.threshold\(t\)', code): complete = False
        if complete:
            complete_count += 1
            digest = hashlib.sha256(code.encode()).hexdigest()
            if digest not in verified: errors.append(f'{page["path"]} block {i}: executable code has no passing receipt')
for p in paths:
    if not (root / p).is_file(): errors.append('Missing generated page ' + p)
call_receipt_path=root/'content/topic-call-verification.json'
if call_receipt_path.exists():
    calls=json.loads(call_receipt_path.read_text(encoding='utf-8'))
    fixture=root/calls['fixture']
    if not fixture.is_file() or hashlib.sha256(fixture.read_bytes()).hexdigest()!=calls['fixture_sha256']:errors.append('Call verification fixture differs from tested version')
    by_path={p['path']:p for p in pages}
    for case in calls['cases']:
        page=by_path.get(case['page'])
        hashes={hashlib.sha256(html.unescape(code).encode()).hexdigest()for code in re.findall(r'<pre><code[^>]*>(.*?)</code></pre>',page['body'],re.S)}if page else set()
        if case['status']!='pass' or case['decoded_code_sha256']not in hashes:errors.append('Call fragment differs from passing receipt: '+case['page'])
if receipt['source_revision'] != 'ce902e85c3405eb63df40c699ddbdf70ee1d03bd': errors.append('Unexpected SDK revision')
for name, expected in receipt.get('downloads', {}).items():
    archive=root/'examples/downloads'/name
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=expected['sha256']:errors.append('Download differs from tested archive: '+name)
print(f'Content QA: {len(pages)} pages, {len(catalog["entries"])} API entries, {complete_count} executable blocks')
for error in errors: print('FAIL', error)
if errors: sys.exit(1)
print('PASS — API IDs, public paths and executed code hashes')
