self.addEventListener('install', (e) => {
    console.log('[Service Worker] Installato');
});

self.addEventListener('fetch', (e) => {
    // Lasciamo vuoto per ora: serve solo a far capire al telefono che l'app è installabile
});