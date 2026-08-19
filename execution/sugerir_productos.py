#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sugerir_productos.py — Sugiere 3-4 tours (wp_single_tours) relevantes
para un artículo de blog, basándose en región, keywords y relevancia temática.

Flujo:
  1. --build-cache: descarga TODOS los wp_single_tours + productos ya usados
     en artículos publicados. Genera .tmp/productos_cache_v2.json.
  2. --tema + --destino: puntúa cada producto y devuelve top 3-4 variados.

Uso:
  py execution/sugerir_productos.py --build-cache
  py execution/sugerir_productos.py --tema "transporte público en Europa" --destino europa
  py execution/sugerir_productos.py --tema "licencia conducir internacional" --destino norteamerica,europa

  # Excluir IDs ya usados en artículos recientes del mismo batch:
  py execution/sugerir_productos.py --tema "..." --excluir 19088,17680

Imprime: RESULT [id1, id2, id3, ...]
Requiere en .env: WP_URL, WP_USER, WP_APP_PASSWORD.
"""
import sys, os, json, time, base64, ssl, re
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, ".tmp", "productos_cache_v2.json")
CTX = ssl.create_default_context()


def _env():
    e = {}
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                e[k.strip()] = v.strip()
    return e


def _auth(e):
    cred = e["WP_USER"] + ":" + e["WP_APP_PASSWORD"]
    return "Basic " + base64.b64encode(cred.encode()).decode()


def _fetch(e, path, retries=8):
    url = e["WP_URL"].rstrip("/") + path
    for i in range(retries):
        try:
            req = request.Request(url, headers={
                "Authorization": _auth(e),
                "User-Agent": "MundoJovenAgent/1.0"
            })
            with request.urlopen(req, timeout=90, context=CTX) as r:
                return json.loads(r.read().decode())
        except Exception as ex:
            print("  ...retry %d: %s" % (i + 1, ex))
            time.sleep(3)
    return None


def _fetch_all(e, endpoint, per_page=50):
    items = []
    page = 1
    while True:
        sep = "&" if "?" in endpoint else "?"
        data = _fetch(e, "%s%sper_page=%d&page=%d" % (endpoint, sep, per_page, page))
        if not data:
            break
        items.extend(data)
        if len(data) < per_page:
            break
        page += 1
        time.sleep(0.5)
    return items


# --- Clasificación de regiones ---

MACRO_REGIONS = {
    "europa": ["europa", "paris", "roma", "florencia", "amsterdam",
               "barcelona", "madrid", "londres", "praga", "berlin",
               "grecia", "croacia", "suiza", "portugal", "italia", "francia",
               "espana", "venecia", "viena", "budapest", "rusia",
               "escandinavia", "noruega", "islandia", "irlanda", "escocia"],
    "asia": ["japon", "china", "tailandia", "vietnam", "india",
             "corea", "bali", "singapur", "camboya", "nepal", "asia",
             "indonesia", "sri lanka", "filipinas", "myanmar"],
    "norteamerica": ["estados unidos", "nueva york", "miami", "las vegas",
                     "los angeles", "san francisco", "canada",
                     "vancouver", "toronto", "chicago", "washington"],
    "latinoamerica": ["peru", "colombia", "argentina", "chile",
                      "brasil", "ecuador", "bolivia", "cusco", "machu picchu",
                      "buenos aires", "cartagena", "bogota", "rio de janeiro",
                      "costa rica", "panama", "guatemala", "cuba"],
    "africa": ["sudafrica", "zimbabue", "tanzania", "kenia",
               "marruecos", "egipto", "safari", "africa"],
    "mexico": ["cancun", "los cabos", "monterrey", "oaxaca",
               "valle de guadalupe", "cdmx", "riviera maya", "mexico",
               "baja california", "chiapas", "yucatan"],
    "medio_oriente": ["dubai", "israel", "jordania", "turquia",
                      "estambul", "abu dhabi", "qatar", "oman"],
    "oceania": ["australia", "nueva zelanda", "oceania"],
}

TEMA_KEYWORDS = {
    "seguro": ["seguro", "asistencia", "medic", "emergencia", "poliza", "cobertura"],
    "vuelo": ["vuelo", "avion", "aeropuerto", "boleto", "aerolinea", "escala"],
    "mochila": ["mochilero", "mochila", "backpack", "presupuesto", "barato", "hostal"],
    "documento": ["documento", "pasaporte", "visa", "etias", "migracion", "tramite", "checklist"],
    "transporte": ["transporte", "metro", "bus", "tren", "autobus", "coche", "auto", "rentar", "conducir", "licencia"],
    "temporada": ["temporada baja", "temporada alta", "off-season", "low season"],
    "comida": ["comida", "gastronomia", "restaurante", "platillo", "comer"],
    "cultura": ["cultura", "museo", "historia", "templo", "arte"],
    "aventura": ["aventura", "senderismo", "hiking", "buceo", "snorkel", "surf"],
    "playa": ["playa", "mar", "costa", "tropical", "arena"],
}


def _normalize(text):
    t = text.lower()
    for a, b in [("\xe1", "a"), ("\xe9", "e"), ("\xed", "i"), ("\xf3", "o"),
                 ("\xfa", "u"), ("\xf1", "n")]:
        t = t.replace(a, b)
    return t


def _classify(text):
    t = _normalize(text)
    regions = []
    for macro, keywords in MACRO_REGIONS.items():
        if any(kw in t for kw in keywords):
            regions.append(macro)
    return regions if regions else ["otro"]


def _parse_price(price_str):
    if not price_str:
        return 0
    nums = re.sub(r"[^\d]", "", str(price_str))
    return int(nums) if nums else 0


# --- Build cache ---

def build_cache():
    e = _env()
    print("1) Fetching wp_single_tours...")
    tours = _fetch_all(e, "/wp-json/wp/v2/wp_single_tours?status=publish&_fields=id,title,slug,acf")
    print("   %d tours" % len(tours))

    print("2) Fetching articles for usage stats...")
    articles = _fetch_all(e, "/wp-json/wp/v2/pt_blog_article?status=publish&_fields=id,acf")
    print("   %d articles" % len(articles))

    usage = {}
    for art in articles:
        acf = art.get("acf", {})
        prods = acf.get("pt_blog_article_producto_relacionado", [])
        if not isinstance(prods, list):
            continue
        for p in prods:
            pi = p.get("pt_blog_article_producto_item")
            if isinstance(pi, dict) and "ID" in pi:
                usage[pi["ID"]] = usage.get(pi["ID"], 0) + 1
            elif isinstance(pi, int):
                usage[pi] = usage.get(pi, 0) + 1

    print("3) Building enriched cache...")
    products = []
    tour_ids = set()
    for t in tours:
        acf = t.get("acf", {})
        title = t["title"]["rendered"]
        keywords = acf.get("meta-keywords", "")
        price = _parse_price(acf.get("wp_single_tours_precio_b3", ""))
        desc = acf.get("wp_single_tours_description_b1", "")[:300]
        promos = acf.get("key_rep_field_wp_single_tours_promo_b2", [])
        all_text = "%s %s %s" % (title, keywords, desc)

        products.append({
            "id": t["id"],
            "title": title,
            "slug": t["slug"],
            "regions": _classify(all_text),
            "price_mxn": price,
            "has_promo": bool(promos and len(promos) > 0),
            "keywords": keywords[:300],
            "used_in_articles": usage.get(t["id"], 0),
        })
        tour_ids.add(t["id"])

    for art in articles:
        acf = art.get("acf", {})
        prods = acf.get("pt_blog_article_producto_relacionado", [])
        if not isinstance(prods, list):
            continue
        for p in prods:
            pi = p.get("pt_blog_article_producto_item")
            if isinstance(pi, dict) and "ID" in pi:
                pid = pi["ID"]
                ptitle = pi.get("post_title", "")
                if pid not in tour_ids:
                    products.append({
                        "id": pid,
                        "title": ptitle,
                        "slug": "",
                        "regions": _classify(ptitle),
                        "price_mxn": 0,
                        "has_promo": False,
                        "keywords": "",
                        "used_in_articles": usage.get(pid, 0),
                        "source": "from_articles",
                    })
                    tour_ids.add(pid)

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print("\nCache: %s (%d products)" % (CACHE_PATH, len(products)))
    return products


def load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


# --- Scoring ---

def score_product(product, tema, destinos=None, excluir=None):
    """Score a product against the article's theme and destinations.

    Priority: region match > keyword overlap > promo bonus > popularity (capped).
    """
    if excluir and product["id"] in excluir:
        return -1000

    score = 0
    tema_n = _normalize(tema)
    title_n = _normalize(product["title"])
    kw_n = _normalize(product.get("keywords", ""))
    all_ctx = "%s %s" % (title_n, kw_n)
    prod_regions = [r.lower() for r in product.get("regions", [])]

    # 1) Destination match (strongest signal)
    if destinos:
        for d in destinos:
            d = d.lower().strip()
            if d in prod_regions:
                score += 40
            else:
                for region_key, aliases in MACRO_REGIONS.items():
                    if d == region_key or any(a in d for a in aliases):
                        if region_key in prod_regions:
                            score += 30
                            break

    # 2) Region in tema text
    for region_key, aliases in MACRO_REGIONS.items():
        if any(a in tema_n for a in aliases):
            if region_key in prod_regions:
                score += 20
                break

    # 3) Keyword overlap between tema and product title/keywords
    tema_words = set(re.findall(r'\w{4,}', tema_n))
    ctx_words = set(re.findall(r'\w{4,}', all_ctx))
    stopwords = {"para", "como", "donde", "cuando", "viaje", "viajero", "viajar",
                 "mejor", "mejores", "guia", "todo", "sobre", "necesitas"}
    common = tema_words & ctx_words - stopwords
    score += len(common) * 8

    # 4) Theme keyword match
    for theme_key, theme_words in TEMA_KEYWORDS.items():
        if any(tw in tema_n for tw in theme_words):
            if any(tw in all_ctx for tw in theme_words):
                score += 10
                break

    # 5) Promo bonus
    if product.get("has_promo"):
        score += 5

    # 6) Popularity (capped low so it doesn't dominate)
    score += min(product.get("used_in_articles", 0), 3)

    return score


def suggest(tema, destinos=None, excluir=None, top_n=4):
    products = load_cache()
    if not products:
        print("ERROR: sin cache. Ejecuta --build-cache primero.")
        sys.exit(1)

    # Solo usar pt_travel_compositor (source=from_articles).
    # wp_single_tours IDs no son aceptados por el campo ACF.
    products = [p for p in products if p.get("source") == "from_articles"]

    scored = [(score_product(p, tema, destinos, excluir), p) for p in products]
    scored.sort(key=lambda x: -x[0])

    results = []
    seen_regions = {}

    for s, p in scored:
        if s <= 0:
            continue
        primary_region = p["regions"][0] if p["regions"] else "otro"

        if primary_region in seen_regions and seen_regions[primary_region] >= 2:
            continue

        results.append(p)
        seen_regions[primary_region] = seen_regions.get(primary_region, 0) + 1

        if len(results) >= top_n:
            break

    if len(results) < 3:
        # Fallback: pick popular, diverse tours
        preferred_order = ["europa", "asia", "latinoamerica", "norteamerica",
                           "africa", "medio_oriente", "mexico", "oceania"]
        by_pop = sorted(products, key=lambda p: -p.get("used_in_articles", 0))
        existing_ids = {p["id"] for p in results}
        for macro in preferred_order:
            for p in by_pop:
                if p["id"] not in existing_ids and macro in p.get("regions", []):
                    results.append(p)
                    existing_ids.add(p["id"])
                    break
            if len(results) >= top_n:
                break

    return results


# --- CLI ---

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-cache", action="store_true")
    ap.add_argument("--tema", default=None)
    ap.add_argument("--destino", default=None,
                    help="Regiones separadas por coma: europa,asia,norteamerica...")
    ap.add_argument("--excluir", default=None,
                    help="IDs a excluir, separados por coma")
    ap.add_argument("--top", type=int, default=4)
    a = ap.parse_args()

    if a.build_cache:
        build_cache()

    if a.tema:
        destinos = [d.strip() for d in a.destino.split(",")] if a.destino else None
        excluir = set(int(x) for x in a.excluir.split(",")) if a.excluir else None

        results = suggest(a.tema, destinos, excluir, a.top)
        print('\nSugerencias para: "%s"' % a.tema +
              (" (destino: %s)" % a.destino if a.destino else "") +
              (" (excluir: %s)" % a.excluir if a.excluir else ""))
        print("-" * 60)
        for i, p in enumerate(results, 1):
            promo = " [PROMO]" if p.get("has_promo") else ""
            price = " $%s MXN" % "{:,}".format(p["price_mxn"]) if p["price_mxn"] else ""
            print("  %d. [%d] %s%s%s" % (i, p["id"], p["title"], price, promo))
            print("     Regiones: %s | Usado en: %d arts" % (
                ", ".join(p.get("regions", [])), p.get("used_in_articles", 0)))
        ids = [p["id"] for p in results]
        print("\nRESULT %s" % json.dumps(ids))

    if not a.build_cache and not a.tema:
        print("Uso: --build-cache | --tema 'keyword' [--destino region] [--excluir id1,id2]")
        print("Cache: %s (existe: %s)" % (CACHE_PATH, os.path.exists(CACHE_PATH)))


if __name__ == "__main__":
    main()
