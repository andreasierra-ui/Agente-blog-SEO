#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: lee campos ACF de un post para verificar íconos y productos."""
import sys, os, json, base64, ssl
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def cargar_env():
    env = {}
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def api_get(env, path):
    url = env["WP_URL"].rstrip("/") + path
    ctx = ssl.create_default_context()
    req = request.Request(url, method="GET")
    token = base64.b64encode(f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    try:
        with request.urlopen(req, timeout=30, context=ctx) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return e.code, body[:500]

def main():
    post_id = sys.argv[1] if len(sys.argv) > 1 else "23654"
    env = cargar_env()

    print(f"=== Diagnóstico ACF para post {post_id} ===\n")

    # 1) Leer campos ACF via ACF REST API v3
    st, data = api_get(env, f"/wp-json/acf/v3/pt_blog_article/{post_id}")
    print(f"ACF API status: {st}")

    if st != 200:
        print(f"Error: {data}")
        return

    acf = data.get("acf", data)

    # 2) Revisar íconos (S3 items)
    items = acf.get("pt_blog_article_item_list", [])
    print(f"\n--- ÍCONOS (S3) --- ({len(items)} items)")
    for i, item in enumerate(items):
        titulo = item.get("pt_blog_article_title_list", "???")
        icono = item.get("pt_blog_article_icon_list", "<<VACÍO>>")
        print(f"  {i+1}. [{icono}] {titulo[:60]}")

    # 3) Revisar productos (S6)
    productos = acf.get("pt_blog_article_producto_relacionado", [])
    print(f"\n--- PRODUCTOS (S6) --- ({len(productos)} entries)")
    if productos:
        for i, p in enumerate(productos):
            if isinstance(p, dict):
                pid = p.get("pt_blog_article_producto_item", "???")
                print(f"  {i+1}. product_id: {pid} (type: {type(pid).__name__})")
            else:
                print(f"  {i+1}. raw value: {p} (type: {type(p).__name__})")
    else:
        print("  (vacío)")

    # 4) Revisar imágenes
    desktop = acf.get("imagen_de_banner_desktop", "")
    mobile = acf.get("imaben_de_banner_mobile", "")
    s2_img = acf.get("pt_blog_article_section2_image", "")
    print(f"\n--- IMÁGENES ---")
    print(f"  desktop: {desktop}")
    print(f"  mobile:  {mobile}")
    print(f"  section2: {s2_img}")

    # 5) Dump completo de keys para debug
    print(f"\n--- TODAS LAS KEYS ACF ---")
    for k in sorted(acf.keys()):
        v = acf[k]
        if isinstance(v, str) and len(v) > 100:
            print(f"  {k}: (string, {len(v)} chars)")
        elif isinstance(v, list):
            print(f"  {k}: (list, {len(v)} items)")
        else:
            print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
