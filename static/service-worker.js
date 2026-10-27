// Service Worker للـ PWA
const CACHE_NAME = 'helpdesk-v1';
const urlsToCache = [
    '/',
    '/static/css/main.css',
    '/static/manifest.json',
    'https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// تثبيت Service Worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Caching app shell');
                return cache.addAll(urlsToCache);
            })
            .catch(err => {
                console.log('[SW] Cache failed:', err);
            })
    );
    self.skipWaiting();
});

// تفعيل Service Worker
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// استراتيجية Cache First للملفات الثابتة
self.addEventListener('fetch', event => {
    // تجاهل الطلبات الخارجية
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // إرجاع من الكاش إذا وُجد
                if (response) {
                    return response;
                }

                // جلب من الشبكة
                return fetch(event.request).then(response => {
                    // التحقق من الاستجابة الصحيحة
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // حفظ نسخة في الكاش للملفات الثابتة فقط
                    if (event.request.url.includes('/static/')) {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    }

                    return response;
                });
            })
            .catch(() => {
                // صفحة offline بسيطة
                if (event.request.destination === 'document') {
                    return new Response(`
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>غير متصل بالإنترنت</title>
              <style>
                body {
                  font-family: 'Cairo', sans-serif;
                  background: #0f172a;
                  color: white;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  min-height: 100vh;
                  text-align: center;
                  padding: 20px;
                }
                .offline-content {
                  max-width: 400px;
                }
                h1 { color: #6366f1; margin-bottom: 1rem; }
                p { color: #94a3b8; line-height: 1.6; }
                button {
                  background: #6366f1;
                  color: white;
                  border: none;
                  padding: 0.75rem 1.5rem;
                  border-radius: 8px;
                  margin-top: 1rem;
                  cursor: pointer;
                  font-family: inherit;
                }
              </style>
            </head>
            <body>
              <div class="offline-content">
                <h1>📡 غير متصل بالإنترنت</h1>
                <p>يبدو أنك غير متصل بالإنترنت حالياً. يرجى التحقق من اتصالك والمحاولة مرة أخرى.</p>
                <button onclick="location.reload()">🔄 إعادة المحاولة</button>
              </div>
            </body>
            </html>
          `, {
                        headers: { 'Content-Type': 'text/html' }
                    });
                }
            })
    );
});

// إشعارات Push (اختياري)
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Help Desk Pro';
    const options = {
        body: data.body || 'لديك إشعار جديد',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        tag: 'helpdesk-notification',
        requireInteraction: true,
        data: {
            url: data.url || '/'
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// فتح الرابط عند الضغط على الإشعار
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});
