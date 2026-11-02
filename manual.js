"use strict";
function normalizeManualSearch(value) {
  return value.toLocaleLowerCase().replace(/[\s_().-]+/g, "");
}

function searchManualIndex(index, query) {
  const normalized = normalizeManualSearch(query.trim());
  if (!normalized) return [];
  const tokens = query.trim().split(/\s+/).map(normalizeManualSearch).filter(Boolean);
  const matches = index.filter(item => tokens.every(token => item.text.includes(token)));
  const rank = item => item.key === normalized ? 0 : item.key.startsWith(normalized) ? 1 : item.key.includes(normalized) ? 2 : 3;
  matches.sort((a,b) => rank(a) - rank(b) || a.label.localeCompare(b.label));
  return matches;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {normalizeManualSearch, searchManualIndex};
}

(() => {
  if (typeof document === "undefined") return;
  const search = document.getElementById("manual-search");
  const results = document.getElementById("search-results");
  const status = document.getElementById("search-status");
  const sidebar = document.getElementById("sidebar");
  const menu = document.getElementById("menu-button");
  const functionHelp = document.getElementById("function-help");
  let functionTrigger = null;
  const index = JSON.parse(document.getElementById("search-data").textContent);
  const functionCards = JSON.parse(document.getElementById("function-data")?.textContent || "{}");
  const legacyPages = JSON.parse(document.getElementById("page-map")?.textContent || "{}");
  const normalize = normalizeManualSearch;
  const searchable = index.map(item => ({...item, key: normalize(item.label), text: normalize(item.label + " " + item.summary + " " + item.terms)}));
  let searchTimer;
  let copyTimer;
  let printState = [];

  function closeMenu() {
    sidebar.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
  }

  function revealHash() {
    const ident = decodeURIComponent(location.hash.slice(1));
    if (!ident) return;
    const target = document.getElementById(ident);
    if (!target) {
      if (legacyPages[ident]) location.replace(legacyPages[ident] + "#" + encodeURIComponent(ident));
      return;
    }
    let parent = target;
    while (parent) {
      if (parent.tagName === "DETAILS") parent.open = true;
      parent = parent.parentElement;
    }
    requestAnimationFrame(() => target.scrollIntoView({block:"start"}));
  }

  function renderSearch() {
    const query = normalize(search.value.trim());
    results.replaceChildren();
    if (!query) {
      results.hidden = true;
      status.textContent = "함수명 · 파라미터 · 검사 용어로 검색";
      return;
    }
    const matches = searchManualIndex(searchable, search.value);
    status.textContent = matches.length + "개 결과 · 상위 40개 표시";
    for (const item of matches.slice(0,40)) {
      const link = document.createElement("a");
      link.href = item.href;
      link.className = "search-result";
      const kind = document.createElement("small");
      kind.textContent = item.kind;
      const label = document.createElement("strong");
      label.textContent = item.label;
      const summary = document.createElement("p");
      summary.textContent = item.summary;
      link.append(kind, label, summary);
      link.addEventListener("click", event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        results.hidden = true;
        closeMenu();
        if (location.pathname === link.pathname && location.hash === link.hash) revealHash();
        else location.assign(link.href);
      });
      results.append(link);
    }
    if (!matches.length) {
      const empty = document.createElement("p");
      empty.className = "search-empty";
      empty.textContent = "일치하는 항목이 없습니다. 함수의 일부나 영어 이름으로 검색해 보세요.";
      results.append(empty);
    }
    results.hidden = false;
  }

  search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(renderSearch, 100);
  });
  search.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") {
      const first = results.querySelector("a");
      if (first) { event.preventDefault(); first.focus(); }
    }
    if (event.key === "Enter") {
      const first = results.querySelector("a");
      if (first) { event.preventDefault(); first.click(); }
    }
  });
  results.addEventListener("keydown", event => {
    const links = [...results.querySelectorAll("a")];
    const current = links.indexOf(document.activeElement);
    if (event.key === "ArrowDown" && current < links.length - 1) { event.preventDefault(); links[current + 1].focus(); }
    if (event.key === "ArrowUp") { event.preventDefault(); (links[current - 1] || search).focus(); }
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (innerWidth <= 760) { sidebar.classList.add("open"); menu.setAttribute("aria-expanded", "true"); }
      search.focus();
    }
    if (event.key === "Escape") { results.hidden = true; closeMenu(); search.blur(); }
  });
  document.addEventListener("click", event => {
    if (!event.target.closest(".search-wrap")) results.hidden = true;
    const link = event.target.closest("a[data-function]");
    if (!link || !functionHelp || typeof functionHelp.showModal !== "function") return;
    let reference = document.getElementById(link.dataset.function);
    if (!reference && functionCards[link.dataset.function]) {
      const template = document.createElement("template");
      template.innerHTML = functionCards[link.dataset.function];
      reference = template.content.firstElementChild;
    }
    const body = reference?.querySelector(".reference-body");
    if (!body) return;
    event.preventDefault();
    functionTrigger = link;
    const heading = reference.querySelector("summary code");
    document.getElementById("function-help-title").textContent = heading?.textContent || link.textContent;
    const content = document.getElementById("function-help-content");
    content.replaceChildren(...[...body.childNodes].map(node => node.cloneNode(true)));
    content.querySelectorAll("[id]").forEach(node => node.removeAttribute("id"));
    document.getElementById("function-help-reference").href = link.href;
    if (!functionHelp.open) functionHelp.showModal();
    functionHelp.scrollTop = 0;
    document.getElementById("function-help-close").focus({preventScroll:true});
  });
  if (functionHelp) {
    document.getElementById("function-help-close").addEventListener("click", () => functionHelp.close());
    functionHelp.addEventListener("close", () => {
      if (functionTrigger?.isConnected) functionTrigger.focus({preventScroll:true});
      functionTrigger = null;
    });
    functionHelp.addEventListener("click", event => {
      if (event.target === functionHelp) {
        const rect = functionHelp.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) functionHelp.close();
      }
      if (event.target.closest("a[href]") && !event.target.closest("a[data-function]")) functionHelp.close();
    });
  }
  menu.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    menu.setAttribute("aria-expanded", String(open));
  });
  sidebar.querySelectorAll("nav a").forEach(link => link.addEventListener("click", closeMenu));
  window.addEventListener("hashchange", revealHash);
  if (location.hash) setTimeout(revealHash, 30);

  document.querySelectorAll(".expand-all,.collapse-all").forEach(button => button.addEventListener("click", () => {
    const section = document.getElementById(button.dataset.target);
    section.querySelectorAll("details.api-reference").forEach(detail => detail.open = button.classList.contains("expand-all"));
  }));
  document.addEventListener("click", async event => {
    const button = event.target.closest(".copy-code");
    if (!button) return;
    const text = button.closest(".code-block").querySelector("code").textContent;
    let copied = false;
    try { await navigator.clipboard.writeText(text); copied = true; } catch (_) {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.append(textarea);
      textarea.select();
      try { copied = document.execCommand("copy"); } catch (_) { /* Selection fallback remains available. */ }
      textarea.remove();
      button.focus();
    }
    const toast = document.getElementById("copy-status");
    toast.textContent = copied ? "코드를 복사했습니다." : "복사가 제한되었습니다. 코드 블록을 선택해 복사하세요.";
    toast.classList.add("visible");
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
  });

  function preparePrint() {
    if (printState.length) return;
    printState = [...document.querySelectorAll("details.api-reference, details.context-api")].map(detail => [detail, detail.open]);
    printState.forEach(([detail]) => detail.open = true);
  }
  function restorePrint() {
    printState.forEach(([detail, open]) => detail.open = open);
    printState = [];
  }
  document.getElementById("print-button").addEventListener("click", () => { preparePrint(); window.print(); });
  window.addEventListener("beforeprint", preparePrint);
  window.addEventListener("afterprint", restorePrint);

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!visible.length) return;
      document.querySelectorAll("nav a").forEach(link => link.classList.toggle("active", link.dataset.nav === visible[0].target.id));
    }, {rootMargin:"-90px 0px -55% 0px",threshold:0});
    document.querySelectorAll("section.chapter").forEach(section => observer.observe(section));
  }
})();
