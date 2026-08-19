#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_imagen_ia.py — Genera imágenes a la medida con la IA de Gemini
("Nano Banana", gemini-2.5-flash-image), las recorta a los tamaños del CPT y
las sube a WordPress. Úsalo cuando Pexels no tenga la escena/demografía exacta.

Uso (genera solo lo que pases):
  py execution/generar_imagen_ia.py --slug mi-slug \
     --banner-prompt "..." --section2-prompt "..."

Requiere en .env: WP_URL, WP_USER, WP_APP_PASSWORD, GEMINI_API_KEY.
Reutiliza los helpers de preparar_imagenes_wp.py (env, cover, crop_upload).
OJO: cada imagen generada tiene un costo en la API de Gemini.
"""
import sys, io, json, time, base64, ssl, argparse
from urllib import request, error
from PIL import Image
import preparar_imagenes_wp as W

# Modelos de imagen de Gemini disponibles (de mejor a más económico):
#   gemini-3-pro-image      = "Nano Banana Pro" (mejor calidad)
#   gemini-3.1-flash-image  = "Nano Banana 2"
#   gemini-2.5-flash-image  = "Nano Banana"
# TODOS requieren FACTURACIÓN activada (el tier gratuito da límite 0 -> HTTP 429).
MODELS = ["gemini-3-pro-image", "gemini-2.5-flash-image"]
CTX = ssl.create_default_context()

# Sufijo de estilo para que todas salgan realistas y profesionales.
ESTILO = (" Fotografía realista de alta calidad, estilo editorial de revista de viajes, "
          "iluminación natural, composición horizontal, sin texto ni marcas de agua, sin deformidades.")


def gen_image(key, prompt):
    body = json.dumps({"contents": [{"parts": [{"text": prompt + ESTILO}]}]}).encode("utf-8")
    last = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        for intento in range(3):
            try:
                req = request.Request(url, data=body, method="POST",
                                      headers={"Content-Type": "application/json"})
                with request.urlopen(req, timeout=150, context=CTX) as r:
                    data = json.loads(r.read().decode())
                for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        print(f"  imagen generada con {model}")
                        return Image.open(io.BytesIO(base64.b64decode(inline["data"]))).convert("RGB")
                last = f"{model}: respuesta sin imagen ({json.dumps(data)[:200]})"
                break
            except error.HTTPError as e:
                cuerpo = e.read().decode("utf-8", "replace")
                if e.code == 429 and "billing" in cuerpo.lower():
                    sys.exit("ERROR: la API de Gemini requiere FACTURACIÓN activada para generar "
                             "imágenes (el tier gratuito da límite 0). Actívala en el proyecto de "
                             "tu API key y reintenta.")
                last = f"{model} HTTP {e.code}: {cuerpo[:200]}"
                if e.code in (400, 404):
                    break
                time.sleep(5)
            except Exception as e:
                last = f"{model}: {e}"
                time.sleep(3)
    sys.exit(f"ERROR generando imagen: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--banner-prompt", default=None)
    ap.add_argument("--section2-prompt", default=None)
    a = ap.parse_args()

    e = W.env()
    base = e["WP_URL"].rstrip("/")
    key = e.get("GEMINI_API_KEY")
    if not key:
        sys.exit("ERROR: falta GEMINI_API_KEY en .env")

    ids = {}
    if a.banner_prompt:
        print(f"Banner  <- IA: {a.banner_prompt[:70]}...")
        img = gen_image(key, a.banner_prompt)
        ids["desktop_id"] = W.crop_upload(e, base, img, 1512, 640, a.slug, "banner-desktop")
        ids["mobile_id"] = W.crop_upload(e, base, img, 375, 600, a.slug, "banner-mobile")
    if a.section2_prompt:
        print(f"Sección2 <- IA: {a.section2_prompt[:70]}...")
        img2 = gen_image(key, a.section2_prompt)
        ids["section2_id"] = W.crop_upload(e, base, img2, 1512, 640, a.slug, "seccion2")

    print("RESULT " + json.dumps(ids))


if __name__ == "__main__":
    main()
