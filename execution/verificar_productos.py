#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica el post_type de una lista de product IDs en WordPress."""
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

    # IDs de productos de los 4 artículos (del manifest)
    ids_to_check = [17962, 23149, 13485, 13484, 10985, 10986, 19056, 20307,
                    16743, 10835, 13492, 13516, 13487, 13486, 19681, 12721]

    print("=== Verificando post_type de product IDs ===\n")

    types_found = {}
    for pid in ids_to_check:
        # Try different CPT endpoints
        for cpt in ["wp_single_tours", "pt_travel_compositor"]:
            st, data = api_get(env, f"/wp-json/wp/v2/{cpt}/{pid}")
            if st == 200:
                title = data.get("title", {}).get("rendered", "???") if isinstance(data, dict) else "???"
                post_type = data.get("type", cpt)
                print(f"  {pid}: {post_type} — {title[:60]}")
                types_found[pid] = post_type
                break
        else:
            # Try generic post endpoint
            st, data = api_get(env, f"/wp-json/wp/v2/posts/{pid}")
            if st == 200:
                print(f"  {pid}: post — {data.get('title', {}).get('rendered', '???')[:60]}")
                types_found[pid] = "post"
            else:
                print(f"  {pid}: NOT FOUND (HTTP {st})")
                types_found[pid] = "NOT_FOUND"

    print(f"\n--- Resumen ---")
    by_type = {}
    for pid, pt in types_found.items():
        by_type.setdefault(pt, []).append(pid)
    for pt, pids in by_type.items():
        print(f"  {pt}: {len(pids)} items — {pids}")

if __name__ == "__main__":
    main()
