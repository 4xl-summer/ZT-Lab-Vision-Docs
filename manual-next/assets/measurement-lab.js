(() => {
  'use strict';
  const app = document.getElementById('measurement-lab');
  if (!app) return;
  const $ = (id) => document.getElementById(id);
  const status = $('mlab-status'), workspace = $('mlab-workspace');
  const canvas = $('mlab-canvas'), context = canvas.getContext('2d');
  const stage = $('mlab-stage'), shell = $('mlab-image-shell'), pixel = $('mlab-pixel');
  const imageError = $('mlab-image-error'), crosshair = $('mlab-crosshair');
  const rootMeta = document.querySelector('meta[name="manual-root"]');
  const manualRoot = new URL(rootMeta?.content || '../', document.baseURI);
  const assetRoot = new URL('assets/measurement/', manualRoot);
  const state = { data: null, cases: [], current: null, image: null, pixels: null, layers: [], layer: 0, zoom: null, cursor: null, request: 0, overlayAllowed: true };
  const finite = (value) => typeof value === 'number' && Number.isFinite(value);
  const text = (value, fallback = '—') => value === null || value === undefined || value === '' ? fallback : String(value);
  const categoryNames = {blob:'연결 성분',circle:'원 측정',profile:'프로파일',color:'색상',inspection:'검사 차분',statistics:'밝기 통계'};
  const categoryLabel = (value) => categoryNames[String(value || '').toLowerCase()] || (/[가-힣]/.test(String(value || '')) ? String(value) : '계측');
  const fmt = (value) => finite(value) ? new Intl.NumberFormat('ko-KR', {maximumFractionDigits: 4}).format(value) : text(value);
  const array = (value) => Array.isArray(value) ? value : [];
  const element = (tag, className, content) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  };
  const clear = (node) => { node.replaceChildren(); };
  function localUrl(path, base) {
    if (typeof path !== 'string' || !path.trim()) return null;
    try {
      const url = new URL(path, base);
      if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname) || !['http:', 'https:', 'file:'].includes(url.protocol)) return null;
      return url.href;
    } catch (_) { return null; }
  }
  function externalUrl(path) {
    try { const url = new URL(path); return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null; }
    catch (_) { return null; }
  }
  function safeLink(label, url, className) {
    if (!url) return null;
    const link = element('a', className, label);
    link.href = url;
    return link;
  }
  function showError(message) {
    status.textContent = message;
    status.classList.add('is-error');
    status.hidden = false;
    workspace.hidden = true;
  }
  function initCases() {
    const holder = $('mlab-case-list'); clear(holder);
    $('mlab-case-count').textContent = `${state.cases.length}개`;
    state.cases.forEach((item, index) => {
      const button = element('button', 'mlab-case-button');
      button.type = 'button';
      button.setAttribute('aria-pressed', item === state.current ? 'true' : 'false');
      button.append(element('span', 'mlab-case-number', String(index + 1).padStart(2, '0')));
      const labels = element('span', 'mlab-case-text');
      labels.append(element('strong', '', text(item.title, '계측 예제')), element('small', '', categoryLabel(item.category)));
      button.append(labels);
      button.addEventListener('click', () => selectCase(index, true));
      holder.append(button);
    });
  }
  function selectCase(index, updateHash = false) {
    const item = state.cases[index];
    if (!item) return;
    state.current = item;
    if (updateHash && item.id) {
      const location = new URL(window.location.href);
      location.hash = encodeURIComponent(String(item.id));
      window.history.replaceState(window.history.state, '', location.href);
    }
    state.layer = 0; state.zoom = null; state.cursor = null;
    state.image = null; state.pixels = null; state.request++; crosshair.hidden = true;
    canvas.width = 1; canvas.height = 1;
    context.clearRect(0, 0, 1, 1);
    pixel.textContent = '좌표 — · 픽셀 —';
    imageError.hidden = true;
    $('mlab-overlay').checked = true;
    $('mlab-overlay').disabled = false;
    $('mlab-category').textContent = categoryLabel(item.category);
    $('mlab-case-title').textContent = text(item.title, '계측 예제');
    $('mlab-description').textContent = text(item.description, '');
    const original = localUrl(item.image?.original, assetRoot);
    const originalLink = $('mlab-original-link');
    if (original) { originalLink.href = original; originalLink.hidden = false; }
    else { originalLink.removeAttribute('href'); originalLink.hidden = true; }
    initCases(); buildLayers(); renderDetails(); loadLayer();
  }
  function buildLayers() {
    const item = state.current;
    const layers = [{label: '원본', path: item.image?.original, description: '입력 사진'}];
    const seen = new Set(layers.map((v) => v.path).filter(Boolean));
    if (item.image?.gray && !seen.has(item.image.gray)) {
      layers.push({label: '그레이', path: item.image.gray, description: '회색조 입력'});
      seen.add(item.image.gray);
    }
    array(item.steps).forEach((step, index) => {
      // Pre-rendered overlay previews already contain marks; show geometry separately
      // so that the user's overlay switch actually hides every annotation.
      if (!step || !step.image || /^overlay\//i.test(step.image) || seen.has(step.image)) return;
      layers.push({label: text(step.label, `단계 ${index + 1}`), path: step.image, description: text(step.description, '')});
      seen.add(step.image);
    });
    state.layers = layers;
    const holder = $('mlab-layers'); clear(holder);
    layers.forEach((layer, index) => {
      const button = element('button', 'mlab-layer-button', layer.label);
      button.type = 'button'; button.title = layer.description;
      button.setAttribute('aria-pressed', index === state.layer ? 'true' : 'false');
      button.addEventListener('click', () => {
        state.layer = index; state.cursor = null; crosshair.hidden = true; pixel.textContent = '좌표 — · 픽셀 —';
        [...holder.children].forEach((v, i) => v.setAttribute('aria-pressed', i === index ? 'true' : 'false'));
        loadLayer();
      });
      holder.append(button);
    });
  }
  function loadLayer() {
    const layer = state.layers[state.layer];
    const url = layer && localUrl(layer.path, assetRoot);
    const ticket = ++state.request;
    state.image = null; state.pixels = null;
    imageError.hidden = true; imageError.classList.remove('is-notice');
    canvas.width = 1; canvas.height = 1;
    if (!url) { imageError.textContent = '이 단계의 이미지 경로를 확인할 수 없습니다.'; imageError.hidden = false; return; }
    const img = new Image();
    img.onload = () => {
      if (ticket !== state.request) return;
      state.image = img;
      const expected = state.current.image || {};
      state.overlayAllowed = !(finite(expected.width) && finite(expected.height)) || (expected.width === img.naturalWidth && expected.height === img.naturalHeight);
      $('mlab-overlay').disabled = !state.overlayAllowed;
      if (!state.overlayAllowed) {
        imageError.textContent = '이 단계의 이미지 크기가 원본과 달라 좌표 오버레이를 표시하지 않습니다.';
        imageError.classList.add('is-notice'); imageError.hidden = false;
      }
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      const sample = document.createElement('canvas'); sample.width = img.naturalWidth; sample.height = img.naturalHeight;
      try {
        const sampleContext = sample.getContext('2d', {willReadFrequently: true});
        sampleContext.drawImage(img, 0, 0);
        state.pixels = sampleContext.getImageData(0, 0, sample.width, sample.height).data;
      } catch (_) { state.pixels = null; }
      draw(); resizeImage();
    };
    img.onerror = () => {
      if (ticket !== state.request) return;
      state.image = null; state.pixels = null;
      canvas.width = 1; canvas.height = 1;
      imageError.textContent = '이미지를 불러오지 못했습니다. 예제 데이터와 사진 경로를 확인하세요.';
      imageError.hidden = false;
    };
    img.src = url;
  }
  function fitZoom() {
    if (!state.image) return 1;
    return Math.max(.05, Math.min(2, (stage.clientWidth - 36) / canvas.width, (stage.clientHeight - 36) / canvas.height));
  }
  function actualZoom() { return state.zoom === null ? fitZoom() : state.zoom; }
  function resizeImage() {
    if (!state.image) return;
    const z = actualZoom();
    canvas.style.width = `${Math.max(1, canvas.width * z)}px`;
    canvas.style.height = `${Math.max(1, canvas.height * z)}px`;
    canvas.style.imageRendering = z >= 2 ? 'pixelated' : 'auto';
    $('mlab-zoom-value').textContent = `${Math.round(z * 100)}%`;
    if (state.cursor) positionCrosshair(state.cursor.x, state.cursor.y);
    $('mlab-zoom-fit').setAttribute('aria-pressed', state.zoom === null ? 'true' : 'false');
  }
  function changeZoom(factor) {
    if (!state.image) return;
    state.zoom = Math.max(.1, Math.min(8, actualZoom() * factor));
    resizeImage();
  }
  let labelRects = [];
  function labelAt(label, x, y, color, fontSize) {
    if (!label || !finite(x) || !finite(y)) return;
    const message = String(label);
    context.font = `600 ${fontSize}px sans-serif`;
    const w = Math.min(canvas.width, context.measureText(message).width + fontSize), h = fontSize * 1.42;
    const candidates = [[x,y-h-4],[x,y+4],[x-w-4,y-h-4],[x-w-4,y+4],[x,y-h*2-8]].map(([left,top]) => ({left:Math.max(0,Math.min(canvas.width-w,left)),top:Math.max(0,Math.min(canvas.height-h,top)),w,h}));
    const overlap = (a,b) => Math.max(0, Math.min(a.left+a.w,b.left+b.w+3)-Math.max(a.left,b.left-3)) * Math.max(0, Math.min(a.top+a.h,b.top+b.h+3)-Math.max(a.top,b.top-3));
    candidates.sort((a,b) => labelRects.reduce((s,r)=>s+overlap(a,r),0)-labelRects.reduce((s,r)=>s+overlap(b,r),0));
    const chosen=candidates[0], {left,top}=chosen; labelRects.push(chosen);
    context.fillStyle = 'rgba(8,27,23,.86)'; context.fillRect(left, top, w, h);
    context.fillStyle = color; context.textBaseline = 'middle'; context.fillText(message, left + fontSize * .5, top + fontSize * .73);
  }
  function draw() {
    if (!state.image) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    labelRects = [];
    context.drawImage(state.image, 0, 0);
    if (!$('mlab-overlay').checked || !state.overlayAllowed) return;
    const item = state.current, geometry = item.geometry || {}, roi = item.roi;
    const scale = Math.max(1, Math.min(canvas.width, canvas.height) / 350);
    const fontSize = Math.max(9, Math.min(19, 12 * scale));
    context.save(); context.lineWidth = Math.max(1.5, 2 * scale); context.lineJoin = 'round';
    if (roi && [roi.x, roi.y, roi.width, roi.height].every(finite) && roi.width > 0 && roi.height > 0) {
      context.strokeStyle = '#f8fbfb'; context.setLineDash([6 * scale, 4 * scale]);
      context.strokeRect(roi.x, roi.y, roi.width, roi.height); context.setLineDash([]);
      labelAt(text(item.roi_label, '표시 영역'), roi.x, roi.y, '#fff', fontSize);
    }
    array(geometry.boxes).forEach((v, i) => {
      if (!v || ![v.x,v.y,v.width,v.height].every(finite)) return;
      context.strokeStyle = '#ffda55'; context.strokeRect(v.x, v.y, v.width, v.height);
      labelAt(text(v.label, `영역 ${i + 1}`), v.x, v.y, '#ffe78e', fontSize);
    });
    array(geometry.circles).forEach((v, i) => {
      if (!v || ![v.cx,v.cy,v.radius].every(finite) || v.radius < 0) return;
      context.strokeStyle = '#a6f07d'; context.beginPath(); context.arc(v.cx, v.cy, v.radius, 0, Math.PI * 2); context.stroke();
      context.beginPath(); context.moveTo(v.cx-4*scale,v.cy); context.lineTo(v.cx+4*scale,v.cy); context.moveTo(v.cx,v.cy-4*scale); context.lineTo(v.cx,v.cy+4*scale); context.stroke();
      labelAt(text(v.label, `원 ${i + 1}`), v.cx - v.radius, v.cy + v.radius + fontSize*1.8, '#d4ffc4', fontSize);
    });
    array(geometry.lines).forEach((v, i) => {
      if (!v || ![v.x1,v.y1,v.x2,v.y2].every(finite)) return;
      context.strokeStyle = '#55dceb'; context.beginPath(); context.moveTo(v.x1,v.y1); context.lineTo(v.x2,v.y2); context.stroke();
      labelAt(text(v.label, `선 ${i + 1}`), v.x1, v.y1, '#b5f6ff', fontSize);
    });
    array(geometry.points).forEach((v, i) => {
      if (!v || ![v.x,v.y].every(finite)) return;
      context.strokeStyle = '#ff8f85'; context.beginPath(); context.arc(v.x,v.y,4*scale,0,Math.PI*2); context.stroke();
      const circleCenter = array(geometry.circles).some(c => c && Math.hypot(c.cx-v.x,c.cy-v.y)<.001);
      if(!circleCenter)labelAt(text(v.label, `점 ${i + 1}`), v.x+7*scale,v.y+fontSize*1.8, '#ffd1cc', fontSize);
    });
    context.restore();
  }
  function positionCrosshair(x, y) {
    crosshair.hidden = false;
    crosshair.style.left = `${18 + (x + .5) * canvas.clientWidth / canvas.width}px`;
    crosshair.style.top = `${18 + (y + .5) * canvas.clientHeight / canvas.height}px`;
  }
  function inspect(x, y, announce = false) {
    if (!state.image) return;
    x = Math.max(0, Math.min(canvas.width - 1, Math.floor(x)));
    y = Math.max(0, Math.min(canvas.height - 1, Math.floor(y)));
    state.cursor = {x,y}; positionCrosshair(x,y);
    let value = '픽셀 값 확인 불가';
    if (state.pixels) {
      const i = (y * canvas.width + x) * 4, p = state.pixels;
      const [r,g,b,a] = [p[i],p[i+1],p[i+2],p[i+3]];
      value = r === g && g === b ? `밝기 ${r}` : `RGB ${r}, ${g}, ${b}`;
      if (a !== 255) value += ` · A ${a}`;
    }
    pixel.textContent = `x ${x}, y ${y} px · ${value}`;
    if (announce) pixel.setAttribute('aria-live', 'polite');
  }
  canvas.addEventListener('pointermove', (event) => {
    pixel.setAttribute('aria-live', 'off');
    const rect = canvas.getBoundingClientRect();
    inspect((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height);
  });
  canvas.addEventListener('click', (event) => {
    const rect = canvas.getBoundingClientRect();
    inspect((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height, true);
    stage.focus({preventScroll:true});
  });
  stage.addEventListener('keydown', (event) => {
    if (event.key === '+' || event.key === '=') { event.preventDefault(); changeZoom(1.25); return; }
    if (event.key === '-') { event.preventDefault(); changeZoom(.8); return; }
    const delta = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
    if (delta && state.image) {
      event.preventDefault(); const current = state.cursor || {x:0,y:0};
      const step = event.shiftKey ? 10 : 1;
      inspect(current.x + delta[0] * step, current.y + delta[1] * step, true);
    }
  });
  $('mlab-overlay').addEventListener('change', draw);
  $('mlab-zoom-in').addEventListener('click', () => changeZoom(1.25));
  $('mlab-zoom-out').addEventListener('click', () => changeZoom(.8));
  $('mlab-zoom-fit').addEventListener('click', () => { state.zoom = null; resizeImage(); });
  window.addEventListener('resize', () => { if (state.zoom === null) resizeImage(); });
  function geometryRows(item) {
    const list = [];
    if (item.roi && [item.roi.x,item.roi.y,item.roi.width,item.roi.height].every(finite)) {
      const r=item.roi; list.push([text(item.roi_label, '표시 영역'), `x ${fmt(r.x)}, y ${fmt(r.y)} · ${fmt(r.width)} × ${fmt(r.height)} px`]);
    }
    const g=item.geometry || {};
    array(g.circles).forEach((v,i) => { if (v && [v.cx,v.cy,v.radius].every(finite)) list.push([text(v.label, `원 ${i+1}`), `중심 (${fmt(v.cx)}, ${fmt(v.cy)}) · 반경 ${fmt(v.radius)} px`]); });
    array(g.lines).forEach((v,i) => { if (v && [v.x1,v.y1,v.x2,v.y2].every(finite)) list.push([text(v.label, `선 ${i+1}`), `(${fmt(v.x1)}, ${fmt(v.y1)}) → (${fmt(v.x2)}, ${fmt(v.y2)}) px`]); });
    array(g.boxes).forEach((v,i) => { if (v && [v.x,v.y,v.width,v.height].every(finite)) list.push([text(v.label, `영역 ${i+1}`), `(${fmt(v.x)}, ${fmt(v.y)}) · ${fmt(v.width)} × ${fmt(v.height)} px`]); });
    array(g.points).forEach((v,i) => { if (v && [v.x,v.y].every(finite)) list.push([text(v.label, `점 ${i+1}`), `(${fmt(v.x)}, ${fmt(v.y)}) px`]); });
    return list;
  }
  function renderDetails() {
    const item = state.current;
    const metrics=$('mlab-metrics');clear(metrics);
    array(item.metrics).forEach((v) => {
      if (!v) return;
      const card=element('div','mlab-metric'); card.append(element('span','mlab-metric-label',text(v.label,'결과')));
      const number=element('span','mlab-metric-value'); number.append(document.createTextNode(fmt(v.value)));
      if (v.unit) number.append(element('span','mlab-metric-unit',String(v.unit)));
      card.append(number); if (v.meaning) card.append(element('small','',String(v.meaning))); metrics.append(card);
    });
    if (!metrics.childElementCount) metrics.append(element('p','mlab-empty','기록된 수치가 없습니다.'));
    const verification=$('mlab-verification');clear(verification);
    if (typeof item.verification?.method === 'string' && item.verification.method.trim()) {
      verification.append(element('strong','','확인한 내용'),element('p','',item.verification.method));
      verification.hidden=false;
    } else verification.hidden=true;
    const region=$('mlab-processing-region');clear(region);
    if (typeof item.processing_region === 'string' && item.processing_region.trim()) {
      region.append(element('strong','','처리 범위'),element('p','',item.processing_region));
      region.hidden=false;
    } else region.hidden=true;
    const geometries=$('mlab-geometry-list');clear(geometries);
    const rows=geometryRows(item);
    if (rows.length) {
      const ul=element('ul','mlab-geometry-list');
      rows.forEach(([name,detail]) => {const li=element('li');li.append(element('span','',name),element('small','',detail));ul.append(li);});geometries.append(ul);
    } else geometries.append(element('p','mlab-empty','표시할 형상이 없습니다.'));
    const steps=$('mlab-steps');clear(steps);
    array(item.steps).forEach((v) => {
      if (!v) return;const li=element('li');li.append(element('strong','',text(v.label,'처리 단계')));
      if(v.api)li.append(element('code','',String(v.api)));if(v.description)li.append(element('p','',String(v.description)));steps.append(li);
    });
    if (!steps.childElementCount) steps.append(element('li','mlab-empty','기록된 처리 단계가 없습니다.'));
    const plotPanel=$('mlab-plots-panel'), plots=$('mlab-plots');clear(plots);
    array(item.plots).forEach((v) => {
      if (!v) return;
      const url = localUrl(v.image, assetRoot); if (!url) return;
      const figure=element('figure','mlab-plot');
      const plotTitle=text(v.title,'표본 그래프'), description=text(v.description,'');
      const image=element('img');image.src=url;image.alt=description ? `${plotTitle}: ${description}` : plotTitle;
      image.loading='lazy';image.decoding='async';
      const caption=element('figcaption');caption.append(element('strong','',plotTitle));
      if(description)caption.append(element('span','',description));
      figure.append(image,caption);plots.append(figure);
    });
    plotPanel.hidden=!plots.childElementCount;
    const params=$('mlab-parameters');clear(params);
    array(item.parameters).forEach((v) => {
      if(!v)return;const row=element('div');row.append(element('dt','',text(v.name,'설정')));const dd=element('dd','',fmt(v.value));
      if(v.meaning)dd.append(element('small','',String(v.meaning)));row.append(dd);params.append(row);
    });
    if (!params.childElementCount) params.append(element('div','mlab-empty','별도로 기록된 설정이 없습니다.'));
    const apis=$('mlab-api-links');clear(apis);
    array(item.api_links).forEach((v)=>{if(!v)return;const link=safeLink(text(v.label,'API 참조'),localUrl(v.path,manualRoot));if(link)apis.append(link);});
    if(!apis.childElementCount)apis.append(element('span','mlab-empty','연결된 API 참조가 없습니다.'));
    const source=$('mlab-source');clear(source);
    const sourceInfo=item.source || {};source.append(element('strong','',text(sourceInfo.label,'사진 출처')));
    const details=[sourceInfo.author,sourceInfo.license].filter(Boolean).join(' · ');if(details)source.append(element('p','',details));
    const sourceLink=safeLink('출처 및 이용 조건 보기 ↗',externalUrl(sourceInfo.url));if(sourceLink){sourceLink.target='_blank';sourceLink.rel='noopener noreferrer';source.append(sourceLink);}
    const warnings=$('mlab-warnings');clear(warnings);
    array(item.warnings).forEach((warning)=>warnings.append(element('p','',`※ ${text(warning)}`)));
  }
  $('mlab-download').addEventListener('click', () => {
    if(!state.current)return;
    const content={version:state.data.version,sdk_revision:state.data.sdk_revision,cases:[state.current]};
    const blob=new Blob([JSON.stringify(content,null,2)+'\n'],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=element('a');a.href=url;
    a.download=`measurement-${String(state.current.id || 'case').replace(/[^a-zA-Z0-9_-]/g,'-')}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  function caseIndexFromHash() {
    let id = '';
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return 0; }
    const index = state.cases.findIndex((item) => item && String(item.id) === id);
    return index < 0 ? 0 : index;
  }
  window.addEventListener('hashchange', () => {
    if (!state.cases.length) return;
    let id = '';
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return; }
    const index = state.cases.findIndex((item) => item && String(item.id) === id);
    if (index >= 0 && state.cases[index] !== state.current) selectCase(index);
  });
  fetch(new URL('measurements.json', assetRoot))
    .then((response) => { if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json(); })
    .then((data) => {
      if(data?.version !== 1 || !Array.isArray(data.cases) || !data.cases.length)throw new Error('지원되는 예제 데이터가 없습니다.');
      state.data=data;state.cases=data.cases;
      status.hidden=true;workspace.hidden=false;selectCase(caseIndexFromHash());
    })
    .catch(() => showError('계측 예제 데이터를 불러오지 못했습니다. 문서를 제공하는 서버와 예제 데이터 경로를 확인하세요.'));
})();
