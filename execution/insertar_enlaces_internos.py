#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insertar_enlaces_internos.py — Inserta enlaces internos en el HTML de un artículo
de blog de Mundo Joven, usando el catálogo de URLs (.tmp/catalogo_enlaces.json).

Reglas:
  - Los enlaces se envuelven en <strong> (bold).
  - No enlazar dentro de headings (<h2>, <h3>, etc.).
  - No enlazar si ya existe un <a> con la misma URL.
  - Máx ~5-8 enlaces internos por artículo (configurable).
  - Prioridad: páginas de servicio (tours, seguros) > blogs relacionados.
  - No enlazar al propio artículo.
  - Frases clave importantes también se ponen en <strong> sin enlace.

Uso como módulo:
  from insertar_enlaces_internos import enlazar_contenido
  html_nuevo = enlazar_contenido(html_original, keyword_articulo, slug_propio)

Uso standalone:
  py execution/insertar_enlaces_internos.py <articulo.json> [--dry-run]
  py execution/insertar_enlaces_internos.py <articulo.json> --apply

El modo --apply modifica el JSON en sitio; sin él, muestra qué haría.
"""
import sys, os, json, re, html as htmlmod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, ".tmp", "catalogo_enlaces.json")

MAX_LINKS_SERVICE = 5
MAX_LINKS_BLOG = 3
MAX_LINKS_TOTAL = 8
MAX_BOLD_PHRASES = 6


def _load_catalog():
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize(text):
    t = text.lower().strip()
    for a, b in [("\xe1", "a"), ("\xe9", "e"), ("\xed", "i"), ("\xf3", "o"),
                 ("\xfa", "u"), ("\xf1", "n"), ("\xfc", "u")]:
        t = t.replace(a, b)
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def _extract_destino_from_title(title, slug):
    """Extrae el nombre del destino de un título de servicio."""
    destinos = []
    t = title.strip()
    for prefix in [
        "Tour a ", "Tour ", "Vacaciones en ", "Viaje a ",
        "Seguro de viaje para ", "Seguro de viaje ", "Seguro para ",
        "Crucero por el ", "Crucero por ", "Crucero a ", "Crucero ",
        "Cruceros a ", "Cruceros por ",
        "Vuelo a ", "Vuelos a ", "Vuelos baratos a ",
        "Hotel en ", "Hoteles en ",
        "Vuelo + hotel a ", "Paquete de viaje a ",
    ]:
        if t.lower().startswith(prefix.lower()):
            rest = t[len(prefix):].strip()
            rest = re.sub(r'\s+desde\s+.*$', '', rest, flags=re.I).strip()
            if len(rest) > 2:
                destinos.append(rest)
            break

    s = slug.replace("-", " ")
    for prefix in ["tour a ", "tour ", "vacaciones en ", "seguro de viaje para ",
                    "seguro de viaje ", "crucero por el ", "crucero por ", "crucero ",
                    "cruceros a ", "vuelo a ", "vuelos a ", "vuelos baratos a ",
                    "hotel en ", "vuelo hotel a ", "paquete de viaje a "]:
        if s.startswith(prefix):
            rest = s[len(prefix):].strip()
            rest = re.sub(r'\s+desde\s+.*$', '', rest).strip()
            if len(rest) > 2:
                destinos.append(rest)
            break

    return list(set(destinos))


def _score_relevance(catalog_item, article_keyword, article_text_norm):
    """Puntúa qué tan relevante es un enlace del catálogo para este artículo."""
    score = 0
    title_norm = _normalize(catalog_item["title"])
    kw_norm = _normalize(article_keyword)

    type_bonus = {
        "tours": 15, "seguros": 14, "cruceros": 13, "vuelos": 12,
        "hoteles": 11, "idiomas": 10, "vuelo_hotel": 9,
        "educacion_superior": 8, "high_school": 8, "campamentos": 8,
        "au_pair": 8, "work_study": 8, "blog": 5,
    }
    score += type_bonus.get(catalog_item["type"], 0)

    # Destino mencionado literalmente en el texto del artículo
    destinos = _extract_destino_from_title(catalog_item["title"], catalog_item["slug"])
    for dest in destinos:
        dest_norm = _normalize(dest)
        if len(dest_norm) > 3 and dest_norm in article_text_norm:
            score += 40
        # Multi-word: check each word
        dest_words = dest_norm.split()
        if len(dest_words) >= 2:
            matches = sum(1 for w in dest_words if len(w) > 3 and w in article_text_norm)
            if matches >= 2:
                score += 25
            elif matches >= 1 and len(dest_words) <= 2:
                score += 15

    # Keyword del artículo matches título del enlace
    kw_words = set(kw_norm.split())
    title_words = set(title_norm.split())
    common = kw_words & title_words - {"de", "en", "a", "la", "el", "los", "las", "y", "para", "del", "por", "un", "una", "como", "mas", "que", "con"}
    if len(common) >= 3:
        score += 25
    elif len(common) >= 2:
        score += 15

    # Tema del servicio mencionado en el texto
    topics = {
        "seguro": ["seguro de viaje", "seguro medico", "poliza", "cobertura"],
        "vuelo": ["vuelo", "avion", "aerolinea", "aeropuerto"],
        "hotel": ["hotel", "hospedaje", "alojamiento"],
        "crucero": ["crucero", "barco", "navegacion"],
        "idioma": ["idioma", "estudiar", "ingles", "frances", "curso"],
        "documento": ["pasaporte", "visa", "documento", "tramite", "requisito"],
    }
    for topic, words in topics.items():
        art_match = any(w in article_text_norm for w in words)
        item_match = any(w in title_norm for w in words)
        if art_match and item_match:
            score += 10

    # Blog topic overlap: compare slug keywords
    if catalog_item["type"] == "blog":
        item_kws = [_normalize(k) for k in catalog_item.get("keywords", [])]
        for item_kw in item_kws:
            if len(item_kw) > 6 and item_kw in article_text_norm:
                score += 15

    return score


def _find_in_text_noaccent(needle, text, text_norm=None):
    """Busca needle en text, ignorando acentos, con word boundaries."""
    if len(needle) < 3:
        return None
    pat = r'\b' + _build_accent_pattern(needle) + r'\b'
    m = re.search(pat, text, re.IGNORECASE)
    if m:
        return m.group()
    # Fallback without trailing boundary (for cases like "París:")
    pat2 = r'\b' + _build_accent_pattern(needle)
    m = re.search(pat2, text, re.IGNORECASE)
    if m:
        found = m.group()
        if len(found) == len(needle) or len(found) <= len(needle) + 1:
            return found
    return None


def _find_anchor_text(catalog_item, article_html):
    """Busca la mejor frase en el artículo para anclar el enlace."""
    text = re.sub(r'<[^>]+>', ' ', article_html)
    text = htmlmod.unescape(text)
    text_lower = text.lower()
    text_norm = _normalize(text)

    candidates = []

    # 1) Nombre de destino extraído del título
    destinos = _extract_destino_from_title(catalog_item["title"], catalog_item["slug"])
    for dest in destinos:
        found = _find_in_text_noaccent(dest, text, text_norm)
        if found:
            candidates.append((found, 90))

    # 2) Título limpio (sin prefijo de tipo)
    title_clean = re.sub(
        r'^(Tour\s+(a\s+)?|Vacaciones\s+en\s+|Seguro\s+de\s+viaje\s+(para\s+)?|'
        r'Crucero\s+(por\s+(el\s+)?|a\s+)?|Cruceros\s+(a\s+|por\s+)?|'
        r'Vuelo\s+(a\s+)?|Vuelos?\s+(baratos?\s+a\s+)?|Hotel(es)?\s+en\s+|'
        r'Vuelo\s*\+\s*hotel\s+a\s+|Paquete\s+de\s+viaje\s+a\s+)',
        '', catalog_item["title"], flags=re.I
    ).strip()
    title_clean = re.sub(r'\s+desde\s+.*$', '', title_clean, flags=re.I).strip()
    if len(title_clean) > 3:
        found = _find_in_text_noaccent(title_clean, text, text_norm)
        if found:
            candidates.append((found, 85))

    # 3) Para blogs, buscar keywords
    if catalog_item["type"] == "blog":
        for kw in catalog_item.get("keywords", []):
            if len(kw) < 5:
                continue
            found = _find_in_text_noaccent(kw, text, text_norm)
            if found:
                candidates.append((found, 50))

    # 4) Slug como última opción
    slug_text = catalog_item["slug"].replace("-", " ")
    for prefix in ["tour a ", "tour ", "seguro de viaje para ", "seguro de viaje ",
                    "seguro ", "crucero por el ", "crucero por ", "crucero ",
                    "cruceros a ", "vuelo a ", "vuelos a ", "hotel en ",
                    "vacaciones en ", "mundo ", "asia ", "europa ", "sudamerica "]:
        if slug_text.startswith(prefix):
            rest = slug_text[len(prefix):]
            rest = re.sub(r'\s+desde\s+.*$', '', rest).strip()
            if len(rest) > 3:
                found = _find_in_text_noaccent(rest, text, text_norm)
                if found:
                    candidates.append((found, 70))
            break

    if not candidates:
        return None

    candidates.sort(key=lambda x: -x[1])
    return candidates[0][0]


def _is_inside_tag(html_text, pos, tag_names):
    """Verifica si la posición está dentro de ciertos tags HTML."""
    before = html_text[:pos]
    for tag in tag_names:
        open_count = len(re.findall(r'<%s[\s>]' % tag, before, re.I))
        close_count = len(re.findall(r'</%s>' % tag, before, re.I))
        if open_count > close_count:
            return True
    return False


def _build_accent_pattern(text):
    """Construye un regex que matchea text con o sin acentos."""
    accent_map = {
        'a': '[aáà]', 'e': '[eéè]', 'i': '[iíì]', 'o': '[oóò]',
        'u': '[uúùü]', 'n': '[nñ]',
    }
    parts = []
    for ch in text:
        low = ch.lower()
        if low in accent_map:
            parts.append(accent_map[low])
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


def _insert_link(html_text, anchor_text, url, bold=True):
    """Inserta un enlace (con bold) reemplazando la primera aparición del anchor text."""
    pat_core = _build_accent_pattern(anchor_text)
    pattern = re.compile(r'\b' + pat_core + r'\b', re.IGNORECASE)

    for m in pattern.finditer(html_text):
        pos = m.start()
        original = m.group()

        if _is_inside_tag(html_text, pos, ["h1", "h2", "h3", "h4", "a"]):
            continue

        if _is_inside_tag(html_text, pos, ["strong"]):
            strong_pat = re.compile(
                r'<strong>([^<]*?\b' + pat_core + r'\b[^<]*?)</strong>', re.IGNORECASE
            )
            sm = strong_pat.search(html_text)
            if sm:
                inner = sm.group(1)
                inner_m = re.search(r'\b' + pat_core + r'\b', inner, re.IGNORECASE)
                if inner_m:
                    anchor_orig = inner_m.group()
                    new_inner = inner[:inner_m.start()] + '<a href="%s">%s</a>' % (url, anchor_orig) + inner[inner_m.end():]
                    replacement = '<strong>' + new_inner + '</strong>'
                    return html_text[:sm.start()] + replacement + html_text[sm.end():]
            continue

        if bold:
            replacement = '<strong><a href="%s">%s</a></strong>' % (url, original)
        else:
            replacement = '<a href="%s">%s</a>' % (url, original)
        return html_text[:pos] + replacement + html_text[pos + len(original):]
    return None


def _insert_bold(html_text, phrase):
    """Pone en bold la primera aparición de una frase clave."""
    pat = _build_accent_pattern(phrase)
    pattern = re.compile(pat, re.IGNORECASE)
    for m in pattern.finditer(html_text):
        pos = m.start()
        if _is_inside_tag(html_text, pos, ["h1", "h2", "h3", "h4", "a", "strong", "b"]):
            continue
        original = m.group()
        return html_text[:pos] + '<strong>' + original + '</strong>' + html_text[pos + len(original):]
    return None


def _get_bold_phrases(keyword):
    """Genera frases clave que deben ir en bold (sin enlace)."""
    phrases = set()
    kw = keyword.strip()
    if kw:
        phrases.add(kw)
    # Variaciones
    words = kw.lower().split()
    if len(words) >= 3:
        phrases.add(" ".join(words[:3]))
    common_bold = [
        "Mundo Joven", "seguro de viaje", "pasaporte vigente",
        "visa", "presupuesto", "temporada alta", "temporada baja",
        "tipo de cambio", "equipaje de mano", "check-in online",
    ]
    for p in common_bold:
        phrases.add(p)
    return phrases


def enlazar_contenido(html_s1, html_s2, html_s4, keyword, slug_propio,
                      max_service=MAX_LINKS_SERVICE, max_blog=MAX_LINKS_BLOG,
                      max_total=MAX_LINKS_TOTAL, catalog=None):
    """
    Inserta enlaces internos + bold en las secciones HTML de un artículo.

    Args:
        html_s1: HTML de Sección 1 (intro)
        html_s2: HTML de Sección 2 (cuerpo)
        html_s4: HTML de Sección 4 (conclusión)
        keyword: keyword principal del artículo
        slug_propio: slug del artículo (para no autoenlazarse)
        catalog: catálogo de enlaces (si None, se carga del archivo)

    Returns:
        dict con s1, s2, s4 modificados, y report de enlaces insertados.
    """
    if catalog is None:
        catalog = _load_catalog()

    # Excluir el propio artículo
    catalog = [c for c in catalog if c["slug"] != slug_propio]

    # Texto completo para scoring
    all_text = " ".join([html_s1 or "", html_s2 or "", html_s4 or ""])
    all_text_norm = _normalize(re.sub(r'<[^>]+>', ' ', all_text))

    # Puntuar cada enlace del catálogo
    scored = []
    for item in catalog:
        score = _score_relevance(item, keyword, all_text_norm)
        if score > 10:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])

    # Seleccionar los mejores: uno por destino, límites por tipo
    selected_service = []
    selected_blog = []
    urls_used = set()
    destinos_used = set()

    for score, item in scored:
        if len(selected_service) + len(selected_blog) >= max_total:
            break
        if item["url"] in urls_used:
            continue

        # Dedup: max one service link per destination
        item_destinos = _extract_destino_from_title(item["title"], item["slug"])
        item_dest_norms = {_normalize(d) for d in item_destinos if len(d) > 2}
        if item["type"] != "blog" and item_dest_norms & destinos_used:
            continue

        if item["type"] == "blog":
            if len(selected_blog) < max_blog:
                selected_blog.append(item)
                urls_used.add(item["url"])
        else:
            if len(selected_service) < max_service:
                selected_service.append(item)
                urls_used.add(item["url"])
                destinos_used.update(item_dest_norms)

    # Insertar enlaces — try from the full ranked list, stop at target counts
    sections = {"s2": html_s2 or "", "s1": html_s1 or "", "s4": html_s4 or ""}
    report = []
    inserted_service = 0
    inserted_blog = 0
    anchors_used = set()

    candidates = selected_service + selected_blog
    # Add overflow candidates (more items from scored list that weren't selected)
    overflow_service = []
    overflow_blog = []
    for score, item in scored:
        if item["url"] in urls_used:
            continue
        item_dest_norms = {_normalize(d) for d in _extract_destino_from_title(item["title"], item["slug"]) if len(d) > 2}
        if item["type"] != "blog" and item_dest_norms & destinos_used:
            continue
        if item["type"] == "blog":
            if len(overflow_blog) < max_blog * 2:
                overflow_blog.append(item)
        else:
            if len(overflow_service) < max_service * 2:
                overflow_service.append(item)
    candidates.extend(overflow_service + overflow_blog)

    for item in candidates:
        if inserted_service + inserted_blog >= max_total:
            break
        if item["type"] == "blog" and inserted_blog >= max_blog:
            continue
        if item["type"] != "blog" and inserted_service >= max_service:
            continue

        inserted = False
        for sec_key in ["s2", "s1", "s4"]:
            anchor = _find_anchor_text(item, sections[sec_key])
            if anchor and len(anchor) >= 3 and anchor.lower() not in anchors_used:
                result = _insert_link(sections[sec_key], anchor, item["url"], bold=True)
                if result is not None:
                    sections[sec_key] = result
                    report.append({
                        "url": item["url"],
                        "anchor": anchor,
                        "section": sec_key,
                        "type": item["type"],
                        "title": item["title"],
                    })
                    anchors_used.add(anchor.lower())
                    if item["type"] == "blog":
                        inserted_blog += 1
                    else:
                        inserted_service += 1
                        dest_norms = {_normalize(d) for d in _extract_destino_from_title(item["title"], item["slug"]) if len(d) > 2}
                        destinos_used.update(dest_norms)
                    inserted = True
                    break
        if not inserted:
            report.append({
                "url": item["url"],
                "anchor": "(no match en texto o ya usado)",
                "section": None,
                "type": item["type"],
                "title": item["title"],
                "skipped": True,
            })

    # Insertar bolds en frases clave (sin enlace)
    bold_phrases = _get_bold_phrases(keyword)
    bold_count = 0
    for phrase in sorted(bold_phrases, key=len, reverse=True):
        if bold_count >= MAX_BOLD_PHRASES:
            break
        if len(phrase) < 4:
            continue
        for sec_key in ["s2", "s1", "s4"]:
            result = _insert_bold(sections[sec_key], phrase)
            if result is not None:
                sections[sec_key] = result
                bold_count += 1
                break

    return {
        "s1": sections["s1"],
        "s2": sections["s2"],
        "s4": sections["s4"],
        "links_inserted": [r for r in report if not r.get("skipped")],
        "links_skipped": [r for r in report if r.get("skipped")],
        "bolds_added": bold_count,
    }


def process_article_json(json_path, dry_run=True):
    """Procesa un artículo JSON, inserta enlaces y (opcionalmente) guarda."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    acf = data.get("acf", {})
    slug = data.get("slug", "")
    keyword = acf.get("pt_blog_article_title", slug).replace("-", " ")

    html_s1 = acf.get("pt_blog_article_richcontent", "")
    html_s2 = acf.get("pt_blog_article_richcontent2", "")
    html_s4 = acf.get("pt_blog_article_richcontent4", "")

    result = enlazar_contenido(html_s1, html_s2, html_s4, keyword, slug)

    print("\n=== REPORTE DE ENLACES INTERNOS ===")
    print("Artículo: %s" % data.get("post_title", slug))
    print("Keyword: %s" % keyword)
    print("\nEnlaces insertados (%d):" % len(result["links_inserted"]))
    for r in result["links_inserted"]:
        print('  [%s] %s → "%s" en %s' % (r["type"], r["url"], r["anchor"], r["section"]))
    if result["links_skipped"]:
        print("\nEnlaces candidatos sin match en texto (%d):" % len(result["links_skipped"]))
        for r in result["links_skipped"]:
            print("  [%s] %s" % (r["type"], r["title"]))
    print("\nBolds adicionales: %d" % result["bolds_added"])

    if not dry_run:
        acf["pt_blog_article_richcontent"] = result["s1"]
        acf["pt_blog_article_richcontent2"] = result["s2"]
        acf["pt_blog_article_richcontent4"] = result["s4"]
        data["acf"] = acf
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\nJSON actualizado: %s" % json_path)
    else:
        print("\n(dry-run: no se modificó el archivo. Usa --apply para guardar)")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  py execution/insertar_enlaces_internos.py <articulo.json>           # dry-run")
        print("  py execution/insertar_enlaces_internos.py <articulo.json> --apply    # guardar")
        sys.exit(0)

    json_path = sys.argv[1]
    dry_run = "--apply" not in sys.argv
    process_article_json(json_path, dry_run=dry_run)
