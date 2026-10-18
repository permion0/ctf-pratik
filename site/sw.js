/* İnternetsiz açılış: uygulama dosyaları ve son indirilen program telefonda saklanır.
   Program verisi (data/) önce internetten istenir, olmazsa son kaydedilen gösterilir. */
const SURUM = 'pp-2026-10-19';
const KABUK = ['./', 'index.html', 'app.js', 'style.css', 'manifest.webmanifest', 'icon.svg', 'icon-180.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SURUM).then(c => c.addAll(KABUK)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== SURUM).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const url = new URL(r.url);
  const yazi = url.hostname.endsWith('gstatic.com') || url.hostname.endsWith('googleapis.com');
  if (url.origin !== location.origin && !yazi) return;
  if (url.origin === location.origin && (url.pathname.includes('/data/') || r.mode === 'navigate' || /\.(js|css)$/.test(url.pathname))) {
    // önce internet (güncel veri ve kod), olmazsa son kayıt
    e.respondWith(fetch(r).then(y => { if (y.ok) { const k = y.clone(); caches.open(SURUM).then(c => c.put(r, k)); } return y; })
      .catch(() => caches.match(r, { ignoreSearch: true }).then(m => m || caches.match('index.html'))));
    return;
  }
  // yazı tipleri ve simgeler: önce kayıt
  e.respondWith(caches.match(r).then(m => m || fetch(r).then(y => { const k = y.clone(); caches.open(SURUM).then(c => c.put(r, k)); return y; })));
});
