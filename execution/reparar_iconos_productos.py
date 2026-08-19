#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reparar_iconos_productos.py — Repara íconos y productos en artículos existentes.

Lee el estado actual de los campos S3 (items) y S6 (productos) de WP,
re-asigna íconos con keyword matching (solo íconos verificados del kit),
y asigna productos pt_travel_compositor válidos.

NO toca el contenido, títulos, FAQs ni imágenes.

Uso:
  py execution/reparar_iconos_productos.py 23654 23659 23664 23669
  py execution/reparar_iconos_productos.py 23654  # solo uno
"""
import sys, os, json, time, base64, ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "execution"))

from asignar_iconos import llenar_iconos
from sugerir_productos import load_cache, suggest, _normalize, MACRO_REGIONS


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


def api(env, method, path, payload=None, reintentos=8):
    url = env["WP_URL"].rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    ctx = ssl.create_default_context()
    from urllib import request, error
    for intento in range(1, reintentos + 1):
        req = request.Request(url, data=data, method=method)
        token = base64.b64encode(
            f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()
        ).decode()
        req.add_header("Authorization", f"Basic {token}")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with request.urlopen(req, timeout=60, context=ctx) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(body)
            except Exception:
                return e.code, {"_raw": body[:400]}
        except Exception as e:
            print(f"  ...conexión falló ({intento}/{reintentos}): {e}")
            time.sleep(3)
    sys.exit(f"ERROR de conexión tras {reintentos} intentos")


def _guess_destino(title):
    t = _normalize(title)
    for region, aliases in MACRO_REGIONS.items():
        if any(a in t for a in aliases):
            return region
    return None


def reparar_post(env, post_id, excluir_productos=None):
    print(f"\n{'='*60}")
    print(f"REPARANDO POST {post_id}")
    print(f"{'='*60}")

    # 1) Leer estado actual de ACF
    print("\n1) Leyendo campos ACF actuales...")
    st, data = api(env, "GET", f"/wp-json/acf/v3/pt_blog_article/{post_id}")
    if st != 200:
        print(f"   ERROR: HTTP {st}")
        return None
    acf = data.get("acf", data)

    # 2) Reparar íconos (S3)
    items = acf.get("pt_blog_article_item_list", [])
    print(f"\n2) Re-asignando íconos ({len(items)} items)...")
    for item in items:
        item.pop("_icon_hint", None)
    llenar_iconos(items, forzar=True)
    for i, item in enumerate(items):
        titulo = item.get("pt_blog_article_title_list", "???")
        icono = item.get("pt_blog_article_icon_list", "???")
        print(f"   {i+1}. [{icono}] {titulo[:50]}")

    # 3) Reparar productos (S6)
    titulo_articulo = acf.get("pt_blog_article_title", "")
    print(f"\n3) Sugiriendo productos para: {titulo_articulo[:50]}...")
    destino = _guess_destino(titulo_articulo)
    results = suggest(titulo_articulo, [destino] if destino else None,
                      excluir_productos, top_n=4)
    product_ids = [p["id"] for p in results]
    for i, p in enumerate(results):
        print(f"   {i+1}. [{p['id']}] {p['title'][:50]} ({', '.join(p.get('regions', []))})")

    productos_acf = [{"pt_blog_article_producto_item": pid} for pid in product_ids]

    # 4) Enviar SOLO íconos y productos a WP
    print(f"\n4) Actualizando ACF (solo íconos + productos)...")
    payload = {
        "fields": {
            "pt_blog_article_item_list": items,
            "pt_blog_article_producto_relacionado": productos_acf,
        }
    }
    st, resp = api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}", payload)
    if st == 200:
        print(f"   -> OK (HTTP {st})")
    else:
        print(f"   -> ERROR (HTTP {st}): {resp}")

    # 5) Verificar
    print(f"\n5) Verificando...")
    st, check = api(env, "GET", f"/wp-json/acf/v3/pt_blog_article/{post_id}")
    if st == 200:
        check_acf = check.get("acf", check)
        check_items = check_acf.get("pt_blog_article_item_list", [])
        check_prods = check_acf.get("pt_blog_article_producto_relacionado", [])

        icon_ok = all(
            item.get("pt_blog_article_icon_list", "").startswith("fa-sharp")
            for item in check_items
        )
        prod_ok = all(
            isinstance(p.get("pt_blog_article_producto_item"), dict)
            and p["pt_blog_article_producto_item"].get("ID")
            for p in check_prods
        ) if check_prods else False

        print(f"   Íconos: {'OK' if icon_ok else 'FALLO'}")
        if not icon_ok:
            for item in check_items:
                print(f"     - {item.get('pt_blog_article_icon_list', 'VACÍO')}")
        print(f"   Productos: {'OK' if prod_ok else 'FALLO'}")
        if check_prods:
            for p in check_prods:
                pi = p.get("pt_blog_article_producto_item")
                if isinstance(pi, dict):
                    print(f"     - {pi.get('ID')} ({pi.get('post_type')}) {pi.get('post_title', '')[:40]}")
                else:
                    print(f"     - {pi} (type: {type(pi).__name__})")

    return product_ids


def main():
    if len(sys.argv) < 2:
        print("Uso: py execution/reparar_iconos_productos.py <post_id1> [post_id2] ...")
        sys.exit(0)

    post_ids = [int(x) for x in sys.argv[1:]]
    env = cargar_env()

    all_used = set()
    for post_id in post_ids:
        used = reparar_post(env, post_id, excluir_productos=all_used)
        if used:
            all_used.update(used)

    print(f"\n{'='*60}")
    print(f"REPARACIÓN COMPLETA — {len(post_ids)} posts procesados")
    print(f"Productos usados: {sorted(all_used)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
