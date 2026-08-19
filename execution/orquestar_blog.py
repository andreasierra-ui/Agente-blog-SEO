#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orquestar_blog.py — Script maestro para el pipeline de blog SEO de Mundo Joven.

Dos fases:

  FASE 1 — Preparar el batch semanal:
    py execution/orquestar_blog.py --prep [--fecha "M/D/AAAA"]
    - Lee calendario → artículos pendientes
    - Revisa caché Ahrefs por keyword
    - Genera .tmp/batch_actual/manifest.json con el plan

  FASE 2 — Finalizar un artículo (post-redacción):
    py execution/orquestar_blog.py --finalize outputs/mundo_joven/245-mi-slug.json
    - Busca imágenes en Pexels y sube a WP
    - Sugiere productos relacionados (con exclusión de batch)
    - Inserta enlaces internos (bold) + bolds en frases clave
    - Limpia marcas/competidores del contenido
    - Redistribuye párrafos largos en richcontent2
    - Auto-asigna íconos FontAwesome (keyword matching forzado)
    - Publica borrador en WordPress
    - Actualiza el JSON local con post_id, faq_id, image IDs

  FASE 2b — Finalizar TODOS los pendientes:
    py execution/orquestar_blog.py --finalize-all
    - Busca JSONs sin post_id en outputs/mundo_joven/
    - Corre --finalize en cada uno, uno tras otro
    - Si uno falla, continúa con el siguiente

  ESTADO del batch:
    py execution/orquestar_blog.py --status
    - Muestra progreso del batch actual

Requiere en .env: WP_URL, WP_USER, WP_APP_PASSWORD, PEXELS_API_KEY.
"""
import sys, os, json, time, argparse, subprocess, re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH_DIR = os.path.join(ROOT, ".tmp", "batch_actual")
MANIFEST = os.path.join(BATCH_DIR, "manifest.json")
EXEC = os.path.join(ROOT, "execution")
PY = "py"


def run_script(script, args, capture=True):
    cmd = [PY, os.path.join(EXEC, script)] + args
    print("  > %s %s" % (script, " ".join(args)))
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if capture:
        r = subprocess.run(cmd, capture_output=True, cwd=ROOT, env=env)
        if r.returncode != 0:
            stderr = r.stderr.decode("utf-8", errors="replace")[:300] if r.stderr else ""
            print("  ERROR (exit %d): %s" % (r.returncode, stderr))
            return None
        return r.stdout.decode("utf-8", errors="replace")
    else:
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        if r.returncode != 0:
            print("  ERROR (exit %d)" % r.returncode)
            return None
        return ""


def load_manifest():
    if not os.path.exists(MANIFEST):
        return None
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(m):
    os.makedirs(BATCH_DIR, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


# ─── FASE 1: PREP ────────────────────────────────────────────────

def fase_prep(fecha=None):
    print("=" * 60)
    print("FASE 1: PREPARAR BATCH")
    print("=" * 60)

    # 1) Leer calendario
    print("\n1) Leyendo calendario...")
    args = []
    if fecha:
        args = ["--fecha", fecha]
    out = run_script("leer_calendario.py", args)
    if not out:
        sys.exit("ERROR: no se pudo leer el calendario")

    try:
        pendientes = json.loads(out)
    except json.JSONDecodeError:
        sys.exit("ERROR: calendario no devolvió JSON válido")

    if not pendientes:
        print("   No hay artículos pendientes.")
        return

    print("   %d artículos pendientes:" % len(pendientes))
    for p in pendientes:
        print("     - %s (%s, %s)" % (p["titulo"], p["vertical"], p["fecha"]))

    # 2) Revisar caché Ahrefs por keyword
    print("\n2) Revisando caché Ahrefs...")
    articles = []
    for p in pendientes:
        keyword = _extract_keyword(p["titulo"])
        cache_out = run_script("cache_ahrefs.py", ["get", keyword])
        has_cache = cache_out and cache_out.strip() != "MISS"
        articles.append({
            "titulo_calendario": p["titulo"],
            "vertical": p["vertical"],
            "fecha": p["fecha"],
            "keyword": keyword,
            "ahrefs_cached": has_cache,
            "status": "pendiente",
            "json_path": "",
            "post_id": None,
            "faq_id": None,
            "image_ids": {},
            "product_ids": [],
        })
        cache_label = "CACHED" if has_cache else "NECESITA investigación"
        print("   [%s] %s" % (cache_label, keyword))

    # 3) Guardar manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "fecha_filtro": fecha,
        "articles": articles,
        "products_used": [],
    }
    save_manifest(manifest)
    print("\n3) Manifest guardado: %s" % MANIFEST)

    # 4) Resumen
    needs_research = sum(1 for a in articles if not a["ahrefs_cached"])
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print("  %d artículos en el batch" % len(articles))
    print("  %d necesitan investigación Ahrefs" % needs_research)
    print("  %d ya tienen caché" % (len(articles) - needs_research))
    print("\nSiguiente paso: investigar y redactar cada artículo.")
    print("Después: py execution/orquestar_blog.py --finalize <json_path>")


def _extract_keyword(titulo):
    """Extrae keyword principal del título del calendario.
    Quita prefijos de categoría, frases entre paréntesis, y sufijos informativos.
    Ejemplos:
      "Mundo - Cómo ahorrar para un viaje" → "cómo ahorrar para un viaje"
      "Países que exigen seguro de viaje obligatorio: lista 2026" → "países que exigen seguro de viaje obligatorio"
      "Guía de viaje a Costa Rica: naturaleza y aventura" → "guía de viaje a costa rica"
    """
    t = titulo.strip()
    for prefix in ["Mundo -", "Europa -", "Asia -", "Sudamérica -",
                    "Seguro -", "Seguros -", "Tours -"]:
        if t.lower().startswith(prefix.lower()):
            t = t[len(prefix):].strip()
            break
    t = re.sub(r'\s*\(.*?\)\s*', ' ', t)
    t = re.sub(r'\s*:\s*.{0,40}$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t.lower()


# ─── FASE 2: FINALIZE ────────────────────────────────────────────

def fase_finalize(json_path):
    print("=" * 60)
    print("FASE 2: FINALIZAR ARTÍCULO")
    print("=" * 60)

    # Cargar contenido
    with open(json_path, encoding="utf-8") as f:
        content = json.load(f)

    slug = content.get("slug", "")
    acf = content.get("acf", {})
    already_published = bool(content.get("post_id"))

    print("\nArtículo: %s" % content.get("post_title", ""))
    print("Slug: %s" % slug)
    if already_published:
        print("Post ID: %d (ya publicado, actualizando)" % content["post_id"])

    # Validar metadata
    if not acf.get("pt_blog_article-title") or not acf.get("pt_blog_article-description"):
        sys.exit("ERROR: falta metadata S7 (pt_blog_article-title / pt_blog_article-description)")

    # Paso 1: Imágenes (solo si no tiene)
    has_images = (acf.get("imagen_de_banner_desktop") and
                  acf.get("imaben_de_banner_mobile") and
                  acf.get("pt_blog_article_section2_image"))

    if has_images:
        print("\n1) Imágenes: ya tiene, saltando.")
        image_ids = {
            "desktop_id": acf["imagen_de_banner_desktop"],
            "mobile_id": acf["imaben_de_banner_mobile"],
            "section2_id": acf["pt_blog_article_section2_image"],
        }
    else:
        print("\n1) Buscando imágenes en Pexels...")
        keyword = acf.get("pt_blog_article_title", slug).replace("-", " ")
        banner_q = _image_query(keyword, "banner")
        section2_q = _image_query(keyword, "section2")

        out = run_script("preparar_imagenes_wp.py", [
            "--slug", slug,
            "--banner-query", banner_q,
            "--section2-query", section2_q,
        ])
        image_ids = _parse_result(out)
        if not image_ids:
            print("   ADVERTENCIA: imágenes fallaron. Continúa sin ellas.")
            print("   Puedes correr manualmente: py execution/preparar_imagenes_wp.py ...")
            image_ids = {}
        else:
            print("   Imágenes OK: %s" % json.dumps(image_ids))
            acf["imagen_de_banner_desktop"] = image_ids.get("desktop_id", "")
            acf["imaben_de_banner_mobile"] = image_ids.get("mobile_id", "")
            acf["pt_blog_article_section2_image"] = image_ids.get("section2_id", "")

    # Paso 2: Productos
    current_products = acf.get("pt_blog_article_producto_relacionado", [])
    has_products = bool(current_products and any(
        p.get("pt_blog_article_producto_item") for p in current_products
    ))

    if has_products:
        print("\n2) Productos: ya tiene, saltando.")
        product_ids = [p.get("pt_blog_article_producto_item") for p in current_products
                       if p.get("pt_blog_article_producto_item")]
    else:
        print("\n2) Sugiriendo productos...")
        manifest = load_manifest()
        excluir = ",".join(str(x) for x in manifest.get("products_used", [])) if manifest else ""

        tema = acf.get("pt_blog_article_title", "")
        destino = _guess_destino(tema + " " + slug)

        args = ["--tema", tema]
        if destino:
            args += ["--destino", destino]
        if excluir:
            args += ["--excluir", excluir]

        out = run_script("sugerir_productos.py", args)
        product_ids = _parse_product_result(out)
        if product_ids:
            print("   Productos sugeridos: %s" % product_ids)
            acf["pt_blog_article_producto_relacionado"] = [
                {"pt_blog_article_producto_item": pid} for pid in product_ids
            ]
            if manifest:
                manifest["products_used"].extend(product_ids)
                save_manifest(manifest)
        else:
            print("   ADVERTENCIA: no se sugirieron productos.")

    # Paso 3: Enlaces internos + bolds
    print("\n3) Insertando enlaces internos y bolds...")
    try:
        sys.path.insert(0, EXEC)
        from insertar_enlaces_internos import enlazar_contenido
        keyword = acf.get("pt_blog_article_title", slug).replace("-", " ")
        result = enlazar_contenido(
            acf.get("pt_blog_article_richcontent", ""),
            acf.get("pt_blog_article_richcontent2", ""),
            acf.get("pt_blog_article_richcontent4", ""),
            keyword, slug,
        )
        acf["pt_blog_article_richcontent"] = result["s1"]
        acf["pt_blog_article_richcontent2"] = result["s2"]
        acf["pt_blog_article_richcontent4"] = result["s4"]
        n_links = len(result["links_inserted"])
        n_bolds = result["bolds_added"]
        print("   -> %d enlaces internos, %d bolds añadidos" % (n_links, n_bolds))
        for lnk in result["links_inserted"]:
            print('      [%s] "%s" -> %s' % (lnk["type"], lnk["anchor"], lnk["url"]))
    except Exception as e:
        print("   ADVERTENCIA: enlaces internos fallaron: %s" % e)

    # Paso 4: Limpieza de marcas
    print("\n4) Limpiando marcas/competidores...")
    try:
        from limpiar_marcas import apply_replacements
        total_brand_changes = 0
        for field in ["pt_blog_article_richcontent", "pt_blog_article_richcontent2",
                      "pt_blog_article_richcontent4"]:
            original = acf.get(field, "")
            cleaned, changes = apply_replacements(original)
            if changes:
                acf[field] = cleaned
                total_brand_changes += len(changes)
        items_s3 = acf.get("pt_blog_article_item_list", [])
        for item in items_s3:
            content_s3 = item.get("pt_blog_article_richcontent_list", "")
            cleaned, changes = apply_replacements(content_s3)
            if changes:
                item["pt_blog_article_richcontent_list"] = cleaned
                total_brand_changes += len(changes)
        print("   -> %d reemplazos de marcas" % total_brand_changes)
    except Exception as e:
        print("   ADVERTENCIA: limpieza de marcas falló: %s" % e)

    # Paso 5: Redistribución de párrafos (richcontent2)
    print("\n5) Redistribuyendo párrafos largos en richcontent2...")
    try:
        from redistribuir_parrafos import redistribute
        rc2 = acf.get("pt_blog_article_richcontent2", "")
        if rc2:
            rc2_new, n_splits = redistribute(rc2)
            if n_splits > 0:
                acf["pt_blog_article_richcontent2"] = rc2_new
            print("   -> %d párrafos partidos" % n_splits)
        else:
            print("   -> (sin richcontent2)")
    except Exception as e:
        print("   ADVERTENCIA: redistribución de párrafos falló: %s" % e)

    # Paso 6: Publicar borrador
    print("\n6) Publicando borrador en WordPress...")
    content["acf"] = acf
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    out = run_script("publicar_borrador_wp.py", [json_path], capture=False)

    # Re-leer JSON para capturar post_id y faq_id (publicar_borrador_wp los guarda)
    with open(json_path, encoding="utf-8") as f:
        updated = json.load(f)
    post_id = updated.get("post_id")
    faq_id = updated.get("faq_id")

    # Actualizar manifest
    manifest = load_manifest()
    if manifest:
        for art in manifest.get("articles", []):
            if art.get("keyword", "").lower() in slug.lower().replace("-", " "):
                art["status"] = "publicado"
                art["json_path"] = json_path
                art["post_id"] = post_id
                art["faq_id"] = faq_id
                art["image_ids"] = image_ids
                art["product_ids"] = product_ids if product_ids else []
                break
        save_manifest(manifest)

    print("\n" + "=" * 60)
    print("ARTÍCULO FINALIZADO")
    print("  JSON: %s" % json_path)
    print("  post_id: %s   faq_id: %s" % (post_id, faq_id))
    print("  Imágenes: %s" % ("sí" if image_ids else "pendiente"))
    print("  Productos: %s" % (product_ids if product_ids else "pendiente"))
    print("=" * 60)


def _image_query(keyword, tipo):
    """Genera query de búsqueda en inglés para Pexels."""
    words = keyword.lower().split()
    travel_words = ["travel", "travelers", "young", "backpack"]
    if tipo == "section2":
        travel_words = ["landscape", "destination", "scenic"]
    q = " ".join(words[:4] + travel_words[:2])
    return q


def _guess_destino(text):
    """Intenta adivinar la región destino del texto."""
    t = text.lower()
    regions = {
        "europa": ["europa", "paris", "roma", "londres", "berlin", "españa"],
        "asia": ["asia", "japon", "tailandia", "china", "corea", "bali"],
        "norteamerica": ["estados unidos", "nueva york", "miami", "canada"],
        "latinoamerica": ["peru", "colombia", "argentina", "brasil"],
        "africa": ["africa", "safari", "egipto", "marruecos"],
        "mexico": ["mexico", "cancun", "oaxaca", "cdmx"],
    }
    found = []
    for region, keywords in regions.items():
        if any(kw in t for kw in keywords):
            found.append(region)
    return ",".join(found) if found else ""


def _parse_result(output):
    """Parsea RESULT {...} del stdout de un script."""
    if not output:
        return None
    for line in output.split("\n"):
        if line.strip().startswith("RESULT"):
            try:
                return json.loads(line.strip()[7:])
            except (json.JSONDecodeError, IndexError):
                pass
    return None


def _parse_product_result(output):
    """Parsea RESULT [id1,id2,...] del stdout de sugerir_productos."""
    if not output:
        return []
    for line in output.split("\n"):
        if line.strip().startswith("RESULT"):
            try:
                return json.loads(line.strip()[7:])
            except (json.JSONDecodeError, IndexError):
                pass
    return []


# ─── FINALIZE ALL ────────────────────────────────────────────────

def fase_finalize_all():
    print("=" * 60)
    print("FINALIZAR TODOS LOS ARTÍCULOS PENDIENTES")
    print("=" * 60)

    outputs_dir = os.path.join(ROOT, "outputs", "mundo_joven")
    if not os.path.isdir(outputs_dir):
        sys.exit("ERROR: no existe %s" % outputs_dir)

    import glob
    jsons = sorted(glob.glob(os.path.join(outputs_dir, "[0-9]*-*.json")))

    pending = []
    skipped = []
    for jp in jsons:
        with open(jp, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("post_id"):
            skipped.append(os.path.basename(jp))
            continue
        acf = data.get("acf", {})
        if not (acf.get("pt_blog_article-title") and acf.get("pt_blog_article-description")):
            skipped.append(os.path.basename(jp) + " (sin metadata S7)")
            continue
        pending.append(jp)

    if skipped:
        print("\nSaltados (%d):" % len(skipped))
        for s in skipped:
            print("  - %s" % s)

    if not pending:
        print("\nNo hay artículos pendientes de finalizar.")
        return

    print("\n%d artículos pendientes:" % len(pending))
    for jp in pending:
        print("  - %s" % os.path.basename(jp))

    ok = 0
    errores = []
    for i, jp in enumerate(pending, 1):
        print("\n\n%s [%d/%d] %s %s" % (">" * 20, i, len(pending), os.path.basename(jp), "<" * 20))
        try:
            fase_finalize(jp)
            ok += 1
        except SystemExit as e:
            print("  ERROR: %s" % e)
            errores.append(os.path.basename(jp))
        except Exception as e:
            print("  ERROR: %s" % e)
            errores.append(os.path.basename(jp))

    print("\n\n" + "=" * 60)
    print("FINALIZE-ALL COMPLETO: %d/%d OK" % (ok, len(pending)))
    if errores:
        print("  Con errores: %s" % errores)
    print("=" * 60)


# ─── STATUS ───────────────────────────────────────────────────────

def mostrar_status():
    manifest = load_manifest()
    if not manifest:
        print("No hay batch activo. Corre --prep primero.")
        return

    print("=" * 60)
    print("BATCH: %s" % manifest.get("created", "?"))
    if manifest.get("fecha_filtro"):
        print("Filtro fecha: %s" % manifest["fecha_filtro"])
    print("=" * 60)

    articles = manifest.get("articles", [])
    done = sum(1 for a in articles if a["status"] == "publicado")
    print("\nProgreso: %d/%d artículos\n" % (done, len(articles)))

    for i, a in enumerate(articles, 1):
        status_icon = "OK" if a["status"] == "publicado" else "PEND"
        research = "cached" if a.get("ahrefs_cached") else "necesita"
        print("  %d. [%s] %s" % (i, status_icon, a["titulo_calendario"]))
        print("     keyword: %s | ahrefs: %s" % (a["keyword"], research))
        if a.get("post_id"):
            print("     post_id: %s | faq_id: %s" % (a["post_id"], a.get("faq_id")))
        if a.get("product_ids"):
            print("     productos: %s" % a["product_ids"])

    used = manifest.get("products_used", [])
    if used:
        print("\nProductos ya usados en este batch: %s" % used)


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Orquestador de blog SEO - Mundo Joven")
    ap.add_argument("--prep", action="store_true",
                    help="Fase 1: leer calendario, revisar caché, crear manifest")
    ap.add_argument("--fecha", default=None,
                    help="Filtro de fecha para el calendario (ej. 8/14/2026)")
    ap.add_argument("--finalize", default=None, metavar="JSON",
                    help="Fase 2: finalizar un artículo (imágenes + productos + publicar)")
    ap.add_argument("--finalize-all", action="store_true",
                    help="Fase 2: finalizar TODOS los artículos pendientes de outputs/mundo_joven/")
    ap.add_argument("--status", action="store_true",
                    help="Mostrar progreso del batch actual")

    a = ap.parse_args()

    if a.prep:
        fase_prep(a.fecha)
    elif a.finalize:
        fase_finalize(a.finalize)
    elif a.finalize_all:
        fase_finalize_all()
    elif a.status:
        mostrar_status()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
