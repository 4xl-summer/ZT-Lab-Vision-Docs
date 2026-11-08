#!/usr/bin/env python3
"""Static manual audit. Usage: python manual_qa.py MANUAL_ROOT [REPORT.json].

Errors are definite structural failures; warnings require editorial review. The
coverage section measures page links and reference-page counts, not SDK symbol
completeness. The caller supplies the SDK baseline separately.
"""
from __future__ import annotations
import collections, json, posixpath, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

LANGS={'rust','python','csharp','c','cpp','bash','powershell','toml','xml','json','text','html','css','javascript','js','shell','sql','ini','yaml','yml','console','sh','plaintext','diff'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
PLACEHOLDER=re.compile(r'\b(?:TODO|TBD|FIXME|PLACEHOLDER|YOUR[_ -](?:NAME|PATH|API[_ -]?KEY)|lorem ipsum)\b|@ROOT@|\{\{\s*(?:TODO|PLACEHOLDER)\s*\}\}',re.I)
IMPLEMENTATION=re.compile(r'(?:\bdef\s+\w+\s*\([^\n]*\)\s*(?:->\s*[^:\n]+)?\s*:\s*(?:return\b|raise\b|self\.)|\b(?:pub\s+)?fn\s+\w+[^\n]*\{\s*(?:let\b|return\b|self\.)|\bpublic\s+[^\n]+\([^\n]*\)\s*\{\s*(?:return\b|if\b|var\b))',re.I)

class Page(HTMLParser):
 def __init__(self, rel):
  super().__init__(convert_charrefs=True); self.rel=rel; self.ids={}; self.links=[]; self.errors=[]; self.warnings=[]; self.stack=[]; self.h1=0; self.title=''; self.article=False; self.article_seen=False; self.article_text=[]; self.article_children=[]; self.related=0; self.related_links=0; self.codes=[]; self.code=None; self.code_depth=0; self.heading=None; self.in_title=False; self.meta={}; self.imgs=[]; self.svgs=[]
 def msg(self,kind,msg): (self.errors if kind=='error' else self.warnings).append(f'{self.rel}:{self.getpos()[0]}: {msg}')
 def handle_starttag(self,tag,attrs):
  d=dict(attrs); line=self.getpos()[0]; classes=set(d.get('class','').split())
  if tag not in VOID: self.stack.append((tag,classes))
  if self.article and len(self.stack)>=2 and self.stack[-2][0]=='article': self.article_children.append((tag,classes))
  if 'id' in d:
   ident=d['id']
   if not ident: self.msg('error','empty id')
   if ident in self.ids: self.msg('error',f'duplicate id {ident!r}; first at line {self.ids[ident]}')
   self.ids[ident]=line
  if tag=='h1': self.h1+=1
  if tag in ('h2','h3','section') and self.article and not d.get('id') and 'related-api' not in classes: self.msg('warning',f'{tag} lacks id')
  if tag=='title': self.in_title=True
  if tag=='meta' and 'name' in d: self.meta[d['name']]=d.get('content','')
  if tag=='article': self.article=True; self.article_seen=True
  if tag=='section' and 'related-api' in classes: self.related+=1
  if tag in ('a','link','script','img','source','video','audio'):
   for attr in ('href','src'):
    if d.get(attr): self.links.append((d[attr],line, any('related-api' in cls for _,cls in self.stack)))
  if tag=='img' and 'alt' not in d: self.msg('error','image lacks alt')
  if tag=='svg' and not (d.get('aria-label') or d.get('aria-labelledby')): self.msg('warning','SVG lacks accessible label')
  if tag=='code' and any(t=='pre' for t,_ in self.stack):
   self.code={'line':line,'classes':classes,'text':[]}; self.codes.append(self.code)
  if tag=='a' and any('related-api' in cls for _,cls in self.stack) and d.get('href'): self.related_links+=1
 def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs); self.handle_endtag(tag)
 def handle_endtag(self,tag):
  if tag=='title': self.in_title=False
  if tag=='code': self.code=None
  if tag=='article': self.article=False
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:
    del self.stack[i:]; break
 def handle_data(self,data):
  if self.in_title: self.title+=data
  if self.code is not None: self.code['text'].append(data)
  if self.article:
   self.article_text.append(data)
   if self.code is None and re.search(r'(^|\n)\s*```',data): self.msg('warning','Markdown fenced code appears in rendered HTML')

def manual_data(root, errors):
 path=root/'assets'/'manual-data.js'
 if not path.is_file(): errors.append('assets/manual-data.js: missing'); return []
 data=path.read_text(encoding='utf-8-sig')
 m=re.search(r'window\.MANUAL_DATA\s*=\s*',data)
 if not m: errors.append('assets/manual-data.js: missing window.MANUAL_DATA assignment'); return []
 try:
  value,_=json.JSONDecoder().raw_decode(data[m.end():].lstrip())
 except ValueError as e: errors.append(f'assets/manual-data.js: invalid JSON: {e}'); return []
 if not isinstance(value,(list,dict)): errors.append('assets/manual-data.js: navigation JSON must be list or object'); return []
 return value

def strings(value):
 if isinstance(value,str): yield value
 elif isinstance(value,list):
  for x in value: yield from strings(x)
 elif isinstance(value,dict):
  for x in value.values(): yield from strings(x)

def main():
 if len(sys.argv) not in (2,3):
  print('Usage: python manual_qa.py MANUAL_ROOT [REPORT.json]',file=sys.stderr); return 2
 root=Path(sys.argv[1]).resolve()
 if not root.is_dir(): print(f'Not a directory: {root}',file=sys.stderr); return 2
 errors=[]; warnings=[]; pages={}; incoming=collections.Counter(); related_incoming=collections.Counter(); titles={}
 files=sorted(root.rglob('*.html'))
 for f in files:
  rel=f.relative_to(root).as_posix(); page=Page(rel)
  try: page.feed(f.read_text(encoding='utf-8-sig')); page.close()
  except (UnicodeError, OSError, ValueError) as e: errors.append(f'{rel}: cannot parse: {e}'); continue
  pages[rel]=page; errors.extend(page.errors); warnings.extend(page.warnings)
  if page.h1!=1: errors.append(f'{rel}: expected one h1, found {page.h1}')
  if not page.title.strip(): errors.append(f'{rel}: missing title')
  elif page.title in titles: errors.append(f'{rel}: duplicate title with {titles[page.title]}')
  else: titles[page.title]=rel
  if page.meta.get('manual-path')!=rel: errors.append(f'{rel}: manual-path is {page.meta.get("manual-path")!r}')
  if not page.meta.get('manual-root'): errors.append(f'{rel}: missing manual-root')
  if not page.meta.get('description'): warnings.append(f'{rel}: missing description')
  if not page.article_seen: errors.append(f'{rel}: missing article')
  if page.related!=1: errors.append(f'{rel}: expected one section.related-api, found {page.related}')
  if page.related and (not page.article_children or page.article_children[-1][0]!='section' or 'related-api' not in page.article_children[-1][1]): errors.append(f'{rel}: related API section is not the last article element')
  if page.related and page.related_links==0: warnings.append(f'{rel}: related API section contains no links')
  article=' '.join(page.article_text).strip()
  if len(article)<40: warnings.append(f'{rel}: article has fewer than 40 text characters')
  for m in PLACEHOLDER.finditer(article): warnings.append(f'{rel}: possible placeholder {m.group()!r}')
  for c in page.codes:
   labels=[v[9:] for v in c['classes'] if v.startswith('language-')]
   if len(labels)!=1: errors.append(f'{rel}:{c["line"]}: pre/code needs exactly one language-* class')
   elif labels[0].lower() not in LANGS: warnings.append(f'{rel}:{c["line"]}: unknown code language {labels[0]!r}')
   value=''.join(c['text'])
   if not value.strip(): warnings.append(f'{rel}:{c["line"]}: empty code block')
   if rel.startswith('reference/') and IMPLEMENTATION.search(value): warnings.append(f'{rel}:{c["line"]}: possible implementation body in reference declaration')
 asset_exists={}
 for rel,page in pages.items():
  for link,line,related in page.links:
   u=urlsplit(link)
   if u.scheme or u.netloc or link.startswith('//'): continue
   if not u.path and not u.fragment: continue
   raw=unquote(u.path); frag=unquote(u.fragment)
   if raw.startswith('/'): errors.append(f'{rel}:{line}: absolute site path {link!r}'); continue
   dest=posixpath.normpath(posixpath.join(posixpath.dirname(rel),raw)) if raw else rel
   if dest=='..' or dest.startswith('../'): errors.append(f'{rel}:{line}: link escapes manual {link!r}'); continue
   if dest in pages:
    incoming[dest]+=1
    if related: related_incoming[dest]+=1
    if frag and frag not in pages[dest].ids: errors.append(f'{rel}:{line}: missing target anchor {link!r}')
   else:
    if dest not in asset_exists:
     target=root/dest; asset_exists[dest]=(target.exists(),target.is_dir())
    exists,is_dir=asset_exists[dest]
    if not exists: errors.append(f'{rel}:{line}: missing target {link!r}'); continue
    if frag and is_dir: errors.append(f'{rel}:{line}: fragment on directory {link!r}')
    elif frag: warnings.append(f'{rel}:{line}: fragment not checked for non-HTML target {link!r}')
 nav=manual_data(root,errors)
 api_entry_count=0; api_link_count=0
 if isinstance(nav,dict) and nav.get('apiIndex'):
  index_name=nav['apiIndex']
  if not isinstance(index_name,str): errors.append('manual-data.js: apiIndex must be a string')
  else:
   idx=(root/index_name).resolve()
   try: idx.relative_to(root)
   except ValueError: errors.append('manual-data.js: apiIndex escapes manual'); idx=None
   if idx is not None:
    try:
     api_data=json.loads(idx.read_text(encoding='utf-8-sig'))
     if not isinstance(api_data,list): raise ValueError('expected array')
     api_entry_count=len(api_data)
     for entry in api_data:
      if not isinstance(entry,dict): errors.append(f'{index_name}: entry must be object'); continue
      for record in [entry]+(entry.get('members') if isinstance(entry.get('members'),list) else []):
       if not isinstance(record,dict) or not isinstance(record.get('href'),str): errors.append(f'{index_name}: entry/member missing href'); continue
       href=record['href']; uri=urlsplit(href)
       if uri.scheme or uri.netloc or uri.path.startswith('/'): errors.append(f'{index_name}: invalid local href {href!r}'); continue
       rel=posixpath.normpath(unquote(uri.path))
       if rel=='..' or rel.startswith('../'): errors.append(f'{index_name}: href escapes manual {href!r}'); continue
       if rel not in pages: errors.append(f'{index_name}: missing HTML target {href!r}'); continue
       if uri.fragment and unquote(uri.fragment) not in pages[rel].ids: errors.append(f'{index_name}: missing target anchor {href!r}')
       api_link_count+=1
    except (OSError,UnicodeError,ValueError) as e: errors.append(f'{index_name}: cannot parse API index: {e}')
 nav_targets=[]
 for s in strings(nav.get("pages", []) if isinstance(nav,dict) else nav):
  parsed=urlsplit(s)
  if not parsed.scheme and parsed.path.endswith('.html'):
   target=unquote(parsed.path).lstrip('./')
   nav_targets.append(target)
   if target not in pages: errors.append(f'assets/manual-data.js: navigation target absent: {target}')
 nav_set=set(nav_targets)
 for target,count in collections.Counter(nav_targets).items():
  if count>1: errors.append(f'assets/manual-data.js: duplicate navigation target {target} ({count})')
 for rel in pages:
  if rel not in nav_set: errors.append(f'{rel}: absent from navigation')
 groups={}
 for lang in ('rust','csharp','python'):
  refs=[x for x in pages if x.startswith('reference/'+lang+'/') and not x.endswith('/index.html')]
  apis=[x for x in pages if x.startswith('api/'+lang+'/') and not x.endswith('/index.html')]
  groups[lang]={'reference_pages':len(refs),'api_pages':len(apis),'reference_pages_with_incoming_links':sum(incoming[x]>0 for x in refs),'reference_pages_linked_from_related_api':sum(related_incoming[x]>0 for x in refs),'reference_pages_without_incoming_links':[x for x in refs if not incoming[x]]}
 report={'baseline_expected':'ce902e85c3405eb63df40c699ddbdf70ee1d03bd','baseline_note':'Supplied baseline identifier; this static manual audit does not verify the SDK checkout or symbol completeness.', 'pages':len(pages),'api_search_entries':api_entry_count,'api_search_links_checked':api_link_count,'navigation_targets':len(nav_targets),'unique_navigation_targets':len(nav_set),'linked_html_targets':sum(v>0 for v in incoming.values()),'reference_coverage':groups,'errors':errors,'warnings':warnings}
 if len(sys.argv)==3: Path(sys.argv[2]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Pages: {len(pages)}; navigation targets: {len(nav_targets)}; API entries: {api_entry_count}; API links: {api_link_count}; linked HTML targets: {report["linked_html_targets"]}')
 for lang,g in groups.items(): print(f'{lang}: reference pages {g["reference_pages"]}, incoming {g["reference_pages_with_incoming_links"]}, related-API incoming {g["reference_pages_linked_from_related_api"]}, API pages {g["api_pages"]}')
 print(f'Errors: {len(errors)}; warnings: {len(warnings)}')
 for item in errors[:100]: print('ERROR '+item)
 for item in warnings[:100]: print('WARN '+item)
 if len(errors)>100 or len(warnings)>100: print('Output truncated; provide REPORT.json for full diagnostics.')
 return 1 if errors else 0
if __name__=='__main__': sys.exit(main())
