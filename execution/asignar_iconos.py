#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asignar_iconos.py — Asigna íconos FontAwesome del kit de Mundo Joven a los ítems
de la Sección 3 (pt_blog_article_item_list), basándose en el título de cada ítem.

Vocabulario: 91 íconos verificados del kit FA del sitio, organizados por tema.
Formato: "fa-sharp fa-light fa-<nombre>" (estándar del sitio).

Uso standalone:
  py execution/asignar_iconos.py "Pasaporte vigente"
  py execution/asignar_iconos.py "Seguro de viaje contratado"

Uso como módulo:
  from asignar_iconos import elegir_icono, llenar_iconos
  icon = elegir_icono("Pasaporte vigente")
  items = llenar_iconos(items_list)  # auto-fill empty icon fields
"""
import sys, re

PREFIX = "fa-sharp fa-light"

# Vocabulario organizado por tema semántico.
# Cada entrada: (palabras_clave, icono_sin_prefijo)
# El orden importa: la primera coincidencia gana.
ICON_MAP = [
    # --- Documentos y trámites ---
    (["pasaporte"], "fa-passport"),
    (["visa", "etias", "permiso de entrada", "migracion", "migratoria"], "fa-file-circle-check"),
    (["documento", "papeles", "papeleo", "tramite", "checklist", "requisito"], "fa-file-check"),
    (["certificado", "constancia", "acta"], "fa-file-certificate"),
    (["licencia", "conducir", "manejar", "conduccion"], "fa-id-card"),
    (["formulario", "registro", "inscripcion"], "fa-ballot-check"),
    (["copia", "fotocopia", "escanear", "digital", "nube", "respaldo"], "fa-mobile-signal"),

    # --- Dinero y pagos ---
    (["presupuesto", "ahorr", "costo", "gasto"], "fa-piggy-bank"),
    (["tarjeta", "credito", "debito", "contactless", "pago"], "fa-credit-card"),
    (["efectivo", "cambio de divisa", "moneda", "cajero"], "fa-money-from-bracket"),
    (["dinero", "precio", "billete"], "fa-money-bill"),
    (["propina"], "fa-money-bills-simple"),
    (["transferencia", "enviar dinero"], "fa-money-bill-transfer"),
    (["cartera", "wallet"], "fa-wallet"),
    (["compra", "recuerdo", "suvenir", "souvenir", "shopping"], "fa-bag-shopping-minus"),

    # --- Seguro y protección ---
    (["seguro de viaje", "seguro medico", "poliza", "cobertura", "asistencia"], "fa-shield-check"),
    (["emergencia", "urgencia", "accidente"], "fa-shield"),
    (["seguridad", "precaucion", "cuidado", "robo", "carterista"], "fa-shield-keyhole"),
    (["vacuna", "vacunacion", "inyeccion"], "fa-syringe"),

    # --- Salud ---
    (["botiquin", "medicamento", "medicina", "farmacia", "pastilla"], "fa-kit-medical"),
    (["medico", "hospital", "doctor", "clinica", "salud"], "fa-briefcase-medical"),
    (["capsulas", "tableta", "pastilla", "ibuprofeno"], "fa-capsules"),
    (["agua", "hidratacion", "botella", "purificador"], "fa-bottle-water"),
    (["diarrea", "estomago", "intestin", "digestion", "intoxicacion"], "fa-prescription-bottle-medical"),
    (["repelente", "mosquit", "insect"], "fa-bug-slash"),
    (["bloqueador", "protector solar", "proteccion solar", "quemadura"], "fa-sun"),
    (["mareo", "nausea", "vertigo"], "fa-face-sleeping"),
    (["dormir", "sueno", "descanso", "jet lag", "jetlag", "siesta"], "fa-face-sleepy"),
    (["virus", "infeccion", "bacteria", "contagio", "enfermedad"], "fa-vial-virus"),
    (["higiene", "jabon", "gel", "antibacterial", "desinfectante"], "fa-pump-soap"),

    # --- Transporte ---
    (["vuelo", "avion", "aerolinea", "boleto aereo", "escala"], "fa-plane-departure"),
    (["aeropuerto", "embarque", "terminal", "check-in"], "fa-plane"),
    (["metro", "transporte", "autobus", "bus", "tren", "tarjeta transporte"], "fa-tickets"),
    (["auto", "coche", "carro", "rentar", "alquiler vehiculo"], "fa-cars"),
    (["boleto", "ticket", "entrada", "pase"], "fa-tickets-airline"),

    # --- Equipaje y ropa ---
    (["maleta", "equipaje", "empacar", "hacer maleta"], "fa-suitcase-rolling"),
    (["mochila", "backpack", "carry-on"], "fa-backpack"),
    (["ropa", "vestir", "outfit", "vestuario", "abrigo"], "fa-clothes-hanger"),
    (["zapato", "bota", "calzado", "caminar"], "fa-boot"),
    (["bufanda", "gorro", "frio", "invierno", "abrigar"], "fa-scarf"),
    (["camisa", "camiseta", "playera", "manga larga"], "fa-shirt-long-sleeve"),
    (["calcetines", "calceta", "media"], "fa-socks"),
    (["lentes", "gafas", "sol"], "fa-sunglasses"),

    # --- Tecnología y comunicación ---
    (["celular", "telefono", "movil", "smartphone", "esim", "sim"], "fa-mobile-button"),
    (["app", "aplicacion", "descarga", "descargar"], "fa-mobile-signal"),
    (["internet", "wifi", "datos", "conexion", "conectividad"], "fa-mobile-signal-out"),
    (["audifonos", "musica", "podcast", "escuchar"], "fa-headphones"),
    (["traductor", "idioma", "traduccion", "comunicar", "lengua"], "fa-language"),
    (["foto", "camara", "fotografia", "capturar"], "fa-camera"),
    (["video", "grabar", "pelicula", "contenido"], "fa-photo-film"),
    (["cargador", "bateria", "power bank", "adaptador", "enchufe"], "fa-battery-bolt"),
    (["laptop", "computadora", "ordenador", "trabajo remoto"], "fa-laptop-binary"),

    # --- Alojamiento ---
    (["hotel", "hostal", "airbnb", "hospedaje", "alojamiento", "reservacion"], "fa-building-flag"),
    (["bano", "ducha", "regadera", "toalla"], "fa-shower"),

    # --- Actividades ---
    (["senderismo", "hiking", "trekking", "montana", "caminata", "excursion"], "fa-person-hiking"),
    (["buceo", "snorkel", "nadar", "mar", "playa"], "fa-mask-snorkel"),
    (["cultura", "templo", "religion", "iglesia", "mezquita"], "fa-vihara"),
    (["juego", "entretenimiento", "diversion"], "fa-gamepad"),
    (["mascara", "mascara venecia", "carnaval", "festival"], "fa-mask"),
    (["naturaleza", "bosque", "parque", "arbol", "verde"], "fa-tree-deciduous"),

    # --- Comida y bebida ---
    (["cafe", "desayuno", "cafeteria"], "fa-mug-hot"),
    (["te", "infusion"], "fa-mug-tea-saucer"),
    (["comida", "restaurante", "gastronomia", "cocina", "platillo"], "fa-jar"),

    # --- Clima ---
    (["calor", "verano", "tropical", "temperatura alta"], "fa-temperature-sun"),
    (["frio", "nieve", "temperatura baja", "helad"], "fa-temperature-snow"),
    (["temporada", "epoca", "calendario", "fecha", "cuando viajar"], "fa-calendar-clock"),
    (["horario", "hora", "zona horaria", "reloj"], "fa-clock-desk"),

    # --- Planificación ---
    (["itinerario", "ruta", "mapa", "ubicacion", "gps", "google maps", "navegacion"], "fa-map-location-dot"),
    (["lista", "verificar", "revisar", "antes de viajar"], "fa-list-check"),
    (["planear", "planificar", "organizar", "agenda", "calendarios"], "fa-calendars"),
    (["libreta", "anotar", "notas", "apuntes", "cuaderno"], "fa-notebook"),
    (["contacto", "embajada", "consulado", "direccion", "telefono emergencia"], "fa-address-book"),

    # --- Actitud / social ---
    (["sonrie", "amable", "actitud", "respeto", "cortesia", "educacion", "etiqueta"], "fa-face-smile"),
    (["saludo", "gente", "local", "interactuar", "convivir"], "fa-hand-wave"),
    (["estafa", "scam", "fraude", "timo", "engano"], "fa-hand-back-fist"),
    (["no hacer", "prohibido", "evitar", "error", "cuidado con"], "fa-comment-xmark"),
    (["alerta", "alarma", "atencion", "aviso", "advertencia"], "fa-alarm-exclamation"),
    (["selfie", "redes sociales", "instagram", "perfil"], "fa-images-user"),
    (["gafas de sol", "cara", "cool", "look"], "fa-face-sunglasses"),

    # --- Miscelánea ---
    (["enchufe", "voltaje", "adaptador electrico"], "fa-plug-circle-check"),
    (["equipaje mano", "carry on", "bulto"], "fa-sack"),
    (["spray", "aerosol", "limpi"], "fa-spray-can-sparkles"),
    (["globo", "mundo", "internacional", "global", "destino"], "fa-globe"),
    (["comparar", "igual", "equivalente", "diferencia"], "fa-equals"),
    (["contraseña", "acceso", "candado", "llave", "seguridad digital"], "fa-lock-keyhole-open"),
    (["medio ambiente", "lluvia", "agua potable", "inundacion"], "fa-water-arrow-down"),
    (["equipaje oscuro", "media noche", "noche"], "fa-circle-half-stroke"),
    (["gafas de sol", "look viajero", "estilo"], "fa-sunglasses"),
]

# Fallback si nada coincide
DEFAULT_ICON = "fa-globe"


def _normalize(text):
    t = text.lower()
    for a, b in [("\xe1", "a"), ("\xe9", "e"), ("\xed", "i"), ("\xf3", "o"),
                 ("\xfa", "u"), ("\xf1", "n")]:
        t = t.replace(a, b)
    return t


def elegir_icono(titulo, contexto=""):
    """Devuelve el ícono FA completo para un título de ítem S3."""
    text = _normalize(titulo + " " + contexto)
    for keywords, icon in ICON_MAP:
        if any(kw in text for kw in keywords):
            return "%s %s" % (PREFIX, icon)
    return "%s %s" % (PREFIX, DEFAULT_ICON)


def llenar_iconos(items, forzar=False):
    """Auto-llena pt_blog_article_icon_list en cada ítem si está vacío.
    Si forzar=True, reemplaza incluso íconos existentes.
    Usa _icon_hint como override si existe y no hay ícono puesto.
    """
    for item in items:
        current = item.get("pt_blog_article_icon_list", "")
        if current and not forzar:
            continue
        hint = item.get("_icon_hint", "")
        if hint and not forzar:
            if not hint.startswith("fa-sharp") and not hint.startswith("fa-classic"):
                item["pt_blog_article_icon_list"] = "%s %s" % (PREFIX, hint)
            else:
                item["pt_blog_article_icon_list"] = hint
        else:
            titulo = item.get("pt_blog_article_title_list", "")
            contenido = item.get("pt_blog_article_richcontent_list", "")
            item["pt_blog_article_icon_list"] = elegir_icono(titulo, contenido)
    return items


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: py execution/asignar_iconos.py \"Título del ítem\"")
        print("     py execution/asignar_iconos.py --file <articulo.json>")
        sys.exit(0)

    if sys.argv[1] == "--file":
        import json
        path = sys.argv[2]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("acf", {}).get("pt_blog_article_item_list", [])
        items = llenar_iconos(items)
        for i, it in enumerate(items):
            print("%d. %s" % (i + 1, it["pt_blog_article_icon_list"]))
            print("   %s" % it.get("pt_blog_article_title_list", ""))
    else:
        titulo = " ".join(sys.argv[1:])
        print(elegir_icono(titulo))
