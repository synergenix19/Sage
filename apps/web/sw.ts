// POST-PILOT: Replace with Serwist for full precaching. Install: npm i serwist @serwist/next
/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope

// Minimal SW — serwist not installed. Caches app shell and serves offline fallback.
const CACHE_NAME = 'cdai-v1'
const OFFLINE_URL = '/offline.html'

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_URL))
  )
})

self.addEventListener('fetch', (event: FetchEvent) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL) as Promise<Response>)
    )
  }
})

self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if ((event.data as { type?: string } | null)?.type === 'SKIP_WAITING') {
    void (self as unknown as ServiceWorkerGlobalScope).skipWaiting()
  }
})
