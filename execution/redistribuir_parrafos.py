#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redistribuir_parrafos.py — Parte párrafos largos en 2-3 más cortos.
NO cambia contenido, solo agrega saltos </p><p> en límites de oración.
"""
import sys, os, json, re, base64, ssl
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


def split_paragraph(inner_html, max_chars=350):
    """Split a long paragraph's inner HTML at sentence boundaries.
    Returns list of inner HTML fragments."""
    text_len = len(re.sub(r'<[^>]+>', '', inner_html))
    if text_len <= max_chars:
        return [inner_html]

    # Find sentence boundaries (. followed by space and uppercase, or ? or !)
    # But respect HTML tags — don't split inside them
    # Strategy: find all sentence-end positions, pick the one closest to the middle
    sentence_ends = []
    i = 0
    in_tag = False
    clean_pos = 0  # position in text (without tags)
    while i < len(inner_html):
        ch = inner_html[i]
        if ch == '<':
            in_tag = True
            i += 1
            continue
        if ch == '>':
            in_tag = False
            i += 1
            continue
        if in_tag:
            i += 1
            continue
        clean_pos += 1
        if ch in '.?!' and i + 1 < len(inner_html):
            # Check next non-tag char is space or end
            j = i + 1
            while j < len(inner_html) and inner_html[j] == ' ':
                j += 1
            if j < len(inner_html) and (inner_html[j].isupper() or inner_html[j] == '¿' or inner_html[j] == '<'):
                sentence_ends.append((i + 1, clean_pos))
        i += 1

    if not sentence_ends:
        return [inner_html]

    # Find split point(s)
    target = text_len / 2
    def _find_split(pos):
        """Return (before, after) at html position pos, consuming trailing space."""
        end = pos
        while end < len(inner_html) and inner_html[end] == ' ':
            end += 1
        return end

    if text_len > max_chars * 2:
        target1 = text_len / 3
        target2 = 2 * text_len / 3
        best1 = min(sentence_ends, key=lambda x: abs(x[1] - target1))
        best2 = min(sentence_ends, key=lambda x: abs(x[1] - target2))
        if best1 == best2:
            sp = _find_split(best1[0])
            parts = [inner_html[:best1[0]], inner_html[sp:]]
        else:
            sp1 = _find_split(best1[0])
            sp2 = _find_split(best2[0])
            parts = [inner_html[:best1[0]], inner_html[sp1:best2[0]], inner_html[sp2:]]
    else:
        best = min(sentence_ends, key=lambda x: abs(x[1] - target))
        sp = _find_split(best[0])
        parts = [inner_html[:best[0]], inner_html[sp:]]

    return [p for p in parts if p.strip()]


def redistribute(html, max_chars=350):
    """Process full HTML, splitting long <p> blocks."""
    changes = 0

    def replacer(m):
        nonlocal changes
        inner = m.group(1)
        text_len = len(re.sub(r'<[^>]+>', '', inner))
        if text_len <= max_chars:
            return m.group(0)
        parts = split_paragraph(inner, max_chars)
        if len(parts) <= 1:
            return m.group(0)
        changes += 1
        return ''.join(f'<p>{p}</p>' for p in parts)

    result = re.sub(r'<p>(.*?)</p>', replacer, html, flags=re.DOTALL)
    return result, changes


def main():
    post_id = int(sys.argv[1]) if len(sys.argv) > 1 else 23669
    dry_run = "--dry-run" in sys.argv

    env = cargar_env()
    st, data = api(env, "GET", f"/wp-json/acf/v3/pt_blog_article/{post_id}")
    if st != 200:
        sys.exit(f"ERROR: HTTP {st}")
    acf = data.get("acf", data)

    field = "pt_blog_article_richcontent2"
    original = acf.get(field, "")

    # Show before
    paras_before = re.findall(r'<p>(.*?)</p>', original, re.DOTALL)
    print(f"ANTES: {len(paras_before)} párrafos")
    for i, p in enumerate(paras_before):
        text = re.sub(r'<[^>]+>', '', p)
        lines = len(text) / 80
        flag = " <<<" if lines > 4.5 else ""
        print(f"  P{i+1}: {len(text.split())} words, ~{lines:.1f} lines{flag}")

    # Redistribute
    result, changes = redistribute(original)

    paras_after = re.findall(r'<p>(.*?)</p>', result, re.DOTALL)
    print(f"\nDESPUÉS: {len(paras_after)} párrafos ({changes} partidos)")
    for i, p in enumerate(paras_after):
        text = re.sub(r'<[^>]+>', '', p)
        lines = len(text) / 80
        flag = " <<<" if lines > 4.5 else ""
        print(f"  P{i+1}: {len(text.split())} words, ~{lines:.1f} lines{flag}")

    # Verify no content was lost (replace tags with space then normalize, since </p><p> splits consume spaces)
    orig_text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', original)).strip()
    new_text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', result)).strip()
    if orig_text != new_text:
        print("\n*** ADVERTENCIA: el texto cambió! Abortando. ***")
        # Find diff
        for i, (a, b) in enumerate(zip(orig_text, new_text)):
            if a != b:
                print(f"  Diferencia en posición {i}: '{orig_text[max(0,i-20):i+20]}' vs '{new_text[max(0,i-20):i+20]}'")
                break
        return
    print("\n  Verificación: texto idéntico al original (solo cambiaron los <p>)")

    if dry_run:
        print("\n  (DRY RUN — no se actualizó WP)")
        return

    print("\n  Actualizando WP...")
    st, resp = api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}",
                   {"fields": {field: result}})
    print(f"  -> HTTP {st}")


if __name__ == "__main__":
    main()
