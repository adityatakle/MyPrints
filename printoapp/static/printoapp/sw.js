// Minimal Service Worker solely to enable browser installation prompt
self.addEventListener('fetch', (event) => {
  // Pass everything straight to the network
  return;
});