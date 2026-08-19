#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escanea contenido de artículos WP buscando menciones de marcas/competidores."""
import sys, os, json, re, base64, ssl
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRANDS = [
    # Aerolíneas
    "Volaris", "VivaAerobus", "Viva Aerobus", "Aeroméxico", "Aeromexico",
    # Hospedaje
    "Airbnb", "Booking", "Booking.com", "Expedia", "Trivago",
    "Hotels.com", "Hostelworld",
    # Renta de autos
    "Hertz", "Avis", "Enterprise", "Sixt", "Budget",
    # Financieras
    "American Express", "Amex", "Visa", "Mastercard",
    # Apps
    "Splitwise", "Tricount", "TripAdvisor", "Google Docs", "Notion",
    # Comparadores
    "Rastreator", "Despegar", "Kayak", "Skyscanner",
    # Parques (discutible pero por seguridad)
    "Disney", "Universal", "Sea World", "SeaWorld",
    # Marcas de seguro
    "Allianz", "AXA", "World Nomads", "Safety Wing", "SafetyWing",
    # Otras
    "Uber", "Cabify", "Didi",
]

BRAND_PATTERNS = [(re.compile(r'\b' + re.escape(b) + r'\b', re.IGNORECASE), b) for b in BRANDS]


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
    with request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def scan_text(text, post_id, field):
    hits = []
    for pat, brand in BRAND_PATTERNS:
        for m in pat.finditer(text):
            context_start = max(0, m.start() - 40)
            context_end = min(len(text), m.end() + 40)
            context = text[context_start:context_end].replace('\n', ' ')
            hits.append({
                "brand": brand,
                "context": f"...{context}...",
                "field": field,
                "post_id": post_id,
            })
    return hits


def main():
    env = cargar_env()
    post_ids = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [23654, 23659, 23664, 23669]

    all_hits = []
    for pid in post_ids:
        data = api_get(env, f"/wp-json/acf/v3/pt_blog_article/{pid}")
        acf = data.get("acf", data)

        content_fields = [
            ("richcontent", acf.get("pt_blog_article_richcontent", "")),
            ("richcontent2", acf.get("pt_blog_article_richcontent2", "")),
            ("richcontent4", acf.get("pt_blog_article_richcontent4", "")),
            ("banner_titulo", acf.get("titulo_del_banner", "")),
            ("banner_subtitulo", acf.get("subtitulo_del_banner", "")),
        ]
        items = acf.get("pt_blog_article_item_list", [])
        for i, item in enumerate(items):
            content_fields.append((f"item_{i}_content", item.get("pt_blog_article_richcontent_list", "")))

        faqs = acf.get("pt_blog_article_faqs", [])
        for i, faq in enumerate(faqs):
            content_fields.append((f"faq_{i}_q", faq.get("pt_blog_article_faq_title", "")))
            content_fields.append((f"faq_{i}_a", faq.get("pt_blog_article_faq_content", "")))

        title = acf.get("pt_blog_article_title", f"Post {pid}")
        print(f"\n=== Post {pid}: {title[:50]} ===")

        for field, text in content_fields:
            if not text:
                continue
            hits = scan_text(text, pid, field)
            all_hits.extend(hits)

        post_hits = [h for h in all_hits if h["post_id"] == pid]
        if post_hits:
            for h in post_hits:
                print(f"  [{h['field']}] {h['brand']}: {h['context']}")
        else:
            print("  (sin marcas encontradas)")

    print(f"\n{'='*60}")
    brands_found = set(h["brand"] for h in all_hits)
    print(f"Total: {len(all_hits)} menciones de {len(brands_found)} marcas")
    if brands_found:
        print(f"Marcas: {', '.join(sorted(brands_found))}")


if __name__ == "__main__":
    main()
