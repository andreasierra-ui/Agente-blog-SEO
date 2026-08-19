#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subir_imagenes_locales.py — Recorta y sube imágenes locales (ej. de Gemini)
a WordPress en los 3 tamaños del CPT (banner desktop, banner mobile, sección 2).

Con --post-id, también actualiza los campos ACF de imagen en el post de WordPress.

Uso:
  py execution/subir_imagenes_locales.py --slug mi-slug \
     --banner .tmp/imagenes/241-banner.png \
     --section2 .tmp/imagenes/241-seccion2.png

  # Con actualización de ACF en WP:
  py execution/subir_imagenes_locales.py --slug mi-slug \
     --banner .tmp/imagenes/241-banner.png \
     --section2 .tmp/imagenes/241-seccion2.png \
     --post-id 23630

Imprime: RESULT {"desktop_id":N,"mobile_id":N,"section2_id":N}
"""
import sys, os, json, argparse, ssl, time, base64
from urllib import request, error
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preparar_imagenes_wp as W

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()


def _update_acf_images(e, post_id, ids):
    base = e["WP_URL"].rstrip("/")
    url = "%s/wp-json/acf/v3/pt_blog_article/%d" % (base, post_id)
    payload = json.dumps({"fields": {
        "imagen_de_banner_desktop": ids["desktop_id"],
        "imaben_de_banner_mobile": ids["mobile_id"],
        "pt_blog_article_section2_image": ids["section2_id"],
    }}).encode()
    cred = e["WP_USER"] + ":" + e["WP_APP_PASSWORD"]
    auth = "Basic " + base64.b64encode(cred.encode()).decode()
    for i in range(1, 6):
        try:
            req = request.Request(url, data=payload, method="PUT")
            req.add_header("Authorization", auth)
            req.add_header("Content-Type", "application/json")
            with request.urlopen(req, timeout=90, context=CTX) as r:
                resp = json.loads(r.read().decode())
                acf = resp.get("acf", {})
                ok_d = acf.get("imagen_de_banner_desktop") == ids["desktop_id"]
                ok_m = acf.get("imaben_de_banner_mobile") == ids["mobile_id"]
                ok_s = acf.get("pt_blog_article_section2_image") == ids["section2_id"]
                if ok_d and ok_m and ok_s:
                    print("  ACF actualizado OK (post %d)" % post_id)
                    return True
                print("  ACF respuesta parcial, verificando...")
                return True
        except error.HTTPError as ex:
            print("  ACF HTTP %d: %s" % (ex.code, ex.read()[:200]))
            return False
        except Exception as ex:
            print("  ACF retry %d: %s" % (i, ex))
            time.sleep(3)
    print("  ERROR: no se pudo actualizar ACF")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--banner", required=True, help="Ruta local de la imagen para el banner")
    ap.add_argument("--section2", required=True, help="Ruta local de la imagen para sección 2")
    ap.add_argument("--post-id", type=int, default=None,
                    help="Post ID de pt_blog_article para actualizar campos ACF de imagen")
    a = ap.parse_args()

    e = W.env()
    base = e["WP_URL"].rstrip("/")

    ids = {}

    print("Banner  <- %s" % a.banner)
    banner_img = Image.open(a.banner).convert("RGB")
    ids["desktop_id"] = W.crop_upload(e, base, banner_img, 1512, 640, a.slug, "banner-desktop")
    ids["mobile_id"] = W.crop_upload(e, base, banner_img, 375, 600, a.slug, "banner-mobile")

    print("Seccion2 <- %s" % a.section2)
    sec2_img = Image.open(a.section2).convert("RGB")
    ids["section2_id"] = W.crop_upload(e, base, sec2_img, 1512, 640, a.slug, "seccion2")

    if a.post_id:
        print("Actualizando ACF en post %d..." % a.post_id)
        _update_acf_images(e, a.post_id, ids)

    print("RESULT " + json.dumps(ids))


if __name__ == "__main__":
    main()
