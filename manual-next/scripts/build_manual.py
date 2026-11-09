#!/usr/bin/env python3
"""Build the ZVision manual from reusable page records and an API catalog.

Initial import: --docs DOCS --stage STAGING --baseline BASELINE --build
Rebuild:        --docs DOCS --build
The initial import writes content/pages.json and a reduced catalog. The builder
renders home and coverage from authored page records when available.
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import shutil
import hashlib
from collections import defaultdict
from pathlib import Path, PurePosixPath

H = html.escape

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def safe_path(value):
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or not value.endswith('.html') or '\\' in value:
        raise ValueError('Invalid page path: '+value)
    return p.as_posix()

def plain(value):
    return html.unescape(re.sub(r'<[^>]+>', '', value or '')).strip()

def extract_baseline(baseline, report):
    result = {}
    for file in sorted(baseline.rglob('*.html')):
        path = file.relative_to(baseline).as_posix()
        text = file.read_text(encoding='utf-8-sig')
        match = re.search(r'<article\b[^>]*class=["\'][^"\']*\bdoc\b[^"\']*["\'][^>]*>(.*?)</article\s*>', text, re.I|re.S)
        if not match:
            report['baseline_without_article'].append(path)
            continue
        head = re.search(r'<h1\b[^>]*>(.*?)</h1\s*>', text, re.I|re.S)
        title = plain(head.group(1)) if head else path
        desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)', text, re.I)
        result[path] = {'path':path, 'title':title, 'description':html.unescape(desc.group(1)) if desc else title,
                        'group':'문서', 'body':match.group(1), 'symbols':[], 'examples':[]}
    return result

def baseline_nav(baseline):
    if not baseline: return []
    file=baseline/'assets/manual.js'
    if not file.exists(): return []
    source=file.read_text(encoding='utf-8-sig')
    found=re.search(r'\bconst\s+data\s*=\s*(\[)', source)
    if not found: return []
    return json.JSONDecoder().raw_decode(source[found.start(1):])[0]

def load_records(stage, baseline, report):
    pages=extract_baseline(baseline, report)
    legacy={path:re.findall(r'\bid=["\']([^"\']+)["\']',p['body']) for path,p in pages.items()}
    origins={p:'baseline' for p in pages}
    # Real API reference pages supersede the old baseline. Reference overview
    # pages are used only where no generated reference page exists.
    ref=stage/'reference'
    for name in ('python-pages.json','csharp-pages.json','rust-pages.json','pages.json'):
        file=ref/name
        if not file.exists(): continue
        for page in read_json(file):
            path=safe_path(page['path'])
            if name=='pages.json' and origins.get(path)=='reference':
                report['duplicate_precedence'].append({'path':path,'kept':'reference','ignored':'reference overview'})
                continue
            pages[path]=page; origins[path]='reference'
    # Domain authors supersede generated reference pages and baseline pages.
    for file in sorted(stage.glob('*/pages.json'), key=lambda f:(f.parent.name == 'root', f.parent.name)):
        if file.parent.name in ('reference','site-tools'): continue
        for page in read_json(file):
            path=safe_path(page['path'])
            if file.parent.name != 'root' and origins.get(path) not in (None,'baseline','reference'):
                report['duplicate_precedence'].append({'path':path,'kept':origins[path],'ignored':file.parent.name})
                continue
            pages[path]=page; origins[path]=file.parent.name
    for path,ids in legacy.items():
        if path in pages:pages[path]['legacy_ids']=list(dict.fromkeys(ids))
    return pages

def compact_catalog(catalog):
    compact=[]
    for e in catalog.get('entries',[]):
        if not e.get('href'): continue
        compact.append({k:e.get(k) for k in ('id','language','name','kind','type_name','href','summary','signature','params','returns')} |
                       {'members':[{k:m.get(k) for k in ('name','kind','href','signature','summary','params','returns')} for m in e.get('members',[]) if m.get('name') and m.get('href')]})
    return {'entries':compact}

def norm(value):
    value=re.sub(r'<[^>]*>', '', str(value or ''))
    return ''.join(c for c in value.casefold() if c.isalnum())

def api_kind(entry,item):
    kind=item.get('kind') or ''
    if kind=='dataclass_field':return 'field'
    if str(kind).lower()=='field' and str(entry.get('kind')).lower()=='enum':return 'enum_member'
    if str(item.get('name','')).startswith('op_'):return 'operator'
    if entry.get('language')=='rust':
        anchor=item.get('href','').partition('#')[2].split('.',1)[0]
        member_kind={'method':'method','tymethod':'method','variant':'enum_member','structfield':'field','associatedconstant':'constant','associatedtype':'associated_type'}
        if anchor in member_kind:return member_kind[anchor]
        if kind=='rustdoc':
            declaration=entry.get('id','').split(':',1)[-1].rsplit('/',1)[-1].split('.',1)[0]
            return {'fn':'function','type':'type_alias'}.get(declaration,declaration)
    return kind

def kind_label(kind):
    return {'class':'클래스','struct':'구조체','enum':'열거형','enum_member':'열거값','method':'메서드','function':'함수','property':'프로퍼티','field':'필드','constructor':'생성자','classmethod':'클래스 메서드','staticmethod':'정적 메서드','constant':'상수','trait':'트레이트','type_alias':'타입 별칭','associated_type':'연관 타입','operator':'연산자','interface':'인터페이스','delegate':'델리게이트','union':'공용체'}.get(str(kind).lower(),kind)

def build_index(catalog):
    index=defaultdict(list); by_page=defaultdict(list)
    for e in catalog.get('entries',[]):
        name=e.get('name') or ''; typename=e.get('type_name') or name
        class_keys={norm(name), norm(typename)}
        if e.get('language','').casefold()=='python': class_keys.add(norm('zvision.'+name))
        for key in class_keys:
            if key: index[key].append((e,None))
        by_page[e['href'].split('#')[0]].append(e)
        for member in e.get('members',[]):
            membername=member.get('name','')
            member_keys={norm(name+'.'+membername), norm(typename+'.'+membername)}
            if e.get('language','').casefold()=='python': member_keys.add(norm('zvision.'+name+'.'+membername))
            for key in member_keys:
                if key: index[key].append((e,member))
    return index,by_page

def relurl(path, destination):
    url, sep, anchor=destination.partition('#')
    rel=os.path.relpath(url, start=str(PurePosixPath(path).parent)).replace('\\','/')
    return rel+(sep+anchor if sep else '')

def ensure_ids(body, path, report):
    ids=set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']',body,re.I))
    counter=0
    pattern=re.compile(r'<(h2|h3)\b([^>]*)>(.*?)</\1\s*>',re.I|re.S)
    def update(m):
        nonlocal counter
        tag,attrs,inner=m.groups()
        if re.search(r'\bid\s*=',attrs,re.I): return m.group(0)
        text=plain(inner).casefold()
        slug=re.sub(r'[^\w\-]+','-',text,flags=re.UNICODE).strip('-')[:70]
        if not slug: slug='section'
        original=slug
        while slug in ids:
            counter+=1; slug=original+'-'+str(counter)
        ids.add(slug)
        report['generated_heading_ids']+=1
        return f'<{tag}{attrs} id="{H(slug,quote=True)}">{inner}</{tag}>'
    return pattern.sub(update,body)

def verification(page):
    cases=list(dict.fromkeys(str(x) for x in page.get('examples',[]) if isinstance(x,str) and x))
    if not cases: return ''
    links=[]
    for case in cases:
        dest='reference/verification.html#case-'+case
        links.append('<li><a href="'+H(relurl(page['path'],dest),quote=True)+'"><code>'+H(case)+'</code></a></li>')
    return '<section id="verification-cases"><h2 id="verification-cases-heading">관련 검증 사례</h2><ul>'+''.join(links)+'</ul></section>'

def render(page,index,by_page,report,version=''):
    path=page['path']; title=page.get('title') or path; description=page.get('description') or title
    root='../'*len(PurePosixPath(path).parts[:-1]) or './'
    body=ensure_ids(page.get('body',''),path,report)
    ids=re.findall(r'\bid=["\']([^"\']+)["\']',body)
    aliases=[]
    for old in page.get('legacy_ids',[]):
        if old in ids:continue
        target=None
        name=re.sub(r'^member-','',old,flags=re.I)
        name=re.sub(r'-\d+$','',name).lower()
        candidates=[x for x in ids if re.match(r'^member-'+re.escape(name)+r'(?:-|$)',x,re.I)]
        if candidates:target=candidates[0]
        elif old.startswith('member-') and norm(name)==norm(PurePosixPath(path).stem.rsplit('-',1)[-1]):
            target=next((x for x in ids if x.startswith('member-ctor-')),None)
        if target is None:
            preferred={'methods':['member-list','members'],'fields':['data-fields'],'variants':['enum-values'],'signature':['overview'],'members':['member-list'],'example':['example'],'theory':['theory','overview']}.get(old,[])
            target=next((x for x in preferred if x in ids),None)
        aliases.append('<span class="legacy-anchor" id="'+H(old,quote=True)+'"'+(' data-legacy-target="'+H(target,quote=True)+'"'if target else'')+' aria-hidden="true"></span>')
    body=''.join(aliases)+body
    existing_ids=re.findall(r'\bid\s*=\s*[\"\']([^\"\']+)[\"\']',body,re.I)
    for ident in sorted(set(existing_ids)):
        if existing_ids.count(ident)>1: report['duplicate_ids'].append({'path':path,'id':ident})
    for fragment in re.findall(r'href\s*=\s*[\"\']#([^\"\']+)[\"\']',body,re.I):
        if fragment not in existing_ids: report['unresolved_local_fragments'].append({'path':path,'fragment':fragment})
    body='<div class="topic-content" data-topic-primary="true">'+body+'</div>'
    parent=page.get('parent')
    if parent:
        body='<p class="topic-context"><a href="'+H(relurl(path,parent),quote=True)+'">상위 목차로 돌아가기</a></p>'+body
    appendix=verification(page)
    # A leaf may itself be the original verification/API topic. Its source
    # anchor keeps its address; generated appendices receive distinct IDs.
    used=set(re.findall(r'\bid=["\']([^"\']+)',body))
    def appendix_id(match):
        original=match[1];candidate=original
        while candidate in used:candidate='appendix-'+candidate
        used.add(candidate)
        return 'id="'+H(candidate,quote=True)+'"'
    appendix=re.sub(r'\bid="([^"]+)"',appendix_id,appendix)
    body+=appendix
    if page.get('previous_topic') or page.get('next_topic'):
        body+='<nav class="topic-pager" aria-label="소주제 순서">'
        for key,label in [('previous_topic','이전 소주제'),('next_topic','다음 소주제')]:
            if page.get(key):body+='<a href="'+H(relurl(path,page[key]['path']),quote=True)+'">'+label+' · '+H(page[key]['title'])+'</a>'
        body+='</nav>'
    extra_head='<link rel="stylesheet" href="'+H(root,quote=True)+'assets/manual-visuals.css?v='+version+'">'
    if page.get('measurement_lab'):
        extra_head+='<link rel="stylesheet" href="'+H(root,quote=True)+'assets/measurement-lab.css?v='+version+'"><script defer src="'+H(root,quote=True)+'assets/measurement-lab.js?v='+version+'"></script>'
    return '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="manual-root" content="{root}"><meta name="manual-path" content="{path}"><meta name="description" content="{description}"><title>{title} · ZVision Manual</title><link rel="stylesheet" href="{root}assets/manual.css"><link rel="stylesheet" href="{root}assets/manual-extra.css"><script defer src="{root}assets/manual-data.js"></script><script defer src="{root}assets/manual.js"></script></head>
<body><a class="skip" href="#main">본문으로 이동</a><div class="layout"><aside class="sidebar"><a class="brand" href="{root}index.html"><span class="logo">ZV</span><span><strong>ZVision</strong><small>DEVELOPER MANUAL</small></span></a><nav id="site-nav" aria-label="문서 전체 목차"></nav></aside><div class="workspace"><header class="topbar"><button id="menu-toggle" class="control toggle-menu" type="button" aria-label="목차 열기">☰</button><span class="top-id">ZVISION / ENGINEERING REFERENCE</span><div class="top-btns"><button id="search-open" class="control" type="button">⌕ 검색 /</button><button id="theme-toggle" class="control" type="button" aria-label="화면 테마 전환">◐</button></div></header><main id="main" class="main"><div class="crumb"><a href="{root}index.html">매뉴얼 홈</a> / {group} / <b>{title}</b></div><header class="page-head"><h1>{title}</h1><p class="lede">{description}</p></header><article class="doc">{body}</article><footer class="footer">ZVision 기술 매뉴얼 · <a href="{root}index.html">매뉴얼 홈</a></footer></main></div></div><dialog id="search-dialog" class="search-modal" aria-label="문서 검색"><div class="search-line"><input id="search-input" type="search" aria-label="검색어" placeholder="API, 알고리즘, 개념 검색"><button id="search-close" type="button">닫기</button></div><ol class="search-list" id="search-results"></ol></dialog></body></html>
'''.format(root=H(root,quote=True),path=H(path,quote=True),title=H(title),description=H(description,quote=True),group=H(page.get('group') or '문서'),body=body).replace('<body>','<body class="measurement-page">'if page.get('measurement_lab')else'<body>').replace('</head>',extra_head+'</head>').replace('assets/manual.css"','assets/manual.css?v='+version+'"').replace('assets/manual-extra.css"','assets/manual-extra.css?v='+version+'"').replace('assets/manual-data.js"','assets/manual-data.js?v='+version+'"').replace('assets/manual.js"','assets/manual.js?v='+version+'"').replace('</body>','<script type="application/json" id="page-redirects">'+json.dumps(page.get('topic_redirects',{}),ensure_ascii=False).replace('</','<\\/')+'</script></body>')

def nav_records(pages,nav):
    rows=[]; seen=set()
    for row in nav:
        if len(row)<3 or row[1] not in pages or row[1] in seen: continue
        page=pages[row[1]]; seen.add(row[1]); page['group']=row[0]
        rows.append([row[0],row[1],page.get('title') or row[2],page.get('description') or ''])
    for path,page in sorted(pages.items()):
        if path not in seen:
            rows.append([page.get('group') or '문서',path,page.get('title') or path,page.get('description') or ''])
    # Preserve existing order within groups, put new items after each existing group.
    group_order=list(dict.fromkeys(row[0] for row in rows))
    return [row for group in group_order for row in rows if row[0]==group]

def render_page_move(path, move):
    """Keep bookmarked URLs working without exposing retired pages in navigation."""
    safe_path(path)
    def destination(value):
        base,sep,fragment=value.partition('#')
        safe_path(base)
        return relurl(path,base)+('#'+fragment if sep else '')
    target=destination(move['target'])
    fragments={key:destination(value) for key,value in move.get('fragments',{}).items()}
    data=json.dumps({'target':target,'fragments':fragments},ensure_ascii=False).replace('</','<\\/')
    root='../'*len(PurePosixPath(path).parts[:-1]) or './'
    script='const m='+data+';let k="";try{k=decodeURIComponent(location.hash.slice(1))}catch{}location.replace(m.fragments[k]||m.target);'
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="manual-root" content="'+H(root,quote=True)+'"><meta name="manual-path" content="'+H(path,quote=True)+'"><meta name="manual-redirect" content="'+H(target,quote=True)+'"><title>기능 문서로 이동 · '+H(path)+'</title><link rel="canonical" href="'+H(target,quote=True)+'"><script>'+script+'</script><noscript><meta http-equiv="refresh" content="0;url='+H(target,quote=True)+'"></noscript></head><body><h1>기능 문서로 이동합니다</h1><p>설명과 예제가 해당 기능 문서에 통합되었습니다.</p><p><a href="'+H(target,quote=True)+'">해당 기능 문서 열기</a></p></body></html>\n'

def main():
    parser=argparse.ArgumentParser(description='Generate the ZVision manual from structured pages.')
    parser.add_argument('--docs',type=Path,required=True)
    parser.add_argument('--stage',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    if not args.build: parser.error('Pass --build to generate the manual.')
    if bool(args.stage)!=bool(args.baseline): parser.error('--stage and --baseline must be supplied together.')
    docs=args.docs.resolve(); manual=docs/'manual-next'; content=manual/'content'
    report={'baseline_without_article':[],'duplicate_precedence':[],'unmatched_symbols':[],'generated_heading_ids':0,'preserved_pages':[],'duplicate_ids':[],'unresolved_local_fragments':[]}
    if args.stage:
        stage=args.stage.resolve(); baseline=args.baseline.resolve()
        pages=load_records(stage,baseline,report)
        catalog=compact_catalog(read_json(stage/'reference/unified-catalog.json'))
        nav=baseline_nav(baseline)
    else:
        pages={p['path']:p for p in read_json(content/'pages.json')}
        catalog=read_json(content/'unified-catalog.json')
        nav=read_json(content/'navigation.json')
        baseline=None
    redirects_file=content/'topic-redirects.json'
    for page in pages.values():
        for key in ('topic_redirects','previous_topic','next_topic'):page.pop(key,None)
    if redirects_file.exists():
        for old,target in read_json(redirects_file).items():
            origin,sep,anchor=old.partition('#')
            if sep and origin in pages:pages[origin].setdefault('topic_redirects',{})[anchor]=target
    families=defaultdict(list)
    for page in pages.values():
        if page.get('parent'):families[page['parent']].append(page)
    for children in families.values():
        children.sort(key=lambda p:p.get('topic_order',99999))
        for i,p in enumerate(children):
            if i:p['previous_topic']={'path':children[i-1]['path'],'title':children[i-1].get('nav_label')or children[i-1]['title']}
            if i+1<len(children):p['next_topic']={'path':children[i+1]['path'],'title':children[i+1].get('nav_label')or children[i+1]['title']}
    moves_file=content/'page-moves.json'
    moves=read_json(moves_file)['moves'] if moves_file.exists() else {}
    for old,move in moves.items():
        if old in pages:raise ValueError('Moved page is still active: '+old)
        for dest in [move['target'],*move.get('fragments',{}).values()]:
            if dest.split('#',1)[0] not in pages:raise ValueError('Move target is not active: '+dest)
    rows=nav_records(pages,nav); index,by_page=build_index(catalog)
    version_hash=hashlib.sha256(json.dumps([pages,catalog],ensure_ascii=False,sort_keys=True).encode())
    version_hash.update(Path(__file__).read_bytes())
    for name in ('manual.js','manual.css','manual-extra.css','manual-visuals.css','measurement-lab.js','measurement-lab.css'):
        asset=manual/'assets'/name
        if asset.exists():version_hash.update(asset.read_bytes())
    version=version_hash.hexdigest()[:12]
    manual.mkdir(parents=True,exist_ok=True)
    for path,page in pages.items():
        path=safe_path(path)
        target=manual.joinpath(*PurePosixPath(path).parts)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(render(page,index,by_page,report,version),encoding='utf-8',newline='\n')
    for path,move in moves.items():
        target=manual.joinpath(*PurePosixPath(safe_path(path)).parts)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(render_page_move(path,move),encoding='utf-8',newline='\n')
    assets=manual/'assets'; assets.mkdir(parents=True,exist_ok=True)
    if baseline:
        for name in ('manual.css','manual.js'):
            source=baseline/'assets'/name; target=assets/name
            if source.exists() and not target.exists(): shutil.copy2(source,target)
    def search_meta(item):
        return {'summary':plain(item.get('summary'))[:140],'keywords':' '.join(p.get('name','') for p in item.get('params',[]) if isinstance(p,dict))}
    api_search=[{k:e.get(k) for k in ('name','language','href')} | {'kind':api_kind(e,e)} | search_meta(e) |
                {'members':[{k:m.get(k) for k in ('name','href')} | {'kind':api_kind(e,m)} | search_meta(m) for m in e.get('members',[])]}
                for e in catalog.get('entries',[])]
    (assets/'api-search.json').write_text(json.dumps(api_search,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    data=json.dumps({'version':version,'pages':[{'group':r[0],'path':r[1],'title':r[2],'description':r[3]}|{k:pages[r[1]][k]for k in ('parent','topic_leaf','nav_label','topic_order')if k in pages[r[1]]} for r in rows], 'apis':[], 'apiIndex':'assets/api-search.json'},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    (assets/'manual-data.js').write_text('window.MANUAL_DATA = '+data+';\n',encoding='utf-8')
    write_json(content/'pages.json',list(pages.values()))
    write_json(content/'unified-catalog.json',catalog)
    write_json(content/'navigation.json',rows)
    write_json(content/'build-report.json',report)
    scripts=manual/'scripts'; scripts.mkdir(parents=True,exist_ok=True)
    destination=scripts/'build_manual.py'
    if Path(__file__).resolve()!=destination.resolve(): shutil.copy2(Path(__file__),destination)
    print('Built',len(pages),'page records; unmatched symbols:',len(report['unmatched_symbols']))

if __name__=='__main__': main()
