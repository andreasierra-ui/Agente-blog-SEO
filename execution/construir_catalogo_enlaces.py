#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
construir_catalogo_enlaces.py — Construye el catálogo completo de URLs enlazables
del sitio de Mundo Joven: blogs + páginas de servicio (tours, seguros, cruceros, etc.).

Salida: .tmp/catalogo_enlaces.json con estructura:
[
  {
    "url": "https://mundojoven.com/tours/tour-japon",
    "title": "Tour Japón",
    "slug": "tour-japon",
    "type": "tours",
    "cluster": "Tours",
    "keywords": ["japón", "tour japón", "viaje japón"]
  },
  ...
]

Uso:
  py execution/construir_catalogo_enlaces.py              # Construir todo
  py execution/construir_catalogo_enlaces.py --stats       # Solo mostrar estadísticas del catálogo existente

Requiere en .env: WP_URL, WP_USER, WP_APP_PASSWORD.
"""
import sys, os, json, time, base64, ssl, re, html
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, ".tmp", "catalogo_enlaces.json")
CTX = ssl.create_default_context()

CPTS = [
    {
        "wp_type": "wp_single_tours",
        "url_prefix": "/tours/",
        "cluster": "Tours",
        "type_key": "tours",
    },
    {
        "wp_type": "wp_single_seguros",
        "url_prefix": "/seguros/",
        "cluster": "Seguros",
        "type_key": "seguros",
    },
    {
        "wp_type": "wp_single_cruise",
        "url_prefix": "/cruceros/",
        "cluster": "Cruceros",
        "type_key": "cruceros",
    },
    {
        "wp_type": "wp_single_vuelo",
        "url_prefix": "/vuelos/",
        "cluster": "Vuelos",
        "type_key": "vuelos",
    },
    {
        "wp_type": "wp_single_hotel",
        "url_prefix": "/hoteles/",
        "cluster": "Hoteles",
        "type_key": "hoteles",
    },
    {
        "wp_type": "wp_single_idiomas",
        "url_prefix": "/estudios/idiomas/",
        "cluster": "Idiomas",
        "type_key": "idiomas",
    },
    {
        "wp_type": "wp_single_edsuperior",
        "url_prefix": "/estudios/educacion-superior/",
        "cluster": "Estudios",
        "type_key": "educacion_superior",
    },
    {
        "wp_type": "wp_single_hschool",
        "url_prefix": "/estudios/high-school/",
        "cluster": "Estudios",
        "type_key": "high_school",
    },
    {
        "wp_type": "wp_single_camp",
        "url_prefix": "/estudios/campamentos/",
        "cluster": "Estudios",
        "type_key": "campamentos",
    },
    {
        "wp_type": "wp_single_aupair",
        "url_prefix": "/estudios/aupair/",
        "cluster": "Estudios",
        "type_key": "au_pair",
    },
    {
        "wp_type": "wp_single_workstudy",
        "url_prefix": "/estudios/estudia-y-trabaja/",
        "cluster": "Estudios",
        "type_key": "work_study",
    },
]

BLOG_CPT = {
    "wp_type": "pt_blog_article",
    "url_prefix": "/blog/",
    "cluster": "Blog",
    "type_key": "blog",
}

SITE_BASE = "https://mundojoven.com"


def _env():
    e = {}
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def _auth(e):
    cred = e["WP_USER"] + ":" + e["WP_APP_PASSWORD"]
    return "Basic " + base64.b64encode(cred.encode()).decode()


def _fetch(e, path, retries=8):
    url = e["WP_URL"].rstrip("/") + path
    for i in range(retries):
        try:
            req = request.Request(url, headers={
                "Authorization": _auth(e),
                "User-Agent": "MundoJovenAgent/1.0",
            })
            with request.urlopen(req, timeout=90, context=CTX) as r:
                total = r.getheader("X-WP-Total", "?")
                return json.loads(r.read().decode()), total
        except Exception as ex:
            print("  ...retry %d: %s" % (i + 1, ex))
            time.sleep(3)
    return None, 0


def _fetch_all(e, wp_type):
    """Descarga todos los posts publicados de un CPT con paginación."""
    items = []
    page = 1
    while True:
        path = "/wp-json/wp/v2/%s?status=publish&per_page=100&page=%d&_fields=id,title,slug" % (wp_type, page)
        data, total = _fetch(e, path)
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.3)
    return items


def _clean_title(raw):
    t = html.unescape(raw)
    t = re.sub(r'<[^>]+>', '', t)
    return t.strip()


def _extract_keywords(title, slug, type_key):
    """Genera keywords de enlace a partir del título y slug."""
    kws = set()
    clean = _clean_title(title).lower()
    kws.add(clean)

    # Del slug: reemplazar guiones por espacios
    slug_text = slug.replace("-", " ").strip()
    kws.add(slug_text)

    # Quitar prefijos comunes del título
    for prefix in ["tour ", "seguro ", "crucero ", "vuelo ", "hotel ",
                    "mundo ", "mundo - ", "europa - ", "asia - "]:
        if clean.startswith(prefix):
            stripped = clean[len(prefix):].strip()
            if len(stripped) > 3:
                kws.add(stripped)

    # Quitar prefijos del slug
    for prefix in ["tour-", "seguro-", "crucero-", "vuelo-", "hotel-",
                    "mundo-", "wp-single-"]:
        if slug.startswith(prefix):
            stripped = slug[len(prefix):].replace("-", " ").strip()
            if len(stripped) > 3:
                kws.add(stripped)

    # Extraer nombre de destino si es tipo servicio
    if type_key in ("tours", "cruceros", "vuelos", "hoteles"):
        parts = clean.split()
        # "tour japón" → "japón"
        if len(parts) >= 2:
            destino = " ".join(parts[1:])
            if len(destino) > 2:
                kws.add(destino)

    return sorted(kws)


def build_catalog():
    env = _env()
    print("=" * 60)
    print("CONSTRUYENDO CATÁLOGO DE ENLACES")
    print("=" * 60)

    catalog = []

    # 1) Blogs
    print("\n1) Blogs (pt_blog_article)...")
    blogs = _fetch_all(env, BLOG_CPT["wp_type"])
    print("   %d blogs encontrados" % len(blogs))
    for b in blogs:
        title = _clean_title(b["title"]["rendered"] if isinstance(b["title"], dict) else b["title"])
        catalog.append({
            "url": SITE_BASE + BLOG_CPT["url_prefix"] + b["slug"],
            "title": title,
            "slug": b["slug"],
            "type": "blog",
            "cluster": "Blog",
            "wp_id": b["id"],
            "keywords": _extract_keywords(title, b["slug"], "blog"),
        })

    # 2) Service CPTs
    for cpt in CPTS:
        print("\n2) %s (%s)..." % (cpt["cluster"], cpt["wp_type"]))
        items = _fetch_all(env, cpt["wp_type"])
        print("   %d items" % len(items))
        for item in items:
            title = _clean_title(item["title"]["rendered"] if isinstance(item["title"], dict) else item["title"])
            catalog.append({
                "url": SITE_BASE + cpt["url_prefix"] + item["slug"],
                "title": title,
                "slug": item["slug"],
                "type": cpt["type_key"],
                "cluster": cpt["cluster"],
                "wp_id": item["id"],
                "keywords": _extract_keywords(title, item["slug"], cpt["type_key"]),
            })

    # 3) Guardar
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("CATÁLOGO GUARDADO: %s" % CATALOG_PATH)
    _print_stats(catalog)
    return catalog


def _print_stats(catalog):
    by_type = {}
    for item in catalog:
        t = item["cluster"]
        by_type[t] = by_type.get(t, 0) + 1
    print("\nTotal: %d URLs enlazables" % len(catalog))
    for t in sorted(by_type, key=lambda x: -by_type[x]):
        print("  %s: %d" % (t, by_type[t]))


def show_stats():
    if not os.path.exists(CATALOG_PATH):
        print("No hay catálogo. Corre sin --stats primero.")
        return
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)
    _print_stats(catalog)


if __name__ == "__main__":
    if "--stats" in sys.argv:
        show_stats()
    else:
        build_catalog()
