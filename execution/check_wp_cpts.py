#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check available WP REST API post types and find pt_travel_compositor."""
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
        return e.code, e.read().decode("utf-8", "replace")[:200]

def main():
    env = cargar_env()

    # 1) List all available post types via REST API
    print("=== WP REST API Types ===")
    st, data = api_get(env, "/wp-json/wp/v2/types")
    if st == 200:
        for slug, info in sorted(data.items()):
            rest_base = info.get("rest_base", "?")
            name = info.get("name", "?")
            print(f"  {slug} (rest_base: {rest_base}) — {name}")

    # 2) Check if pt_travel_compositor exists
    print("\n=== Checking pt_travel_compositor ===")
    for base in ["pt_travel_compositor", "travel_compositor", "compositor"]:
        st, d = api_get(env, f"/wp-json/wp/v2/{base}?per_page=1")
        print(f"  /wp-json/wp/v2/{base}: HTTP {st}")
        if st == 200 and d:
            print(f"    First item: id={d[0].get('id')}, type={d[0].get('type')}, title={d[0].get('title', {}).get('rendered', '?')[:60]}")

    # 3) Check a working product: read article 23242 (known-good, reference article)
    print("\n=== Reference article 23242 products ===")
    st, data = api_get(env, "/wp-json/acf/v3/pt_blog_article/23242")
    if st == 200:
        acf = data.get("acf", data)
        prods = acf.get("pt_blog_article_producto_relacionado", [])
        print(f"  {len(prods)} products:")
        for i, p in enumerate(prods):
            if isinstance(p, dict):
                pi = p.get("pt_blog_article_producto_item")
                if isinstance(pi, dict):
                    print(f"  {i+1}. ID={pi.get('ID')}, type={pi.get('post_type')}, title={pi.get('post_title', '?')[:50]}")
                else:
                    print(f"  {i+1}. value={pi} (type: {type(pi).__name__})")
            else:
                print(f"  {i+1}. raw: {p}")

    # 4) Check wp_single_tours for a parent/compositor field
    print("\n=== wp_single_tours ACF fields (sample tour 17962) ===")
    st, data = api_get(env, "/wp-json/acf/v3/wp_single_tours/17962")
    if st == 200:
        acf = data.get("acf", data)
        for k, v in sorted(acf.items()):
            if "compositor" in k.lower() or "parent" in k.lower() or "related" in k.lower():
                print(f"  ** {k}: {v}")
            elif isinstance(v, str) and len(v) < 100:
                print(f"  {k}: {v}")
            elif isinstance(v, (int, bool, float)):
                print(f"  {k}: {v}")
            elif isinstance(v, list):
                print(f"  {k}: (list, {len(v)} items)")
            elif isinstance(v, dict):
                keys = list(v.keys())[:5]
                print(f"  {k}: (dict, keys: {keys})")
            else:
                print(f"  {k}: ({type(v).__name__})")

if __name__ == "__main__":
    main()
