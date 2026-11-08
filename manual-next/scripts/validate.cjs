#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const failures=[],warnings=[],pages=[];
function walk(d){for(const f of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,f.name);if(f.isDirectory())walk(p);else if(f.name.endsWith(".html"))pages.push(p);}}
walk(root);
const manifest=fs.readFileSync(path.join(root,"assets","manual.js"),"utf8");
const match=manifest.match(/const data=(\[[\s\S]*?\]);\s*\nconst root=/);
if(!match){failures.push("Cannot parse navigation JSON from manual.js");} 
let entries=[];try{if(match)entries=JSON.parse(match[1]);}catch(e){failures.push("Navigation JSON invalid: "+e.message)}
const byRel=new Map(pages.map(p=>[path.relative(root,p).replaceAll(path.sep,"/"),p]));
const linked=new Set(),titles=new Map();
for(const page of pages){
  const rel=path.relative(root,page).replaceAll(path.sep,"/"),html=fs.readFileSync(page,"utf8");
  const h1=(html.match(/<h1\b/gi)||[]).length;
  if(h1!==1)failures.push(rel+": expected exactly 1 h1, got "+h1);
  const ti=html.match(/<title>([^<]*)<\/title>/i)?.[1];if(!ti)failures.push(rel+": missing title");
  else{if(titles.has(ti))failures.push(rel+": duplicate title with "+titles.get(ti));titles.set(ti,rel)}
  if(!/<meta name="description" content="/.test(html))warnings.push(rel+": missing description");
  const rootAttr=html.match(/<meta name="manual-root" content="([^"]+)"/)?.[1];
  if(!rootAttr)failures.push(rel+": missing manual-root");
  const pathAttr=html.match(/<meta name="manual-path" content="([^"]+)"/)?.[1];
  if(pathAttr!==rel)failures.push(rel+": incorrect manual-path "+pathAttr);
  if(html.includes("@ROOT@"))failures.push(rel+": unresolved @ROOT@");
  const ids=new Set();
  for(const m of html.matchAll(/\bid="([^"]+)"/g)){
    if(ids.has(m[1]))failures.push(rel+": duplicate id "+m[1]);ids.add(m[1]);
  }
  for(const m of html.matchAll(/\b(?:href|src)="([^"]+)"/g)){
    let uri=m[1];
    if(/^(https?:|mailto:|data:|tel:)/.test(uri))continue;
    if(uri.startsWith("#")){if(!ids.has(uri.slice(1)))failures.push(rel+": absent anchor "+uri);continue;}
    const [target,fragment]=uri.split("#");
    if(!target)continue;
    const resolved=path.resolve(path.dirname(page),target);
    if(!resolved.startsWith(root+path.sep)&&resolved!==root){failures.push(rel+": link leaves manual: "+uri);continue;}
    if(!fs.existsSync(resolved)){failures.push(rel+": broken link "+uri);continue;}
    if(fragment){let other=fs.readFileSync(resolved,"utf8");if(!other.includes('id="'+fragment+'"'))failures.push(rel+": broken target anchor "+uri)}
    if(resolved.endsWith(".html"))linked.add(path.relative(root,resolved).replaceAll(path.sep,"/"));
  }
  for(const m of html.matchAll(/<img\b[^>]*>/gi))if(!/\balt="/.test(m[0]))failures.push(rel+": image missing alt");
  for(const m of html.matchAll(/<svg\b[^>]*>/gi))if(!/\baria-label="/.test(m[0])&&!/\b<svg[^>]*aria-labelledby="/.test(m[0]))warnings.push(rel+": SVG missing accessible label");
}
const navSet=new Set();
for(const row of entries){
  if(!Array.isArray(row)||row.length<3){failures.push("Bad nav entry "+JSON.stringify(row));continue;}
  const target=row[1];
  if(navSet.has(target))failures.push("Duplicate nav target "+target);
  navSet.add(target);
  if(!byRel.has(target))failures.push("Nav points to absent HTML "+target);
}
for(const rel of byRel.keys())if(!navSet.has(rel))failures.push("HTML page not in navigation: "+rel);
console.log("HTML manual QA: "+pages.length+" pages, "+entries.length+" nav entries, "+linked.size+" linked target pages");
console.log("Warnings: "+warnings.length);warnings.slice(0,40).forEach(x=>console.warn("WARN "+x));
if(failures.length){failures.forEach(x=>console.error("FAIL "+x));process.exit(1)}
console.log("PASS — HTML structure, links, anchors, navigation, unique titles");
