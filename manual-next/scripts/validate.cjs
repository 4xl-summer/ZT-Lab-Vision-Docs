#!/usr/bin/env node
"use strict";
// Usage: node scripts/validate.cjs [manual-root]. Validates generated files locally.
const fs = require("node:fs"), path = require("node:path");
const root = path.resolve(process.argv[2] || path.join(__dirname, ".."));
const errors = [], warnings = [], pages = new Map(), assetCache = new Map();
function walk(dir) { for (const ent of fs.readdirSync(dir, {withFileTypes:true})) { const f=path.join(dir, ent.name); if(ent.isDirectory()) walk(f); else if(ent.name.endsWith(".html")) { const rel=path.relative(root,f).split(path.sep).join("/"); const html=fs.readFileSync(f,"utf8"); const ids=new Set(); for(const m of html.matchAll(/\bid="([^"]*)"/g)) { if(ids.has(m[1])) errors.push(`${rel}: duplicate id ${m[1]}`); ids.add(m[1]); } pages.set(rel,{html,ids}); } } }
function localTarget(from, href) { if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return null; const [beforeHash,fragRaw] = href.split("#",2); const p=beforeHash.split("?",1)[0]; let fragment, decoded; try {fragment=decodeURIComponent(fragRaw||""); decoded=decodeURIComponent(p);} catch {errors.push(`${from}: invalid URL encoding ${href}`);return null;} if(decoded.startsWith("/")){errors.push(`${from}: absolute site path ${href}`);return null;} const dest=decoded ? path.posix.normalize(path.posix.join(path.posix.dirname(from),decoded)) : from; if(dest===".." || dest.startsWith("../")){errors.push(`${from}: link escapes manual ${href}`);return null;} return {dest,fragment}; }
function check(from,href){const t=localTarget(from,href);if(!t)return;const page=pages.get(t.dest);if(page){if(t.fragment&&!page.ids.has(t.fragment))errors.push(`${from}: missing anchor ${href}`);return;}if(!assetCache.has(t.dest))assetCache.set(t.dest,fs.existsSync(path.join(root,...t.dest.split("/"))));if(!assetCache.get(t.dest)) errors.push(`${from}: missing target ${href}`);}
function navJSON() { const f=path.join(root,"assets","manual-data.js"); let text; try{text=fs.readFileSync(f,"utf8");}catch(e){errors.push(`manual-data.js: ${e.message}`);return null;} const m=text.match(/window\.MANUAL_DATA\s*=\s*([\s\S]*?)\s*;?\s*$/); if(!m){errors.push("manual-data.js: missing assignment");return null;} try{return JSON.parse(m[1].replace(/;\s*$/, ""));}catch(e){errors.push(`manual-data.js: invalid JSON ${e.message}`);return null;} }
try{walk(root);}catch(e){console.error(`FAIL ${e.message}`);process.exit(2);}
const nav=navJSON(), targets=[];
function strings(x){ if(typeof x==="string"){if(/\.html(?:[#?].*)?$/.test(x))targets.push(x.split(/[?#]/,1)[0].replace(/^\.\//,""));} else if(Array.isArray(x))x.forEach(strings);else if(x&&typeof x==="object")Object.values(x).forEach(strings); }
if(nav)strings((nav.pages || (Array.isArray(nav)?nav:[])).map(item=>item&&typeof item==="object"&&!Array.isArray(item)?item.path:item));
const navset=new Set();for(const p of targets){if(navset.has(p))errors.push(`duplicate navigation target ${p}`);navset.add(p);if(!pages.has(p))errors.push(`navigation target absent ${p}`);}
// A registered legacy URL is the sole exception to the navigation requirement.
// Move targets are rooted at the manual root, while redirect meta and links are
// relative to the legacy page. Validate destination pages rather than assets.
let moves={};
try {
 const data=JSON.parse(fs.readFileSync(path.join(root,"content","page-moves.json"),"utf8"));
 if(!data || data.version!==1 || !data.moves || typeof data.moves!=="object" || Array.isArray(data.moves)) throw Error("expected version 1 and moves object");
 moves=data.moves;
} catch(e) { errors.push(`content/page-moves.json: ${e.message}`); }
function moveTarget(old,href,description) {
 if(typeof href!=="string" || !href || /^(?:[a-z][a-z\d+.-]*:|\/\/|\/)/i.test(href) || href.includes("?")) { errors.push(`${old}: invalid ${description} ${String(href)}`); return null; }
 const t=localTarget("index.html",href);
 if(!t || !t.dest.endsWith(".html") || !pages.has(t.dest)) { errors.push(`${old}: ${description} is not an existing HTML page: ${href}`); return null; }
 if(Object.hasOwn(moves,t.dest) || /<meta\s+name="manual-redirect"\s+content="[^"]*"/i.test(pages.get(t.dest).html)) errors.push(`${old}: ${description} redirects again: ${href}`);
 if(t.fragment && !pages.get(t.dest).ids.has(t.fragment)) errors.push(`${old}: ${description} has missing anchor: ${href}`);
 return t;
}
function sameTarget(old,href,target,label) {
 if(!href || /^(?:[a-z][a-z\d+.-]*:|\/\/|\/)/i.test(href)) { errors.push(`${old}: ${label} must be a relative URL`); return; }
 const t=localTarget(old,href);
 if(!t || !target || t.dest!==target.dest || t.fragment!==target.fragment || href.includes("?")) errors.push(`${old}: ${label} does not match registered target: ${href}`);
}
for(const [old,entry] of Object.entries(moves)) {
 let decodedOld;
 try { decodedOld=decodeURIComponent(old); } catch { decodedOld=''; }
 const safePath = value => value && value.endsWith('.html') && !/^(?:[a-z][a-z\d+.-]*:|\/)/i.test(value) && !/[\\?#\x00-\x1f]/.test(value) && !value.split('/').some(part=>!part || part==='.' || part==='..') && path.posix.normalize(value)===value;
 if(!safePath(old) || !safePath(decodedOld)) { errors.push(`invalid legacy path ${old}`); continue; }
 if(!entry || typeof entry!=="object" || Array.isArray(entry) || (entry.fragments!==undefined && (!entry.fragments || typeof entry.fragments!=="object" || Array.isArray(entry.fragments)))) { errors.push(`${old}: invalid move record`); continue; }
 if(!pages.has(old)) { errors.push(`${old}: registered redirect missing`); continue; }
 if(navset.has(old)) errors.push(`${old}: redirect is in navigation`);
 const target=moveTarget(old,entry.target,"target");
 for(const [hash,dest] of Object.entries(entry.fragments || {})) {
   if(!hash || hash.includes("#")) errors.push(`${old}: invalid old fragment ${hash}`);
   moveTarget(old,dest,`fragment ${hash}`);
 }
 const html=pages.get(old).html;
 const redirects=[...html.matchAll(/<meta\s+name="manual-redirect"\s+content="([^"]*)"/gi)];
 if(redirects.length!==1) errors.push(`${old}: expected exactly one manual-redirect meta`);
 else sameTarget(old,redirects[0][1],target,"manual-redirect");
 const canonical=[...html.matchAll(/<link\s+rel="canonical"\s+href="([^"]*)"/gi)];
 if(canonical.length!==1) errors.push(`${old}: expected exactly one canonical link`);
 else sameTarget(old,canonical[0][1],target,"canonical");
 const links=[...html.matchAll(/<a\b[^>]*\bhref="([^"]*)"/gi)];
 if(!links.some(m=>{const t=localTarget(old,m[1]);return t && target && t.dest===target.dest && t.fragment===target.fragment;})) errors.push(`${old}: missing link to registered target`);
}
// Only active page paths, navigation paths and search data are checked; prose
// may still discuss historical URLs without becoming a search destination.
function noLabsPaths(value,label) {
 if(typeof value==="string") { if(/^(?:\.\/)?labs\//i.test(value)) errors.push(`${label}: obsolete labs path ${value}`); }
 else if(Array.isArray(value)) value.forEach(v=>noLabsPaths(v,label));
 else if(value && typeof value==="object") Object.values(value).forEach(v=>noLabsPaths(v,label));
}
for(const name of ["pages.json","navigation.json"]) try {
 const data=JSON.parse(fs.readFileSync(path.join(root,"content",name),"utf8"));
 if(!Array.isArray(data)) throw Error("expected array");
 if(name==="pages.json") data.forEach(item=>{noLabsPaths(item?.path,`content/${name}`);if(['관련 API','관련 공개 API'].includes(item?.nav_label?.trim())) errors.push(`content/${name}: obsolete 관련 API navigation label ${item.path}`);});
 else data.forEach(row=>noLabsPaths(Array.isArray(row)?row[1]:row?.path,`content/${name}`));
} catch(e) { errors.push(`content/${name}: ${e.message}`); }
if(nav) { noLabsPaths(nav,"assets/manual-data.js"); for(const p of nav.pages || []) if(['관련 API','관련 공개 API'].includes(p?.nav_label?.trim())) errors.push(`assets/manual-data.js: obsolete 관련 API navigation label ${p.path}`); }
const titles=new Map();for(const [rel,{html,ids}] of pages){const registered=Object.hasOwn(moves,rel);if(!navset.has(rel)&&!registered)errors.push(`${rel}: not in navigation`);if(!registered && /<meta\s+name="manual-redirect"\s+content="[^"]*"/i.test(html))errors.push(`${rel}: unregistered redirect`);if(!registered && /<section\b[^>]*\bclass="[^"]*\brelated-api\b[^"]*"/i.test(html))errors.push(`${rel}: obsolete related-api section`);const h1=(html.match(/<h1\b/gi)||[]).length;if(h1!==1)errors.push(`${rel}: expected one h1, got ${h1}`);const title=html.match(/<title>([^<]+)<\/title>/i)?.[1];if(!title)errors.push(`${rel}: missing title`);else if(titles.has(title))errors.push(`${rel}: duplicate title with ${titles.get(title)}`);else titles.set(title,rel);const m=html.match(/<meta\s+name="manual-path"\s+content="([^"]+)"/i);if(m?.[1]!==rel)errors.push(`${rel}: incorrect manual-path`);if(!/<meta\s+name="manual-root"\s+content="[^"]+"/i.test(html))errors.push(`${rel}: missing manual-root`);if(html.includes("@ROOT@"))errors.push(`${rel}: unresolved @ROOT@`);for(const x of html.matchAll(/\b(?:href|src)="([^"]+)"/g))check(rel,x[1]);for(const x of html.matchAll(/<img\b[^>]*>/gi))if(!/\balt=/.test(x[0]))errors.push(`${rel}: img missing alt`);for(const x of html.matchAll(/<svg\b[^>]*>/gi))if(!/\baria-(?:label|labelledby)=/.test(x[0]))warnings.push(`${rel}: SVG missing accessible label`);}
let apiEntries=0,apiLinks=0;
if(nav && typeof nav.apiIndex==="string") { const index=path.posix.normalize(nav.apiIndex);if(index===".."||index.startsWith("../")||index.startsWith("/"))errors.push("apiIndex escapes manual");else try{const data=JSON.parse(fs.readFileSync(path.join(root,...index.split("/")),"utf8"));if(!Array.isArray(data))throw Error("expected array");noLabsPaths(data,index);apiEntries=data.length;for(const item of data){for(const entry of [item,...(Array.isArray(item.members)?item.members:[])]){if(!entry || typeof entry.href!=="string"){errors.push(`${index}: missing href`);continue;}check("index.html",entry.href);apiLinks++;}}}catch(e){errors.push(`${index}: ${e.message}`);}}
console.log(`HTML manual QA: ${pages.size} pages, ${targets.length} nav entries, ${apiEntries} API entries, ${apiLinks} API links`);console.log(`Warnings: ${warnings.length}; Errors: ${errors.length}`);warnings.slice(0,100).forEach(x=>console.warn(`WARN ${x}`));errors.forEach(x=>console.error(`FAIL ${x}`));if(errors.length)process.exit(1);console.log("PASS — HTML structure, links, anchors, navigation, API search and unique titles");
