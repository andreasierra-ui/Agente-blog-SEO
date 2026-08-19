#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reparar_imagenes.py — Reemplaza imágenes específicas en artículos de blog
de Mundo Joven. Descarga de Pexels, recorta y sube a WP, actualiza ACF.

Solo toca campos de imagen, NO contenido.

Uso:
  py execution/reparar_imagenes.py
  (Las reparaciones están hardcodeadas en el script)
"""
import sys, os, io, json, time, base64, ssl
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
            print(f"  ...GET falló ({i}/{reintentos}): {ex}")
            time.sleep(3)
    sys.exit(f"ERROR: sin respuesta de {url}")


def pexels_url(key, photo_id):
    data = json.loads(_get(f"https://api.pexels.com/v1/photos/{photo_id}",
                           headers={"Authorization": key}))
    print(f"  Pexels {photo_id}: {data['width']}x{data['height']} por {data.get('photographer','?')}")
    return data["src"]["original"] + "?auto=compress&cs=tinysrgb&w=2400"


def descarga_img(url):
    return Image.open(io.BytesIO(_get(url))).convert("RGB")


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


def subir(e, jpg, filename, reintentos=8):
    url = e["WP_URL"].rstrip("/") + "/wp-json/wp/v2/media"
    for i in range(1, reintentos + 1):
        req = request.Request(url, data=jpg, method="POST")
        req.add_header("Authorization", auth(e))
        req.add_header("Content-Type", "image/jpeg")
        req.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        try:
            with request.urlopen(req, timeout=120, context=CTX) as r:
                data = json.loads(r.read().decode())
                return data["id"], data.get("source_url", "")
        except error.HTTPError as ex:
            sys.exit(f"ERROR al subir {filename} (HTTP {ex.code}): {ex.read()[:200]}")
        except Exception as ex:
            print(f"  ...subida falló ({i}/{reintentos}): {ex}")
            time.sleep(3)
    sys.exit("ERROR: no se pudo subir la imagen")


def crop_upload(e, img, w, h, slug, nombre):
    c = cover(img, w, h)
    buf = io.BytesIO()
    c.save(buf, format="JPEG", quality=85, optimize=True)
    fid, src_url = subir(e, buf.getvalue(), f"{slug}-{nombre}.jpg")
    print(f"    {nombre} {w}x{h} -> media ID {fid}")
    return fid


def api_post(e, path, payload):
    url = e["WP_URL"].rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    for i in range(1, 9):
        req = request.Request(url, data=data, method="POST")
        req.add_header("Authorization", auth(e))
        req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with request.urlopen(req, timeout=60, context=CTX) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except error.HTTPError as ex:
            return ex.code, {"_raw": ex.read().decode("utf-8", "replace")[:400]}
        except Exception as ex:
            print(f"  ...conexión falló ({i}/8): {ex}")
            time.sleep(3)
    return 0, {"error": "timeout"}


def replace_banner_and_section2(e, key, post_id, slug, banner_pexels_id, section2_pexels_id):
    """Replace both banner (desktop+mobile) and section2 image."""
    print(f"\n--- Post {post_id}: reemplazando banner + section2 ---")

    print("  Descargando banner...")
    banner_img = descarga_img(pexels_url(key, banner_pexels_id))
    print("  Descargando section2...")
    sec2_img = descarga_img(pexels_url(key, section2_pexels_id))

    desktop_id = crop_upload(e, banner_img, 1512, 640, slug, "banner-desktop-v2")
    mobile_id = crop_upload(e, banner_img, 375, 600, slug, "banner-mobile-v2")
    sec2_id = crop_upload(e, sec2_img, 1512, 640, slug, "seccion2-v2")

    print("  Actualizando ACF...")
    st, resp = api_post(e, f"/wp-json/acf/v3/pt_blog_article/{post_id}", {
        "fields": {
            "imagen_de_banner_desktop": desktop_id,
            "imaben_de_banner_mobile": mobile_id,
            "pt_blog_article_section2_image": sec2_id,
        }
    })
    print(f"  -> HTTP {st}")
    return {"desktop_id": desktop_id, "mobile_id": mobile_id, "section2_id": sec2_id}


def replace_section2_only(e, key, post_id, slug, section2_pexels_id):
    """Replace only the section2 image, leave banner as-is."""
    print(f"\n--- Post {post_id}: reemplazando solo section2 ---")

    print("  Descargando section2...")
    sec2_img = descarga_img(pexels_url(key, section2_pexels_id))
    sec2_id = crop_upload(e, sec2_img, 1512, 640, slug, "seccion2-v2")

    print("  Actualizando ACF...")
    st, resp = api_post(e, f"/wp-json/acf/v3/pt_blog_article/{post_id}", {
        "fields": {
            "pt_blog_article_section2_image": sec2_id,
        }
    })
    print(f"  -> HTTP {st}")
    return {"section2_id": sec2_id}


def main():
    e = env()
    key = e.get("PEXELS_API_KEY")
    if not key:
        sys.exit("ERROR: falta PEXELS_API_KEY en .env")

    # --- Reparaciones definidas ---
    # 245: banner no tiene "vibra de viaje" + section2 es igual al banner
    r1 = replace_banner_and_section2(e, key,
        post_id=23654,
        slug="mundo-viajar-en-familia-pareja-o-grupo",
        banner_pexels_id=7343992,   # couple exploring ruins/destination
        section2_pexels_id=7368263, # family with kids at airport/travel
    )

    # 246: banner "no la entendí" + section2 no transmite viajar solo
    r2 = replace_banner_and_section2(e, key,
        post_id=23659,
        slug="mundo-como-conocer-gente-hacer-amigos-viajando",
        banner_pexels_id=1143514,   # solo traveler with backpack exploring
        section2_pexels_id=3184177, # group of people laughing/socializing
    )

    # 247: solo section2 no concuerda
    r3 = replace_section2_only(e, key,
        post_id=23664,
        slug="seguros-que-cubre-seguro-de-viaje-como-elegir",
        section2_pexels_id=7368308, # person with passport/travel docs
    )

    # 248: solo section2 no concuerda
    r4 = replace_section2_only(e, key,
        post_id=23669,
        slug="seguros-5-tips-contratar-seguro-de-viaje",
        section2_pexels_id=7010194, # travel planning with documents
    )

    print("\n" + "=" * 60)
    print("IMÁGENES REPARADAS")
    print(f"  245: {r1}")
    print(f"  246: {r2}")
    print(f"  247: {r3}")
    print(f"  248: {r4}")
    print("=" * 60)


if __name__ == "__main__":
    main()
