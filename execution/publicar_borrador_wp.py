#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar_borrador_wp.py — Crea un artículo de blog de Mundo Joven como BORRADOR
en WordPress (CPT pt_blog_article) vía REST API, carga sus campos ACF y, si el
contenido trae FAQs, crea el FAQ Single (pt_faqs_singles) y lo enlaza.

Uso:
    py execution/publicar_borrador_wp.py <ruta_al_contenido.json>

El JSON de contenido debe tener esta forma:
{
  "post_title": "Mundo - Titulo corto (define la URL)",
  "slug": "mundo-titulo-corto",
  "faq_single_title": "FAQs ...",           # opcional
  "acf": { ...campos ACF de pt_blog_article... },
  "faqs": [ {"q": "Pregunta", "a": "<p>Respuesta HTML</p>"}, ... ]   # opcional
}

Credenciales en .env (raíz del proyecto): WP_URL, WP_USER, WP_APP_PASSWORD.
Nunca publica: status = draft. Registra la corrida en .tmp/logs/YYYY-MM-DD.jsonl.
"""
import sys, os, json, time, base64, ssl
from datetime import datetime, timezone
from urllib import request, error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar_env():
    env = {}
    ruta = os.path.join(ROOT, ".env")
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            env[k.strip()] = v.strip()
    faltan = [k for k in ("WP_URL", "WP_USER", "WP_APP_PASSWORD") if not env.get(k)]
    if faltan:
        sys.exit("ERROR: faltan en .env: " + ", ".join(faltan))
    return env


def auth_header(user, pw):
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
    return "Basic " + token


def api(env, method, path, payload=None, reintentos=8):
    url = env["WP_URL"].rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    ctx = ssl.create_default_context()
    ultimo = None
    for intento in range(1, reintentos + 1):
        req = request.Request(url, data=data, method=method)
        req.add_header("Authorization", auth_header(env["WP_USER"], env["WP_APP_PASSWORD"]))
        req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with request.urlopen(req, timeout=60, context=ctx) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")
            return e.code, _try_json(cuerpo)
        except (error.URLError, TimeoutError, ssl.SSLError) as e:
            ultimo = e
            print(f"  ...conexión falló (intento {intento}/{reintentos}): {e}. Reintento en 3s")
            time.sleep(3)
    sys.exit(f"ERROR de conexión tras {reintentos} intentos: {ultimo}")


def _try_json(txt):
    try:
        return json.loads(txt)
    except Exception:
        return {"_raw": txt[:400]}


def log(entrada):
    d = os.path.join(ROOT, ".tmp", "logs")
    os.makedirs(d, exist_ok=True)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(os.path.join(d, f"{fecha}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: py execution/publicar_borrador_wp.py <contenido.json>")
    ruta = sys.argv[1]
    t0 = time.time()
    with open(ruta, encoding="utf-8") as f:
        c = json.load(f)

    # Validación: la metadata (Sección 7) es obligatoria y se olvida fácil.
    _acf = c.get("acf", {})
    if not (_acf.get("pt_blog_article-title") and _acf.get("pt_blog_article-description")):
        sys.exit("ERROR: falta la metadata (Sección 7). Agrega 'pt_blog_article-title' y "
                 "'pt_blog_article-description' en acf antes de publicar.")

    env = cargar_env()
    base = env["WP_URL"].rstrip("/")

    # 1) Crear o ACTUALIZAR el artículo (siempre BORRADOR)
    if c.get("post_id"):
        post_id = c["post_id"]
        print(f"1) Actualizando artículo existente {post_id}...")
        st, post = api(env, "POST", f"/wp-json/wp/v2/pt_blog_article/{post_id}",
                       {"title": c["post_title"], "slug": c.get("slug", "")})
        if st != 200:
            sys.exit(f"ERROR al actualizar el post (HTTP {st}): {post}")
    else:
        print("1) Creando artículo (borrador)...")
        st, post = api(env, "POST", "/wp-json/wp/v2/pt_blog_article",
                       {"title": c["post_title"], "slug": c.get("slug", ""), "status": "draft"})
        if st != 201 or "id" not in post:
            log({"script": "publicar_borrador_wp", "status": "error", "paso": "crear", "resp": post})
            sys.exit(f"ERROR al crear el post (HTTP {st}): {post}")
        post_id = post["id"]
    print(f"   -> post ID {post_id} (draft)")

    # 2) Cargar campos ACF (en 2 tandas: contenido y metadata, para no exceder tamaño)
    print("2) Cargando campos ACF...")
    acf = json.loads(json.dumps(c["acf"]))
    # Auto-llenar íconos de S3 si están vacíos (usa _icon_hint o keyword matching)
    items = acf.get("pt_blog_article_item_list", [])
    if items:
        try:
            from asignar_iconos import llenar_iconos
            llenar_iconos(items, forzar=True)
            print("   -> íconos S3 auto-asignados (keyword matching forzado)")
        except ImportError:
            pass
    # Limpiar hints internos que no son campos ACF reales
    for item in acf.get("pt_blog_article_item_list", []):
        item.pop("_icon_hint", None)
    meta = {k: v for k, v in acf.items() if k.startswith("pt_blog_article-")}
    principal = {k: v for k, v in acf.items() if not k.startswith("pt_blog_article-")}
    st, _ = api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}", {"fields": principal})
    if st != 200:
        log({"script": "publicar_borrador_wp", "status": "error", "paso": "acf", "post_id": post_id})
        sys.exit(f"ERROR al cargar ACF principal (HTTP {st})")
    if meta:
        st, _ = api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}", {"fields": meta})
        if st != 200:
            sys.exit(f"ERROR al cargar metadata (HTTP {st})")
    print("   -> campos ACF cargados (contenido + metadata)")

    # 3) FAQs -> crear o actualizar FAQ Single y enlazar
    faq_id = c.get("faq_id")
    if c.get("faqs"):
        items = [{"faqs_singles_faqs_titulo": q["q"], "faqs_singles_faqs_question": q["a"]}
                 for q in c["faqs"]]
        if faq_id:
            print(f"3) Actualizando FAQ Single existente {faq_id}...")
        else:
            print("3) Creando FAQ Single y enlazando...")
            titulo_faq = c.get("faq_single_title", f"FAQs {c['post_title']}")
            st, faq = api(env, "POST", "/wp-json/wp/v2/pt_faqs_singles",
                          {"title": titulo_faq, "status": "publish"})
            if st != 201 or "id" not in faq:
                sys.exit(f"ERROR al crear FAQ Single (HTTP {st}): {faq}")
            faq_id = faq["id"]
        api(env, "POST", f"/wp-json/acf/v3/pt_faqs_singles/{faq_id}",
            {"fields": {"faqs_singles_faqs": items}})
        api(env, "POST", f"/wp-json/acf/v3/pt_blog_article/{post_id}",
            {"fields": {"pt_blog_article_faqs_source": faq_id}})
        print(f"   -> FAQ Single ID {faq_id} enlazado ({len(items)} preguntas)")

    # 4) Guardar post_id y faq_id de vuelta en el JSON fuente
    c["post_id"] = post_id
    c["faq_id"] = faq_id
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)

    edit_url = f"{base}/wp-admin/post.php?post={post_id}&action=edit"
    dur = int((time.time() - t0) * 1000)
    log({"script": "publicar_borrador_wp", "status": "ok", "inputs": os.path.basename(ruta),
         "outputs": {"post_id": post_id, "faq_id": faq_id}, "duration_ms": dur})

    print("\n== LISTO (BORRADOR) ==")
    print(f"post_id: {post_id}   faq_id: {faq_id}")
    print(f"Editar: {edit_url}")


if __name__ == "__main__":
    main()
