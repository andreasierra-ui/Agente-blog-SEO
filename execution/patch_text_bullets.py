"""
Parcha texto específico en richcontent2:
- Art. 254: 5 destinos Costa Rica → bullets
- Art. 255: zonas de playa Punta Cana → bullets
"""
import os, requests
from dotenv import load_dotenv

load_dotenv()
WP_URL = os.getenv("WP_URL").rstrip("/")
AUTH = (os.getenv("WP_USER"), os.getenv("WP_APP_PASSWORD"))


def get_rc2(post_id):
    r = requests.get(f"{WP_URL}/wp-json/acf/v3/pt_blog_article/{post_id}", auth=AUTH)
    return r.json().get("acf", {}).get("pt_blog_article_richcontent2", "")


def patch_rc2(post_id, new_rc2, label):
    resp = requests.post(
        f"{WP_URL}/wp-json/acf/v3/pt_blog_article/{post_id}",
        auth=AUTH,
        json={"fields": {"pt_blog_article_richcontent2": new_rc2}},
    )
    resp.raise_for_status()
    print(f"[OK] {label}")


# ---- ART 254: 5 destinos Costa Rica → bullets ----
rc2_254 = get_rc2(23768)

OLD_254 = (
    '<h3>1. Los 5 destinos principales y qué hace especial a cada uno</h3>\n'
    '<p>San José es la capital y el punto de entrada de la mayoría de los vuelos internacionales. No es un destino de larga estancia, pero tiene el Museo del Oro Precolombino (entrada $11 USD), el Mercado Central para comer ceviche de conchas o casados desde $3 USD, y la arquitectura del Teatro Nacional inaugurado en 1897.</p>\n'
    '<p>Lo más importante de San José es que está a 1-2 horas en auto de los principales destinos del país: es la base logística.</p>\n'
    '<p>Arenal es el destino de aventura más popular de <strong><a href="https://mundojoven.com/tours/tour-a-costa-rica">Costa Rica</a></strong>. El volcán Arenal, con 1,633 metros de altura, estuvo activo hasta 2010 y hoy se puede hacer senderismo en sus faldas con vistas directas al cráter. Las aguas termales naturales de La Fortuna (a 7 km del volcán) van de $20 USD en las de acceso público hasta $60-80 USD en los resorts con piscinas termales construidas.</p>\n'
    '<p>Desde Arenal también se hacen los tours de tirolesa más largos de Centroamérica (hasta 1.6 km por cable, a 200 metros de altura) y el kayak en el lago Arenal (60 km² de espejo de agua con el volcán de fondo).</p>\n'
    '<p>Manuel Antonio es el parque nacional más visitado del país y el punto de encuentro entre selva y playa. El parque tiene 4 playas dentro de sus límites (Playa Espadilla Sur, Playa Manuel Antonio, Playa Biesanz y Playa Escondida) con monos cara blanca, monos araña, perezosos de 2 y 3 dedos y mapaches que literalmente te roban el sándwich si no cuidas la mochila.</p>\n'
    '<p>La entrada al parque cuesta $18-20 USD por persona, con aforo limitado: hay que reservar con anticipación en línea.</p>\n'
    '<p>La Península de Osa y el Parque Nacional Corcovado representan la Costa Rica más prístina: la National Geographic lo llamó «el lugar más intenso del planeta en términos biológicos». El 2.5% de la biodiversidad del mundo en 540 km².</p>\n'
    '<p>Para llegar hay que tomar un vuelo doméstico desde San José a Puerto Jiménez ($60-120 USD) o hacer 7 horas de bus+lancha desde San José. Es un destino para quienes quieren naturaleza real sin concesiones de confort.</p>\n'
    '<p>Tortuguero es el destino caribeño de Costa Rica por excelencia: un sistema de canales sin carreteras (se llega en bote o lancha desde Limón) donde anidan 4 especies de tortugas marinas.</p>\n'
    '<p>Entre julio y octubre es la temporada de desove de la tortuga verde, el espectáculo natural más impresionante de Costa Rica: en una noche puedes ver hasta 100 tortugas salir del mar a desovar en la playa, un proceso que tarda 2-3 horas por tortuga. Las visitas nocturnas son reguladas y guiadas para proteger a los animales.</p>'
)

NEW_254 = (
    '<h3>1. Los 5 destinos principales y qué hace especial a cada uno</h3>\n'
    '<ul>\n'
    '<li><strong>San José:</strong> La capital y punto de entrada para la mayoría de vuelos internacionales. Museo del Oro Precolombino ($11 USD), Mercado Central con comida local desde $3 USD y Teatro Nacional (1897). Su valor real es la posición logística: a 1-2 horas en auto de los principales destinos del país.</li>\n'
    '<li><strong>Arenal:</strong> El destino de aventura más popular de <strong><a href="https://mundojoven.com/tours/tour-a-costa-rica">Costa Rica</a></strong>. Volcán Arenal (1,633 m, activo hasta 2010), aguas termales naturales en La Fortuna ($20-80 USD), tirolesas de hasta 1.6 km y kayak en el lago Arenal.</li>\n'
    '<li><strong>Manuel Antonio:</strong> El parque nacional más visitado: 4 playas con monos cara blanca, monos araña, perezosos y mapaches a metros del agua. Entrada $18-20 USD; hay que reservar en línea por el aforo limitado.</li>\n'
    '<li><strong>Península de Osa / Corcovado:</strong> La Costa Rica más prístina. National Geographic lo llamó «el lugar más intenso del planeta en términos biológicos»: el 2.5% de la biodiversidad mundial en 540 km². Acceso en vuelo doméstico ($60-120 USD) o 7 horas de bus+lancha desde San José.</li>\n'
    '<li><strong>Tortuguero:</strong> El destino caribeño por excelencia: canales sin carreteras donde anidan 4 especies de tortugas marinas. Entre julio y octubre, la temporada de desove de la tortuga verde permite ver hasta 100 tortugas salir del mar en una sola noche.</li>\n'
    '</ul>'
)

if OLD_254 in rc2_254:
    patch_rc2(23768, rc2_254.replace(OLD_254, NEW_254), "Art 254: 5 destinos → bullets")
else:
    print("[WARN] Art 254: bloque no encontrado exacto, verificando manualmente...")
    idx = rc2_254.find("San José es la capital")
    if idx >= 0:
        print(repr(rc2_254[max(0, idx - 5):idx + 60]))
    else:
        print("'San José es la capital' no encontrado en richcontent2")


# ---- ART 255: zonas de playa Punta Cana → bullets ----
rc2_255 = get_rc2(23773)

OLD_255 = (
    '<h3>1. Las playas de Punta Cana: diferencias entre zonas y cuál elegir</h3>\n'
    '<p>«<strong><a href="https://mundojoven.com/tours/tour-a-punta-cana">Punta Cana</a></strong>» en el lenguaje de los viajeros no es solo un punto en el mapa: es toda la franja este de <strong><a href="https://mundojoven.com/seguros/seguro-de-viaje-republica-dominicana">República Dominicana</a></strong>, que incluye varias playas con personalidades distintas. Bávaro es la zona más desarrollada: aquí están la mayoría de los resorts todo incluido de cadenas internacionales, los centros comerciales turísticos y el mayor concentrado de turistas.</p>\n'
    '<p>El agua es increíble (turquesa, cálida, con oleaje mínimo gracias al arrecife de coral que funciona como barrera natural) pero la playa está llena de sombrillas de hotel y vendedores ambulantes.</p>\n'
    '<p>Uvero Alto es la zona más exclusiva y tranquila: menos densidad de hoteles, la misma calidad de playa y precios de resort 20-40% más altos que en Bávaro. Macao es la playa pública más popular de la zona, de acceso libre, con oleaje más fuerte (surf posible) y sin la infraestructura de resort.</p>\n'
    '<p>Cap Cana es el desarrollo más moderno y de lujo: marina privada, campos de golf de Jack Nicklaus y los resorts más caros de la zona con precios de $500-1,000 USD por noche. Para un primer viaje a Punta Cana, Bávaro ofrece la mejor relación calidad-precio: buena playa, opciones en todos los rangos de precio y la mayor variedad de excursiones disponibles.</p>'
)

NEW_255 = (
    '<h3>1. Las playas de Punta Cana: diferencias entre zonas y cuál elegir</h3>\n'
    '<p>«<strong><a href="https://mundojoven.com/tours/tour-a-punta-cana">Punta Cana</a></strong>» en el lenguaje de los viajeros no es solo un punto en el mapa: es toda la franja este de <strong><a href="https://mundojoven.com/seguros/seguro-de-viaje-republica-dominicana">República Dominicana</a></strong>, que incluye varias zonas con personalidades distintas.</p>\n'
    '<ul>\n'
    '<li><strong>Bávaro:</strong> La zona más desarrollada. La mayoría de los resorts todo incluido, centros comerciales turísticos y el mayor concentrado de turistas. Agua turquesa y cálida con oleaje mínimo gracias al arrecife de coral, aunque la playa está llena de sombrillas de hotel y vendedores ambulantes.</li>\n'
    '<li><strong>Uvero Alto:</strong> La zona más exclusiva y tranquila: menos densidad de hoteles, la misma calidad de playa y precios de resort 20-40% más altos que en Bávaro.</li>\n'
    '<li><strong>Macao:</strong> La playa pública más popular de la zona. Acceso libre, oleaje más fuerte (surf posible) y sin la infraestructura de resort.</li>\n'
    '<li><strong>Cap Cana:</strong> El desarrollo más moderno y de lujo: marina privada, campos de golf y los resorts más caros de la zona ($500-1,000 USD por noche).</li>\n'
    '</ul>\n'
    '<p>Para un primer viaje, Bávaro ofrece la mejor relación calidad-precio: buena playa, opciones en todos los rangos de precio y la mayor variedad de excursiones disponibles.</p>'
)

if OLD_255 in rc2_255:
    patch_rc2(23773, rc2_255.replace(OLD_255, NEW_255), "Art 255: zonas de playa → bullets")
else:
    print("[WARN] Art 255: bloque no encontrado exacto, verificando...")
    idx = rc2_255.find("Bávaro es la zona más desarrollada")
    if idx >= 0:
        print(repr(rc2_255[max(0, idx - 10):idx + 80]))
    else:
        print("'Bávaro es la zona' no encontrado")
