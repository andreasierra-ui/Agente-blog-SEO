#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lee un artículo pt_blog_article de WordPress y lo imprime en texto plano
(para analizar estilo/estructura). Uso: py execution/leer_articulo.py <post_id>"""
import sys, os, re, json, base64, ssl, html
from urllib import request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context()


def env():
    e = {}
    for l in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); e[k.strip()] = v.strip()
    return e


def get(e, path):
    import time
    for i in range(10):
        try:
            r = request.Request(e["WP_URL"].rstrip("/") + path)
            r.add_header("Authorization", "Basic " + base64.b64encode(f"{e['WP_USER']}:{e['WP_APP_PASSWORD']}".encode()).decode())
            return json.loads(request.urlopen(r, timeout=60, context=CTX).read().decode())
        except Exception as ex:
            if i == 9:
                raise
            time.sleep(3)


def txt(s):
    if not isinstance(s, str):
        return s
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def main():
    pid = sys.argv[1]
    e = env()
    a = get(e, f"/wp-json/acf/v3/pt_blog_article/{pid}")["acf"]
    P = lambda *x: print(*x)
    P("H1:", txt(a.get("pt_blog_article_title")))
    P("\n[S1 INTRO]\n", txt(a.get("pt_blog_article_richcontent")))
    P("\nBANNER:", txt(a.get("titulo_del_banner")), "|", txt(a.get("subtitulo_del_banner")))
    P("\n[S2 H2]:", txt(a.get("pt_blog_article_title2")))
    P(txt(a.get("pt_blog_article_richcontent2")))
    P("\n[S3 H2]:", txt(a.get("pt_blog_article_title3")))
    for it in (a.get("pt_blog_article_item_list") or []):
        P(" -", txt(it.get("pt_blog_article_title_list")), "::", txt(it.get("pt_blog_article_richcontent_list")))
    P("\n[S4 H2]:", txt(a.get("pt_blog_article_title4")))
    P(txt(a.get("pt_blog_article_richcontent4")))
    P("\n[META]:", txt(a.get("pt_blog_article-title")), "||", txt(a.get("pt_blog_article-description")))
    src = a.get("pt_blog_article_faqs_source")
    if isinstance(src, dict) and src.get("ID"):
        fa = get(e, f"/wp-json/acf/v3/pt_faqs_singles/{src['ID']}")["acf"]
        P("\n[FAQs]")
        for q in (fa.get("faqs_singles_faqs") or []):
            P(" Q:", txt(q.get("faqs_singles_faqs_titulo")))
            P("  A:", txt(q.get("faqs_singles_faqs_question")))


if __name__ == "__main__":
    main()
