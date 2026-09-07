import {readdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../dist/',import.meta.url),files=[];
async function walk(prefix='') {for(const e of await readdir(new URL(prefix,root),{withFileTypes:true})){const path=prefix+e.name;if(e.isDirectory())await walk(path+'/');else if(path!=='sw.js')files.push(path);}}
await walk();files.sort();const hash=createHash('sha256');for(const f of files)hash.update(await readFile(new URL(f,root)));const version=hash.digest('hex').slice(0,16);
await writeFile(new URL('sw.js',root),`const PREFIX='otw-shell-'+new URL(self.registration.scope).pathname+'-';
const CACHE=PREFIX+'${version}';
const FILES=${JSON.stringify(files)};
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES.map(p=>new URL(p,self.registration.scope).href)))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith(PREFIX)&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const r=event.request,u=new URL(r.url),scope=new URL(self.registration.scope);
 if(r.method!=='GET'||u.origin!==scope.origin||!u.pathname.startsWith(scope.pathname))return;
 const relative=u.pathname.slice(scope.pathname.length);
 if(r.mode==='navigate')event.respondWith(fetch(r).catch(()=>caches.open(CACHE).then(cache=>cache.match(new URL('index.html',scope).href))));
 else if(FILES.includes(relative))event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(r,{ignoreSearch:true,ignoreVary:true}))||fetch(r)));
});
`);
console.log('Offline shell built: '+files.length+' files, '+version);
