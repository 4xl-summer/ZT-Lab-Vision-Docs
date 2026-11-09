"use strict";
(() => {
  const script = document.currentScript;
  const version = script?.src ? new URL(script.src).searchParams.get('v') : null;
  const rootMeta = document.querySelector('meta[name="manual-root"]');
  if (!rootMeta || !document.getElementById('main') || !Array.isArray(window.MANUAL_DATA?.pages)) return;
  const initialBase = document.baseURI;
  const brand = document.querySelector('.sidebar .brand[href]');
  if (brand) brand.setAttribute('href', new URL(brand.getAttribute('href'), initialBase).href);
  for (const link of document.querySelectorAll('head link[rel="stylesheet"][href]')) {
    link.setAttribute('href', new URL(link.getAttribute('href'), initialBase).href);
  }
  const manualRoot = new URL(rootMeta.content, document.baseURI);
  const known = new Set(window.MANUAL_DATA.pages.map(page => page.path).filter(Boolean));
  const stateKey = '__zvisionNavigation';
  let requestNumber = 0, controller = null, loading = false;
  let widgetAssets;
  const assetUrl = name => {
    const url = new URL('assets/' + name, manualRoot);
    if (version) url.searchParams.set('v', version);
    return url.href;
  };
  function pathOf(url) {
    if (url.origin !== manualRoot.origin || !url.pathname.startsWith(manualRoot.pathname)) return null;
    let rel;
    try { rel = decodeURIComponent(url.pathname.slice(manualRoot.pathname.length)); } catch (_) { return null; }
    return known.has(rel) && rel.endsWith('.html') ? rel : null;
  }
  function saveScroll() {
    if (loading) return;
    const state = {...(history.state || {}), [stateKey]: {x: scrollX, y: scrollY}};
    try { history.replaceState(state, '', location.href); } catch (_) {}
  }
  try { history.scrollRestoration = 'manual'; } catch (_) {}
  window.addEventListener('scroll', saveScroll, {passive: true});
  window.addEventListener('pagehide', saveScroll);
  saveScroll();

  function redirects(doc) {
    const element = doc.getElementById('page-redirects');
    if (!element) return {};
    const parsed = JSON.parse(element.textContent || '{}');
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw Error('Invalid page redirects');
    return parsed;
  }
  function aliasTarget(doc, url) {
    if (!url.hash) return null;
    let hash;
    try { hash = decodeURIComponent(url.hash.slice(1)); } catch (_) { throw Error('Invalid fragment'); }
    const target = redirects(doc)[hash];
    if (target == null) return null;
    if (typeof target !== 'string') throw Error('Invalid redirect target');
    const next = new URL(target, manualRoot);
    if (!pathOf(next)) throw Error('Unknown redirect target');
    return next;
  }
  function scrollToHash(url) {
    if (!url.hash) { window.scrollTo({left:0, top:0, behavior:'instant'}); return; }
    let id;
    try { id = decodeURIComponent(url.hash.slice(1)); } catch (_) { return; }
    let element = document.getElementById(id);
    if (!element) return;
    if (element.dataset.legacyTarget) element = document.getElementById(element.dataset.legacyTarget) || element;
    for (let parent = element.parentElement; parent; parent = parent.parentElement) if (parent.tagName === 'DETAILS') parent.open = true;
    if (element.tagName === 'DETAILS') element.open = true;
    element.scrollIntoView({block:'start', behavior:'instant'});
  }
  function loadWidgetAssets() {
    if (widgetAssets) return widgetAssets;
    const cssUrl = assetUrl('measurement-lab.css'), jsUrl = assetUrl('measurement-lab.js');
    const css = [...document.querySelectorAll('link[rel="stylesheet"]')].find(e => e.href.split('?')[0] === cssUrl.split('?')[0]);
    const cssReady = css ? Promise.resolve() : new Promise((resolve, reject) => {
      const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = cssUrl;
      link.onload = resolve; link.onerror = () => reject(Error('Measurement stylesheet failed')); document.head.append(link);
    });
    const jsReady = window.ZVisionMeasurement ? Promise.resolve() : new Promise((resolve, reject) => {
      const element = document.createElement('script'); element.src = jsUrl;
      element.onload = () => window.ZVisionMeasurement ? resolve() : reject(Error('Measurement module unavailable'));
      element.onerror = () => reject(Error('Measurement module failed')); document.head.append(element);
    });
    widgetAssets = Promise.all([cssReady, jsReady]);
    return widgetAssets;
  }
  function setMeta(name, value) {
    let meta = document.querySelector(`meta[name="${name}"]`);
    if (!meta) { meta = document.createElement('meta'); meta.name = name; document.head.append(meta); }
    meta.content = value;
  }
  function rebase(main, base) {
    for (const element of main.querySelectorAll('[href], [src]')) for (const attr of ['href','src']) {
      if (!element.hasAttribute(attr)) continue;
      const value = element.getAttribute(attr);
      if (attr === 'href' && value?.startsWith('#') && element.namespaceURI === 'http://www.w3.org/2000/svg') continue;
      if (value) element.setAttribute(attr, new URL(value, base).href);
    }
    for (const node of main.querySelectorAll('script')) if (node.type !== 'application/json') node.remove();
  }
  function pageVersion(doc, url) {
    const element = [...doc.querySelectorAll('script[src]')].find(e => new URL(e.getAttribute('src'), url).pathname.endsWith('/assets/manual-navigation.js'));
    return element ? new URL(element.getAttribute('src'), url).searchParams.get('v') : undefined;
  }
  async function navigate(initial, options = {}) {
    controller?.abort(); controller = new AbortController();
    const signal = controller.signal, serial = ++requestNumber;
    loading = true;
    let url = new URL(initial.href), doc, incoming, path;
    try {
      for (let depth = 0; depth < 9; depth++) {
        if (depth === 8) throw Error('Redirect limit');
        path = pathOf(url); if (!path) throw Error('Unknown page');
        const response = await fetch(url.href, {signal});
        if (!response.ok) throw Error(`Page fetch failed: ${response.status}`);
        if (new URL(response.url).pathname !== url.pathname) throw Error('Unexpected HTTP redirect');
        doc = new DOMParser().parseFromString(await response.text(), 'text/html');
        incoming = doc.getElementById('main');
        if (!incoming || doc.querySelector('meta[name="manual-path"]')?.content !== path) throw Error('Invalid manual page');
        if (pageVersion(doc, url) !== version) throw Error('Manual version changed');
        const next = aliasTarget(doc, url);
        if (!next) break;
        url = next;
      }
      if (incoming.querySelector('#measurement-lab')) await loadWidgetAssets();
      if (signal.aborted || serial !== requestNumber) return;
      const shell = window.ZVisionManualShell;
      const snapshot = options.navigationSnapshot ?? shell?.captureNavigation?.();
      const dialog = document.getElementById('search-dialog');
      if (dialog?.open) {
        if (typeof dialog.close === 'function') dialog.close();
        else dialog.removeAttribute('open');
      }
      const currentMain = document.getElementById('main');
      if (!currentMain) throw Error('Missing current content');
      rebase(incoming, url);
      if (options.push) { loading = false; saveScroll(); loading = true; }
      document.dispatchEvent(new CustomEvent('zvision:before-page-change', {detail:{path,url:url.href}}));
      window.ZVisionMeasurement?.unmount?.();
      currentMain.replaceWith(document.importNode(incoming, true));
      document.title = doc.title;
      setMeta('manual-path', path);
      setMeta('manual-root', manualRoot.href);
      setMeta('description', doc.querySelector('meta[name="description"]')?.content || '');
      const existingRedirects = document.getElementById('page-redirects');
      const newRedirects = doc.getElementById('page-redirects');
      if (existingRedirects) existingRedirects.remove();
      if (newRedirects) document.body.append(document.importNode(newRedirects, true));
      document.body.classList.toggle('measurement-page', doc.body.classList.contains('measurement-page'));
      if (options.push) history.pushState({[stateKey]:{x:0,y:0}}, '', url.href);
      else if (location.href !== url.href) history.replaceState(history.state, '', url.href);
      shell?.updatePage?.(path);
      shell?.restoreNavigation?.(snapshot);
      if (document.getElementById('measurement-lab')) window.ZVisionMeasurement?.mount?.();
      document.dispatchEvent(new CustomEvent('zvision:page-changed', {detail:{path,url:url.href}}));
      loading = false;
      if (options.pop && options.state?.[stateKey]) {
        const pos = options.state[stateKey]; window.scrollTo({left:pos.x || 0, top:pos.y || 0, behavior:'instant'});
      } else scrollToHash(url);
      saveScroll();
    } catch (error) {
      if (signal.aborted || serial !== requestNumber) return;
      loading = false;
      if (options.pop) location.reload(); else location.assign(url.href);
    }
  }
  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest?.('a[href]');
    if (!link || link.hasAttribute('download') || (link.target && link.target.toLowerCase() !== '_self')) return;
    let url; try { url = new URL(link.href, document.baseURI); } catch (_) { return; }
    if (!pathOf(url)) return;
    if (url.pathname === location.pathname && url.search === location.search && url.hash) {
      try {
        if (!aliasTarget(document, url)) {
          controller?.abort(); ++requestNumber; loading = false;
          return;
        }
      } catch (_) { controller?.abort(); ++requestNumber; loading = false; return; }
    }
    const mobileSidebar = link.closest('.sidebar') && matchMedia('(max-width: 940px)').matches;
    const navigationSnapshot = mobileSidebar ? window.ZVisionManualShell?.captureNavigation?.() : undefined;
    event.preventDefault(); navigate(url, {push:true,navigationSnapshot});
  }, true);
  window.addEventListener('popstate', event => {
    const url = new URL(location.href);
    if (!pathOf(url)) { location.reload(); return; }
    const current = document.querySelector('meta[name="manual-path"]')?.content;
    if (pathOf(url) === current) {
      controller?.abort(); ++requestNumber; loading = false;
      if (event.state?.[stateKey]) window.scrollTo({left:event.state[stateKey].x || 0, top:event.state[stateKey].y || 0, behavior:'instant'});
      else scrollToHash(url);
      return;
    }
    navigate(url, {pop:true,state:event.state});
  });
})();
