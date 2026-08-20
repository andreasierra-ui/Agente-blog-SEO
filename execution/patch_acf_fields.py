"""
Actualiza campos ACF específicos en WP sin tocar el contenido completo del artículo.
Solo parchea los campos pasados como argumento, preservando todo lo demás.
"""
import os, sys, json, requests
from dotenv import load_dotenv

load_dotenv()
WP_URL = os.getenv("WP_URL").rstrip("/")
AUTH = (os.getenv("WP_USER"), os.getenv("WP_APP_PASSWORD"))

def patch(post_id, fields: dict, label=""):
    url = f"{WP_URL}/wp-json/acf/v3/pt_blog_article/{post_id}"
    r = requests.post(url, auth=AUTH, json={"fields": fields})
    r.raise_for_status()
    keys = list(fields.keys())
    print(f"  [OK] post {post_id} ({label}): {keys}")
    return r.json()

if __name__ == "__main__":
    updates = [
        # Art. 249: banner y section2 nuevos (aeropuerto + docs seguro)
        (23743, {
            "imagen_de_banner_desktop": 23780,
            "imaben_de_banner_mobile": 23781,
            "pt_blog_article_section2_image": 23782,
        }, "249 – países que exigen seguro"),

        # Art. 250: section2 + titulo_del_banner diferente al H1
        (23748, {
            "pt_blog_article_section2_image": 23794,
            "titulo_del_banner": "Destinos donde viajar sin seguro puede salirte muy caro",
        }, "250 – países recomendados seguro"),

        # Art. 251: banner nuevo + section2 nuevo + intro fix + H2 distinto al H1
        (23753, {
            "imagen_de_banner_desktop": 23783,
            "imaben_de_banner_mobile": 23784,
            "pt_blog_article_section2_image": 23785,
            "pt_blog_article_title2": "Paso a paso: cómo activar la asistencia según el tipo de emergencia",
        }, "251 – cómo usar tu seguro"),

        # Art. 252: section2 nueva (familia con documentos)
        (23758, {
            "pt_blog_article_section2_image": 23797,
        }, "252 – consejos primera vez"),

        # Art. 253: section2 nueva (comparando seguros)
        (23763, {
            "pt_blog_article_section2_image": 23800,
        }, "253 – cómo elegir seguro"),

        # Art. 255: banner + section2 Punta Cana reales
        (23773, {
            "imagen_de_banner_desktop": 23786,
            "imaben_de_banner_mobile": 23787,
            "pt_blog_article_section2_image": 23788,
        }, "255 – guía Punta Cana"),

        # Art. 256: banner + section2 fraude digital
        (23778, {
            "imagen_de_banner_desktop": 23789,
            "imaben_de_banner_mobile": 23790,
            "pt_blog_article_section2_image": 23791,
        }, "256 – estafas fraudes"),
    ]

    print(f"Parcheando {len(updates)} artículos...")
    for post_id, fields, label in updates:
        try:
            patch(post_id, fields, label)
        except Exception as e:
            print(f"  [ERR] post {post_id}: {e}")

    print("Listo.")
