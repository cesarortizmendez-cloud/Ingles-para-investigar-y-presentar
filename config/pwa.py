"""Aplicación instalable (PWA): manifiesto, service worker y página sin conexión.

El service worker se sirve desde la raíz (/sw.js) para que su alcance cubra todo el sitio.
"""
import json

from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

APP_VERSION = "v6"


@cache_control(max_age=3600, public=True)
def manifest(request):
    data = {
        "name": "Inglés para investigar y presentar",
        "short_name": "Inglés Investigación",
        "description": "Lee publicaciones científicas y presenta tu investigación en inglés.",
        "lang": "es-CL",
        "id": "/",
        "start_url": "/?origen=app",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "orientation": "any",
        "dir": "ltr",
        "categories": ["education", "productivity"],
        "background_color": "#F4F7FC",
        "theme_color": "#0A3161",
        "icons": [
            {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("img/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        # Accesos directos (clic derecho en el ícono en Windows/Mac; mantener presionado en Android)
        "shortcuts": [
            {"name": "Plan de 40 días", "short_name": "Plan 40", "url": "/plan/?origen=app",
             "icons": [{"src": static("img/icon-192.png"), "sizes": "192x192"}]},
            {"name": "Plan base de 20 días", "short_name": "Base 20", "url": "/plan/base20/?origen=app",
             "icons": [{"src": static("img/icon-192.png"), "sizes": "192x192"}]},
            {"name": "Repaso de hoy", "short_name": "Repaso", "url": "/repaso/?origen=app",
             "icons": [{"src": static("img/icon-192.png"), "sizes": "192x192"}]},
        ],
        # Capturas: Android y Windows muestran una ventana de instalación más completa
        "screenshots": [
            {"src": static("img/screens/inicio-ancho.jpg"), "sizes": "1280x800", "type": "image/jpeg",
             "form_factor": "wide", "label": "Inicio con los planes y el avance"},
            {"src": static("img/screens/dia-movil.jpg"), "sizes": "412x915", "type": "image/jpeg",
             "form_factor": "narrow", "label": "Un día del plan, paso a paso"},
        ],
    }
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type="application/manifest+json; charset=utf-8")


SW_TEMPLATE = """
const CACHE = "ingles-__VERSION__";
const PRECACHE = __PRECACHE__;
const OFFLINE = "/sin-conexion/";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;                       // nunca interceptar envíos
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/voz/") || url.pathname.startsWith("/admin/")) return;  // audio y admin: siempre red
  if (url.pathname.startsWith("/static/")) {              // estáticos: caché primero
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    })));
    return;
  }
  if (req.mode === "navigate") {                          // páginas: red primero, sin conexión → aviso
    e.respondWith(fetch(req).catch(() => caches.match(OFFLINE)));
  }
});
"""


def service_worker(request):
    precache = [
        "/sin-conexion/",
        static("css/app.css"), static("js/app.js"),
        static("js/pwa.js"), static("js/voice.js"),
        static("img/flag.svg"), static("img/icon-192.png"),
    ]
    body = SW_TEMPLATE.replace("__VERSION__", APP_VERSION).replace("__PRECACHE__", json.dumps(precache))
    resp = HttpResponse(body, content_type="application/javascript; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    resp["Service-Worker-Allowed"] = "/"
    return resp


def offline(request):
    return render(request, "offline.html")
