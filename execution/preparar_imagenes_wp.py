#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_imagenes_wp.py — Consigue imágenes de ALTA RESOLUCIÓN para un blog de
Mundo Joven (por defecto desde Pexels), las recorta a los tamaños del CPT y las
sube a WordPress. Devuelve los IDs de adjunto para enlazarlas en los campos ACF.

- Banner (desktop 1512x640 + mobile 375x600): salen de la MISMA foto.
- Sección 2 (1512x640): sale de una foto DISTINTA (regla de marca v0.5).

Uso:
    py execution/preparar_imagenes_wp.py --slug mundo-mal-de-altura \
        --banner-query "Machu Picchu Peru" --section2-query "Cusco Peru"

Imprime: RESULT {"desktop_id":N,"mobile_id":N,"section2_id":N}
Requiere en .env: WP_URL, WP_USER, WP_APP_PASSWORD, PEXELS_API_KEY.
"""
import sys, os, io, json, time, base64, ssl, argparse
from urllib import request, error, parse
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()


def env():
    e = {}
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def _get(url, headers=None, reintentos=8):
    h = {"User-Agent": "Mozilla/5.0 (compatible; MundoJovenAgent/1.0)"}
    h.update(headers or {})
    for i in range(1, reintentos + 1):
        try:
            req = request.Request(url, headers=h)
            with request.urlopen(req, timeout=90, context=CTX) as r:
                return r.read()
        except Exception as ex:
            print(f"  ...GET falló ({i}/{reintentos}): {ex}; reintento")
            time.sleep(3)
    sys.exit(f"ERROR: sin respuesta de {url}")


def pexels_search(key, query):
    """Lista candidatos de Pexels (para revisión visual antes de elegir)."""
    q = parse.quote(query)
    data = json.loads(_get(f"https://api.pexels.com/v1/search?query={q}&per_page=10&orientation=landscape&size=large",
                           headers={"Authorization": key}))
    return [p for p in data.get("photos", []) if p.get("width", 0) >= 1512]


def pexels_by_id(key, photo_id):
    data = json.loads(_get(f"https://api.pexels.com/v1/photos/{photo_id}", headers={"Authorization": key}))
    print(f"  Pexels foto fija id={photo_id} ({data['width']}x{data['height']}) por {data.get('photographer','?')} — alt: {data.get('alt','')}")
    return data["src"]["original"] + "?auto=compress&cs=tinysrgb&w=2400"


def pexels_pick(key, query, elegir=0):
    """Devuelve la URL original de una foto landscape de alta resolución de Pexels."""
    fotos = pexels_search(key, query)
    if not fotos:
        sys.exit(f"ERROR: Pexels no devolvió fotos usables para '{query}'")
    p = fotos[min(elegir, len(fotos) - 1)]
    print(f"  Pexels '{query}': foto {p['id']} ({p['width']}x{p['height']}) por {p.get('photographer','?')}")
    # Versión comprimida ancha (rápida y de sobra para recortar)
    return p["src"]["original"] + "?auto=compress&cs=tinysrgb&w=2400"


def cover(img, w, h):
    sr, tr = img.width / img.height, w / h
    if sr > tr:
        nh, nw = h, round(h * sr)
    else:
        nw, nh = w, round(w / sr)
    r = img.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - w) // 2, (nh - h) // 2
    return r.crop((l, t, l + w, t + h))


def auth(e):
    return "Basic " + base64.b64encode(f"{e['WP_USER']}:{e['WP_APP_PASSWORD']}".encode()).decode()


def subir(e, base, jpg, filename, reintentos=8):
    url = base + "/wp-json/wp/v2/media"
    for i in range(1, reintentos + 1):
        req = request.Request(url, data=jpg, method="POST")
        req.add_header("Authorization", auth(e))
        req.add_header("Content-Type", "image/jpeg")
        req.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        try:
            with request.urlopen(req, timeout=120, context=CTX) as r:
                return json.loads(r.read().decode())["id"]
        except error.HTTPError as ex:
            sys.exit(f"ERROR al subir {filename} (HTTP {ex.code}): {ex.read()[:200]}")
        except Exception as ex:
            print(f"  ...subida falló ({i}/{reintentos}): {ex}; reintento")
            time.sleep(3)
    sys.exit("ERROR: no se pudo subir la imagen")


def descarga_img(url):
    return Image.open(io.BytesIO(_get(url))).convert("RGB")


def crop_upload(e, base, img, w, h, slug, nombre):
    c = cover(img, w, h)
    buf = io.BytesIO()
    c.save(buf, format="JPEG", quality=85, optimize=True)
    fid = subir(e, base, buf.getvalue(), f"{slug}-{nombre}.jpg")
    print(f"    {nombre} {w}x{h} -> media ID {fid}")
    return fid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--banner-query", default=None)
    ap.add_argument("--section2-query", default=None)
    ap.add_argument("--banner-index", type=int, default=0, help="Índice del candidato ya verificado visualmente")
    ap.add_argument("--section2-index", type=int, default=0)
    ap.add_argument("--banner-id", type=int, default=None, help="ID exacto de foto de Pexels (ya verificada) para el banner")
    ap.add_argument("--section2-id", type=int, default=None, help="ID exacto de foto de Pexels (ya verificada) para la sección 2")
    ap.add_argument("--banner-local", default=None, help="Ruta a imagen local para el banner (ej. de Gemini AI)")
    ap.add_argument("--section2-local", default=None, help="Ruta a imagen local para la sección 2 (ej. de Gemini AI)")
    ap.add_argument("--list-only", action="store_true",
                     help="Solo lista candidatos (id, dimensiones, url de imagen) para revisión visual; no descarga ni sube nada")
    a = ap.parse_args()

    if a.list_only:
        e = env()
        key = e.get("PEXELS_API_KEY")
        for etiqueta, q in [("BANNER", a.banner_query), ("SECCION2", a.section2_query)]:
            print(f"--- {etiqueta}: '{q}' ---")
            for i, p in enumerate(pexels_search(key, q)):
                print(f"  [{i}] id={p['id']} {p['width']}x{p['height']} url={p['src']['large']}")
        return

    e = env()
    base = e["WP_URL"].rstrip("/")
    key = e.get("PEXELS_API_KEY")
    if not key:
        sys.exit("ERROR: falta PEXELS_API_KEY en .env")

    if a.banner_local:
        print(f"Banner  <- local '{a.banner_local}'")
        banner_img = Image.open(a.banner_local).convert("RGB")
    elif a.banner_id:
        print("Banner  <- Pexels ID fijo")
        banner_img = descarga_img(pexels_by_id(key, a.banner_id))
    else:
        print(f"Banner  <- Pexels '{a.banner_query}' [{a.banner_index}]")
        banner_img = descarga_img(pexels_pick(key, a.banner_query, a.banner_index))
    if a.section2_local:
        print(f"Sección2 <- local '{a.section2_local}'")
        sec2_img = Image.open(a.section2_local).convert("RGB")
    elif a.section2_id:
        print("Sección2 <- Pexels ID fijo")
        sec2_img = descarga_img(pexels_by_id(key, a.section2_id))
    else:
        print(f"Sección2 <- Pexels '{a.section2_query}' [{a.section2_index}]")
        sec2_img = descarga_img(pexels_pick(key, a.section2_query, a.section2_index))

    ids = {
        "desktop_id": crop_upload(e, base, banner_img, 1512, 640, a.slug, "banner-desktop"),
        "mobile_id": crop_upload(e, base, banner_img, 375, 600, a.slug, "banner-mobile"),
        "section2_id": crop_upload(e, base, sec2_img, 1512, 640, a.slug, "seccion2"),
    }
    print("RESULT " + json.dumps(ids))


if __name__ == "__main__":
    main()
