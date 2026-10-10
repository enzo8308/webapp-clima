// Smart Clima - service worker v2
// Serve a rendere l'app installabile. Non mette nulla in cache:
// stato, comandi e login restano sempre "dal vivo".
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(function () {
      return new Response('Sei offline: riprova quando torna la connessione.',
        { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    }));
  }
});
