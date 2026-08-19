#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpiar_marcas.py — Reemplaza menciones de marcas/competidores en artículos WP.
Lee contenido actual de WP, aplica reemplazos, y actualiza solo los campos modificados.

NO toca estructura, títulos ni imágenes. Solo sustituye texto en richcontent.
"""
import sys, os, json, re, base64, ssl
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reemplazos: (regex pattern, replacement)
# El orden importa: patrones más específicos primero.
REPLACEMENTS = [
    # --- Aerolíneas (no aparecen en escaneo actual, pero por si acaso) ---
    (r'\bVolaris\b', 'aerolíneas nacionales'),
    (r'\bVivaAerobus\b', 'aerolíneas nacionales'),
    (r'\bViva Aerobus\b', 'aerolíneas nacionales'),
    (r'\bAeroméxico\b', 'aerolíneas nacionales'),

    # --- Hospedaje / reservas ---
    (r'\bAirbnb\b', 'departamento vacacional'),
    (r'\bBooking\.com\b', 'plataformas de hospedaje'),
    (r'\bBooking\b(?!\.)', 'plataformas de hospedaje'),
    (r'\bHostelworld\b', 'plataformas de hostales'),
    (r'\bHostelWorld\b', 'plataformas de hostales'),

    # --- Apps de gastos ---
    (r'\bSplitwise o Tricount\b', 'apps para dividir gastos'),
    (r'\bSplitwise\b', 'una app de gastos compartidos'),
    (r'\bTricount\b', 'apps de gastos compartidos'),

    # --- Parques temáticos ---
    (r'\bDisney, Universal, Sea World\b', 'los principales parques temáticos'),
    (r'\bDisney\b', 'parques temáticos'),
    (r'\bSea World\b', 'parques temáticos'),
    (r'\bSeaWorld\b', 'parques temáticos'),

    # --- Productividad ---
    (r'en Google Docs\b', 'en línea'),
    (r'\bGoogle Docs\b', 'un documento en línea'),
    (r'\bNotion\b', 'herramientas de organización'),

    # --- Transporte ---
    (r'\bUber\b', 'transporte privado'),
    (r'\bCabify\b', 'transporte privado'),
    (r'\bDidi\b', 'transporte privado'),

    # --- Renta de autos ---
    (r'\bHertz\b', 'agencias de renta de autos'),
    (r'\bAvis\b', 'agencias de renta de autos'),
    (r'\bEnterprise\b', 'agencias de renta de autos'),

    # --- Tarjetas de crédito (CUIDADO: "Visa" sin contexto de tarjeta NO se toca) ---
    (r'American Express Platinum, algunas Visa Signature, HSBC Premier',
     'tarjetas de crédito premium con beneficios de viaje'),
    (r'American Express Platinum', 'tarjetas de crédito premium'),
    (r'\bAmerican Express\b', 'tarjetas premium'),
    (r'\bHSBC Premier\b', 'tarjetas premium'),

    # --- Seguros ---
    (r'Rastreator\.mx o AseguraTuViaje\.com', 'comparadores de seguros en línea'),
    (r'Rastreator\.mx, AseguraTuViaje\.com', 'comparadores de seguros en línea'),
    (r'\bRastreator\.mx\b', 'comparadores de seguros'),
    (r'\bRastreator\b', 'comparadores de seguros'),
    (r'\bAseguraTuViaje\.com\b', 'comparadores de seguros'),
    (r'Assist Card, Mapfre, AXA Assistance, Chubb y otros',
     'las principales aseguradoras del mercado'),
    (r'Assist Card, Mapfre, AXA, Chubb',
     'las principales aseguradoras'),
    (r'Assist Card, AXA y Mapfre',
     'las principales aseguradoras de viaje'),
    (r'Assist Card, World Nomads',
     'aseguradoras especializadas en viajeros'),
    (r'\bAXA Assistance\b', 'aseguradoras internacionales'),
    (r'\bAXA\b', 'aseguradoras internacionales'),
    (r'\bAssist Card\b', 'aseguradoras de viaje'),
    (r'\bWorld Nomads\b', 'aseguradoras para viajeros'),
    (r'\bMapfre\b', 'aseguradoras internacionales'),
    (r'\bChubb\b', 'aseguradoras internacionales'),
]


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


def api(env, method, path, payload=None):
    url = env["WP_URL"].rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload else None
    ctx = ssl.create_default_context()
    import time
    for i in range(1, 9):
        req = request.Request(url, data=data, method=method)
        token = base64.b64encode(f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with request.urlopen(req, timeout=60, context=ctx) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except error.HTTPError as e:
            return e.code, {"_raw": e.read().decode("utf-8", "replace")[:400]}
        except Exception as e:
            print(f"  ...conexión falló ({i}/8): {e}")
            time.sleep(3)
    return 0, {"error": "timeout"}


def apply_replacements(text):
    """Aplica los reemplazos de marcas al texto. Retorna (texto_limpio, cambios)."""
    if not text:
        return text, []
    changes = []
    result = text
    for pattern, replacement in REPLACEMENTS:
        regex = re.compile(pattern)
        matches = regex.findall(result)
        if matches:
            for m in matches:
                changes.append(f"  '{m}' → '{replacement}'")
            result = regex.sub(replacement, result)
    return result, changes


def clean_post(env, post_id, dry_run=False):
    print(f"\n{'='*60}")
    print(f"POST {post_id}")
    print(f"{'='*60}")

    st, data = api(env, "GET", f"/wp-json/acf/v3/pt_blog_article/{post_id}")
    if st != 200:
        print(f"ERROR: HTTP {st}")
        return
    acf = data.get("acf", data)

    updates = {}
    total_changes = []

    # Richcontent fields
    for field in ["pt_blog_article_richcontent", "pt_blog_article_richcontent2",
                  "pt_blog_article_richcontent4"]:
        original = acf.get(field, "")
        cleaned, changes = apply_replacements(original)
        if changes:
            print(f"\n  [{field}] {len(changes)} cambios:")
            for c in changes:
                print(f"    {c}")
            updates[field] = cleaned
            total_changes.extend(changes)

    # S3 item content
    items = acf.get("pt_blog_article_item_list", [])
    items_changed = False
    for i, item in enumerate(items):
        content = item.get("pt_blog_article_richcontent_list", "")
        cleaned, changes = apply_replacements(content)
        if changes:
            print(f"\n  [item_{i}_content] {len(changes)} cambios:")
            for c in changes:
                print(f"    {c}")
            item["pt_blog_article_richcontent_list"] = cleaned
            items_changed = True
            total_changes.extend(changes)
    if items_changed:
        updates["pt_blog_article_item_list"] = items

    # FAQs
    faqs = acf.get("pt_blog_article_faqs", [])
    faqs_changed = False
    for i, faq in enumerate(faqs):
        for fkey in ["pt_blog_article_faq_title", "pt_blog_article_faq_content"]:
            content = faq.get(fkey, "")
            cleaned, changes = apply_replacements(content)
            if changes:
                print(f"\n  [faq_{i}_{fkey.split('_')[-1]}] {len(changes)} cambios:")
                for c in changes:
                    print(f"    {c}")
                faq[fkey] = cleaned
                faqs_changed = True
                total_changes.extend(changes)
    if faqs_changed:
        updates["pt_blog_article_faqs"] = faqs

    if not total_changes:
        print("\n  (sin marcas que limpiar)")
        return

    print(f"\n  TOTAL: {len(total_changes)} reemplazos")

    if dry_run:
        print("  (DRY RUN — no se actualizó WP)")
        return

    print("  Actualizando WP...")
    st, resp = api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}",
                   {"fields": updates})
    if st == 200:
        print(f"  -> OK (HTTP {st})")
    else:
        print(f"  -> ERROR (HTTP {st}): {resp}")


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("*** MODO DRY RUN — solo muestra cambios, no actualiza WP ***\n")

    env = cargar_env()
    post_ids = [23654, 23659, 23664, 23669]

    for pid in post_ids:
        clean_post(env, pid, dry_run=dry_run)

    print(f"\n{'='*60}")
    print("LIMPIEZA COMPLETA" if not dry_run else "DRY RUN COMPLETO")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
