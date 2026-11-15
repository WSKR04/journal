/* Journal de trading : fonctionnement hors connexion.
   Page et données : réseau d'abord (toujours à jour), copie locale si pas de connexion.
   Librairie de graphiques : copie locale d'abord. Les appels Supabase / IA ne sont jamais mis en cache. */
const C='journal-v1';
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(['./','./manifest.webmanifest','./icon-192.png']).catch(()=>{})))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const r=e.request;if(r.method!=='GET')return;
  const u=new URL(r.url);
  if(u.hostname==='cdnjs.cloudflare.com'){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(x=>{if(x.ok){const y=x.clone();caches.open(C).then(c=>c.put(r,y))}return x})));return}
  if(u.origin!==location.origin)return;
  e.respondWith(fetch(r).then(x=>{if(x.ok){const y=x.clone();const k=new Request(u.origin+u.pathname);caches.open(C).then(c=>c.put(k,y))}return x}).catch(()=>caches.match(new Request(u.origin+u.pathname)).then(m=>m||caches.match('./'))));
});
