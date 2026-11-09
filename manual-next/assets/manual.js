"use strict";
(() => {
  const data = window.MANUAL_DATA || {pages: [], apis: []};
  const pages = Array.isArray(data.pages) ? data.pages : [];
  let apis = Array.isArray(data.apis) ? data.apis : [];
  let apiLoadPromise = null;
  let apiLoadState = data.apiIndex ? 'idle' : 'ready';
  const manualBase = new URL(document.querySelector('meta[name="manual-root"]')?.content || './', document.baseURI);
  const root = manualBase.href;
  let current = document.querySelector('meta[name="manual-path"]')?.content || 'index.html';
  const normal = value => String(value ?? '').normalize('NFKC').toLocaleLowerCase();
  const kindName = value => ({method:'메서드',classmethod:'클래스 메서드',staticmethod:'정적 메서드',property:'프로퍼티',attribute:'속성',field:'필드',enum_member:'열거값',constructor:'생성자',class:'클래스',struct:'구조체',enum:'열거형',function:'함수',rustdoc:'Rust 선언',rustdoc_heading:'Rust 멤버',other:'기타',constant:'상수',trait:'트레이트',type_alias:'타입 별칭',associated_type:'연관 타입',operator:'연산자',interface:'인터페이스',delegate:'델리게이트',union:'공용체'}[normal(value)] || value);
  const href = path => new URL(String(path || ''), root).href;
  const make = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  };
  const languageOfPath = path => {
    const m = String(path).match(/^(?:api|reference)\/(rust|csharp|python)\//i);
    return m ? m[1] : '';
  };
  const languageLabel = value => ({rust: 'Rust', csharp: 'C#', python: 'Python'}[normal(value).replace(/[^a-z]/g, '')] || value);
  const languageKey = value => {
    const s = normal(value).replace(/\s+/g, '');
    return s === 'c#' || s === 'cs' || s === '.net' ? 'csharp' : s;
  };

  function collectHeadings() {
  const headings = [...document.querySelectorAll('.doc h2, .doc h3')];
  let autoId = 0;
  return headings.map(h => {
    let id = h.id;
    if (!id) {
      const parent = h.closest('section[id]');
      if (parent && parent.querySelector('h2, h3') === h) id = parent.id;
    }
    if (!id) {
      do { id = 'contents-' + (++autoId); } while (document.getElementById(id));
      h.id = id;
    }
    return {id, text: h.textContent.trim(), level: h.tagName};
  }).filter(h => h.text);

  }
  let currentHeadings = collectHeadings();

  const byPath = new Map(pages.map(p => [p.path,p]));
  const childPages = new Map();
  for (const p of pages) if (p.parent) { if (!childPages.has(p.parent)) childPages.set(p.parent,[]); childPages.get(p.parent).push(p); }
  for(const children of childPages.values())children.sort((a,b)=>(a.topic_order??99999)-(b.topic_order??99999));
  const lineage = new Set([current]);
  for (let p=byPath.get(current), guard=0; p?.parent && guard++<12; p=byPath.get(p.parent)) lineage.add(p.parent);
  const nav = document.getElementById('site-nav');
  let captureNavigation = () => null, restoreNavigation = () => {}, updatePage = () => {};
  if (nav) {
    const panel = nav.closest('.sidebar');
    const stateKey = 'zvision-nav-state:' + manualBase.pathname;
    const keyedDetails = new Map(), pageDetails = new Map(), pageLinks = new Map();
    nav.dataset.instance = globalThis.crypto?.randomUUID?.() || String(Date.now()) + Math.random();
    let restoring = false, restoreSerial = 0, saveFrame = 0;
    const expandKey = 'zvision-nav-expand-mode';
    const renderers = new WeakMap();
    const actions = make('div', 'nav-actions');
    const expandAll = make('button', '', '모두 펼침');
    expandAll.type = 'button'; expandAll.id = 'nav-expand-all'; expandAll.setAttribute('aria-controls', 'site-nav');
    const collapseAll = make('button', '', '모두 접기');
    collapseAll.type = 'button'; collapseAll.id = 'nav-collapse-all'; collapseAll.setAttribute('aria-controls', 'site-nav');
    actions.append(expandAll, collapseAll); nav.append(actions);
    const groups = new Map(), references = new Map();
    for (const page of pages) {
      if (!page?.path || !page.title || page.parent) continue;
      const lang = page.path.startsWith('reference/') ? languageOfPath(page.path) : '';
      const map = lang ? references : groups, key = lang || page.group || '기타';
      if (!map.has(key)) map.set(key,[]); map.get(key).push(page);
    }
    const linkFor = page => {
      const link=make('a','nav-a'+(page.path===current?' active':''),page.nav_label || page.title);
      pageLinks.set(page.path,link); link.dataset.manualPath=page.path;
      link.href=href(page.path); if(page.path===current)link.setAttribute('aria-current','page'); return link;
    };
    const appendPage=(parent,page)=>{
      const kids=childPages.get(page.path)||[];
      if(kids.length){
        const detail=make('details','nav-topic-parent');detail.open=lineage.has(page.path);
        detail.dataset.navKey='page:'+page.path; keyedDetails.set(detail.dataset.navKey,detail); pageDetails.set(page.path,detail);
        const summary=make('summary','nav-parent-summary');summary.append(linkFor(page));detail.append(summary);
        const content=make('div','nav-topic-children');
        let rendered=false;
        const renderChildren=()=>{if(rendered)return;rendered=true;for(const child of kids)appendPage(content,child);};
        renderers.set(detail, renderChildren);
        if(detail.open)renderChildren();
        detail.addEventListener('toggle',()=>{if(detail.open)renderChildren();});
        detail.append(content);parent.append(detail);
      } else {
        parent.append(linkFor(page));
        // Leaf headings describe the same topic; peer topics always open actual files.
        if(page.path===current && !page.topic_leaf && currentHeadings.length){
          const list=make('div','nav-toc');list.setAttribute('aria-label','이 페이지 목차');
          for(const h of currentHeadings){const item=make('a','nav-toc-link '+h.level.toLowerCase(),h.text);item.href='#'+encodeURIComponent(h.id);list.append(item);}parent.append(list);
        }
      }
    };
    const appendGroup=(target,name,items)=>{
      const detail=make('details','nav-details');detail.open=items.some(p=>lineage.has(p.path));
      detail.dataset.navKey='group:'+name+':'+items[0].path;keyedDetails.set(detail.dataset.navKey,detail);
      detail.append(make('summary','nav-summary',`${name} (${items.length})`));const content=make('div','nav-group');
      for(const p of items)appendPage(content,p);detail.append(content);target.append(detail);
    };
    for(const [name,items]of groups)appendGroup(nav,name,items);
    if(references.size){const outer=make('details','nav-details nav-reference');outer.dataset.navKey='reference:all';keyedDetails.set(outer.dataset.navKey,outer);outer.open=[...references.values()].some(xs=>xs.some(p=>lineage.has(p.path)));outer.append(make('summary','nav-summary','언어별 API 참조'));for(const [lang,items]of references)appendGroup(outer,languageLabel(lang),items);nav.append(outer);}
    const openEveryLevel = () => {
      const pending = [nav];
      while (pending.length) {
        const node = pending.pop();
        if (node.tagName === 'DETAILS') {
          renderers.get(node)?.();
          node.open = true;
        }
        for (const child of node.children) pending.push(child);
      }
    };
    const ensurePage = (path, depth = 0) => {
      if (depth > 20) return;
      const page = byPath.get(path);
      if (page?.parent) {
        ensurePage(page.parent, depth + 1);
        const parent = pageDetails.get(page.parent);
        if (parent) renderers.get(parent)?.();
      }
    };
    captureNavigation = () => ({
      expanded: [...keyedDetails].filter(([,node]) => node.open).map(([key]) => key),
      scrollTop: panel?.scrollTop || 0
    });
    const saveNavigation = () => {
      if (restoring) return;
      try { sessionStorage.setItem(stateKey, JSON.stringify(captureNavigation())); } catch (_) {}
    };
    const queueSave = () => {
      if (restoring) return;
      cancelAnimationFrame(saveFrame);
      saveFrame = requestAnimationFrame(saveNavigation);
    };
    restoreNavigation = snapshot => {
      if (!snapshot || !Array.isArray(snapshot.expanded)) return;
      const serial = ++restoreSerial; restoring = true;
      const expanded = new Set(snapshot.expanded.filter(key => typeof key === 'string'));
      for (const key of expanded) if (key.startsWith('page:')) ensurePage(key.slice(5));
      // Materialize open descendants now. Waiting for native toggle events
      // would insert rows after scroll restoration and move the scroll anchor.
      for (const key of expanded) {
        const node = keyedDetails.get(key);
        if (node) renderers.get(node)?.();
      }
      for (const [key,node] of keyedDetails) node.open = expanded.has(key);
      const top = Number.isFinite(snapshot.scrollTop) ? Math.max(0,snapshot.scrollTop) : 0;
      if (panel) panel.scrollTop = top;
      requestAnimationFrame(() => {
        if (serial !== restoreSerial) return;
        if (panel) panel.scrollTop = top;
        requestAnimationFrame(() => { if (serial === restoreSerial) { restoring = false; saveNavigation(); } });
      });
    };
    updatePage = path => {
      const top = panel?.scrollTop || 0;
      current = path; currentHeadings = collectHeadings(); ensurePage(path);
      for (const [key,link] of pageLinks) {
        link.classList.toggle('active', key === path);
        if (key === path) link.setAttribute('aria-current','page');
        else link.removeAttribute('aria-current');
      }
      nav.querySelectorAll('.nav-toc').forEach(node => node.remove());
      const page = byPath.get(path), link = pageLinks.get(path);
      if (page && link && !page.topic_leaf && !childPages.get(path)?.length && currentHeadings.length) {
        const list = make('div','nav-toc'); list.setAttribute('aria-label','이 페이지 목차');
        for (const h of currentHeadings) {
          const item = make('a','nav-toc-link '+h.level.toLowerCase(),h.text);
          item.href = href(path)+'#'+encodeURIComponent(h.id); list.append(item);
        }
        link.after(list);
      }
      if (panel) panel.scrollTop = top;
    };
    nav.addEventListener('toggle', queueSave, true);
    panel?.addEventListener('scroll', queueSave, {passive:true});
    window.addEventListener('pagehide', saveNavigation);
    document.addEventListener('zvision:before-page-change', saveNavigation);
    expandAll.addEventListener('click', () => {
      openEveryLevel();
      try { sessionStorage.setItem(expandKey, 'all'); } catch (_) {}
      saveNavigation();
    });
    collapseAll.addEventListener('click', () => {
      nav.querySelectorAll('details').forEach(detail => { detail.open = false; });
      try { sessionStorage.removeItem(expandKey); } catch (_) {}
      saveNavigation();
    });
    try {
      const saved = JSON.parse(sessionStorage.getItem(stateKey) || 'null');
      if (saved && Array.isArray(saved.expanded)) restoreNavigation(saved);
      else if (sessionStorage.getItem(expandKey) === 'all') openEveryLevel();
    } catch (_) {}
  }

  window.ZVisionManualShell = {captureNavigation, restoreNavigation, updatePage};

  const sidebar = document.querySelector('.sidebar');
  const menu = document.getElementById('menu-toggle');
  if (menu && sidebar) {
    sidebar.id ||= 'manual-sidebar';
    menu.setAttribute('aria-controls', sidebar.id);
    menu.setAttribute('aria-label', '목차 열기');
    const mobile = matchMedia('(max-width: 940px)');
    const setMenu = open => {
      document.body.classList.toggle('nav-open', open);
      sidebar.inert = mobile.matches && !open;
      if (mobile.matches && !open) sidebar.setAttribute('aria-hidden', 'true');
      else sidebar.removeAttribute('aria-hidden');
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? '목차 닫기' : '목차 열기');
    };
    setMenu(false);
    mobile.addEventListener('change', () => setMenu(false));
    menu.addEventListener('click', () => setMenu(!document.body.classList.contains('nav-open')));
    document.addEventListener('click', e => {
      if (document.body.classList.contains('nav-open') && !sidebar.contains(e.target) && !menu.contains(e.target)) setMenu(false);
    });
    sidebar.addEventListener('click', e => {
      if (e.target.closest('a') && matchMedia('(max-width: 940px)').matches) setMenu(false);
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && document.body.classList.contains('nav-open')) { setMenu(false); menu.focus(); }
    });
  }

  const themeButton = document.getElementById('theme-toggle');
  let theme = 'light';
  try { theme = localStorage.getItem('zvision-html-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); } catch (_) {}
  const setTheme = value => {
    document.documentElement.dataset.theme = value === 'dark' ? 'dark' : 'light';
    themeButton?.setAttribute('aria-label', value === 'dark' ? '밝은 테마로 변경' : '어두운 테마로 변경');
    themeButton?.setAttribute('aria-pressed', String(value === 'dark'));
  };
  setTheme(theme);
  themeButton?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('zvision-html-theme', next); } catch (_) {}
  });

  document.addEventListener('click', async e => {
    const button = e.target.closest('.copy');
    if (!button) return;
    const code = button.closest('.code')?.querySelector('pre code');
    if (!code) return;
    const old = button.textContent;
    try { await navigator.clipboard.writeText(code.textContent); button.textContent = '복사됨'; }
    catch (_) { button.textContent = '코드를 선택하여 복사'; }
    setTimeout(() => { button.textContent = old; }, 1800);
  });
  const topButtons = document.querySelector('.top-btns');
  if (topButtons && !document.getElementById('print-page')) {
    const button = make('button', 'control', '인쇄');
    button.type = 'button'; button.id = 'print-page';
    button.addEventListener('click', () => window.print());
    topButtons.append(button);
  }
  function revealHash() {
    if (!location.hash) return;
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const redirects = document.getElementById('page-redirects');
    if (redirects) {
      try { const target=JSON.parse(redirects.textContent)[id]; if(target){location.replace(href(target));return;} } catch (_) {}
    }
    let target = document.getElementById(id);
    if (!target) return;
    if (target.dataset.legacyTarget) target = document.getElementById(target.dataset.legacyTarget) || target;
    for (let node = target.parentElement; node; node = node.parentElement) if (node.tagName === 'DETAILS') node.open = true;
    if (target.tagName === 'DETAILS') target.open = true;
    requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
  }
  window.addEventListener('hashchange', revealHash);
  revealHash();
  let printOpened = [];
  window.addEventListener('beforeprint', () => {
    printOpened = [...document.querySelectorAll('.doc details:not([open])')];
    printOpened.forEach(item => { item.open = true; });
  });
  window.addEventListener('afterprint', () => {
    printOpened.forEach(item => { item.open = false; });
    printOpened = [];
  });

  const dialog = document.getElementById('search-dialog');
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  const trigger = document.getElementById('search-open');
  if (!dialog || !input || !results || !trigger) return;
  let previousFocus = null;
  const filters = make('div', 'search-filters');
  const langLabel = make('label', '', '언어 ');
  const lang = make('select'); lang.id = 'search-language'; lang.setAttribute('aria-label', '언어');
  const kindLabel = make('label', '', '종류 ');
  const kind = make('select'); kind.id = 'search-kind'; kind.setAttribute('aria-label', '종류');
  langLabel.append(lang); kindLabel.append(kind); filters.append(langLabel, kindLabel);
  const status = make('p', 'search-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  results.before(filters, status);
  const addOption = (select, value, text) => { const option = make('option', '', text); option.value = value; select.append(option); };
  addOption(lang, '', '모든 언어'); addOption(kind, '', '모든 종류');
  const languages = new Map();
  const kinds = new Set(['페이지', 'API', '멤버']);
  for (const p of pages) { const l = languageOfPath(p.path); if (l) languages.set(l, languageLabel(l)); }
  function populateFilters() {
    for (const api of apis) {
      const l = languageKey(api.language); if (l) languages.set(l, languageLabel(api.language));
      if (api.kind) kinds.add(kindName(api.kind));
      for (const member of api.members || []) if (member.kind) kinds.add(kindName(member.kind));
    }
    const selectedLanguage = lang.value, selectedKind = kind.value;
    lang.replaceChildren(); kind.replaceChildren();
    addOption(lang, '', '모든 언어'); addOption(kind, '', '모든 종류');
    [...languages].sort((a, b) => a[1].localeCompare(b[1])).forEach(([v, label]) => addOption(lang, v, label));
    [...kinds].sort((a, b) => a.localeCompare(b)).forEach(k => addOption(kind, k, k));
    lang.value = selectedLanguage; kind.value = selectedKind;
  }
  populateFilters();
  function loadApis() {
    if (!data.apiIndex || apiLoadState === 'ready') return Promise.resolve();
    if (apiLoadPromise) return apiLoadPromise;
    apiLoadState = 'loading';
    apiLoadPromise = fetch(href(data.apiIndex) + (data.version ? '?v=' + encodeURIComponent(data.version) : ''))
      .then(response => { if (!response.ok) throw new Error('API index unavailable'); return response.json(); })
      .then(index => {
        if (!Array.isArray(index)) throw new Error('Invalid API index');
        apis = index;
        apiLoadState = 'ready';
        populateFilters();
      })
      .catch(() => { apiLoadState = 'error'; })
      .finally(() => { apiLoadPromise = null; if (dialog.open) render(); });
    return apiLoadPromise;
  }
  const limit = 40;
  function render() {
    const terms = normal(input.value).trim().split(/\s+/u).filter(Boolean);
    results.replaceChildren();
    const loadNote = apiLoadState === 'loading' ? ' API 색인을 불러오는 중입니다.' : apiLoadState === 'error' ? ' API 색인을 불러오지 못했습니다. 페이지 검색만 가능합니다. 검색창을 다시 열어 재시도하세요.' : '';
    if (!terms.length) { status.textContent = '검색어를 입력하세요. 공백으로 여러 단어를 함께 찾습니다.' + loadNote; return; }
    const found = [];
    let count = 0;
    function consider(name, language, type, link, context, description, keywords='') {
      type = kindName(type);
      if (!link || (lang.value && languageKey(language) !== lang.value) || (kind.value && type !== kind.value)) return;
      const n = normal(name), ctx = normal(context), text = normal([name, language, type, context, description, keywords].join(' '));
      if (!terms.every(t => text.includes(t))) return;
      count++;
      const joined = terms.join(' ');
      const score = n === joined ? 0 : n.startsWith(joined) ? 1 : n.includes(joined) ? 2 : ctx.includes(joined) ? 3 : 4;
      const record = {name, language, type, link, context, description, score};
      // Keep only 40 best records rather than creating a second full member index.
      let pos = found.findIndex(item => score < item.score);
      if (pos < 0) pos = found.length;
      if (pos < limit) { found.splice(pos, 0, record); if (found.length > limit) found.pop(); }
    }
    for (const p of pages) consider(p.title, languageOfPath(p.path), '페이지', p.path, p.group, p.description);
    for (const api of apis) {
      consider(api.name, api.language, api.kind || 'API', api.href, '', api.summary || '', api.keywords);
      for (const member of api.members || []) consider(member.name, api.language, member.kind || '멤버', member.href, api.name, member.summary || member.signature || '', member.keywords);
    }
    const fragment = document.createDocumentFragment();
    for (const r of found) {
      const li = make('li'); const a = make('a', '', r.name); a.href = href(r.link);
      const meta = make('small', '', [languageLabel(r.language), r.type, r.context, r.description].filter(Boolean).join(' · '));
      a.append(meta); li.append(a); fragment.append(li);
    }
    results.append(fragment);
    status.textContent = (count ? `${count}개 중 ${found.length}개 표시` : '일치하는 결과가 없습니다.') + loadNote;
  }
  let timer;
  function queueRender() { clearTimeout(timer); timer = setTimeout(render, 100); }
  input.addEventListener('input', queueRender); lang.addEventListener('change', render); kind.addEventListener('change', render);
  function openSearch() {
    if (dialog.open) { input.focus(); return; }
    previousFocus = document.activeElement;
    input.value = ''; lang.value = ''; kind.value = '';
    loadApis(); render();
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    input.focus();
  }
  function closeSearch() {
    if (typeof dialog.close === 'function' && dialog.open) dialog.close();
    else { dialog.removeAttribute('open'); previousFocus?.focus(); }
  }
  trigger.addEventListener('click', openSearch);
  document.getElementById('search-close')?.addEventListener('click', closeSearch);
  dialog.addEventListener('close', () => previousFocus?.focus());
  dialog.addEventListener('click', e => { if (e.target === dialog) closeSearch(); });
  dialog.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); closeSearch(); }
    if (e.key === 'ArrowDown' && e.target === input) { const first = results.querySelector('a'); if (first) { e.preventDefault(); first.focus(); } }
  });
  document.addEventListener('keydown', e => {
    const editable = e.target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])');
    if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') || (e.key === '/' && !editable && !e.altKey && !e.ctrlKey && !e.metaKey)) {
      e.preventDefault(); openSearch();
    }
  });
})();
