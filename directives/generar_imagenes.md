# Generar y subir imágenes para artículos de blog

## Objetivo
Obtener 2 imágenes (banner + sección 2) para cada artículo de blog, recortarlas a los tamaños del CPT, subirlas a WordPress y actualizar los campos ACF correspondientes.

## Cuándo usarla
Después de publicar el borrador del artículo (ya tiene `post_id`), cuando los campos de imagen están vacíos.

## Entradas requeridas
- **Artículo JSON:** `outputs/mundo_joven/<num>-<slug>.json` con `post_id`, `slug`, `keyword` y tema del artículo.
- **Fuente de imágenes:** Pexels API (primaria, rápida y gratis) o Gemini Web UI (cuando Pexels no tenga la escena/demografía exacta).

## Herramientas / Scripts
- **claude-in-chrome MCP** — controla Gemini en el Chrome del usuario para generar imágenes IA.
- **`execution/preparar_imagenes_wp.py`** — busca fotos en Pexels, recorta y sube a WP (modo respaldo/stock).
- **`execution/subir_imagenes_locales.py`** — recorta imágenes locales (descargadas de Gemini) y sube a WP. Con `--post-id` también actualiza los campos ACF en WordPress.

## Pasos

### Decisión de fuente
- **Pexels primero** (rápido, ~2 seg, gratis, fotos reales de alta calidad).
- **Gemini solo si** Pexels no tiene la escena/demografía/ángulo que necesitas (ej. viajero latino específico, composición muy puntual).

### Opción A: Pexels API (principal)

1. **Listar candidatos:**
   ```
   py execution/preparar_imagenes_wp.py --slug <slug> \
     --banner-query "<tema banner en inglés>" \
     --section2-query "<tema sección 2 en inglés>" --list-only
   ```

2. **Verificar visualmente** los candidatos (abrir URLs en browser). Aplicar las reglas de personas: jóvenes, target MX, congruencia con el tema.

3. **Subir el elegido:**
   ```
   py execution/preparar_imagenes_wp.py --slug <slug> \
     --banner-query "<query>" --banner-index <N> \
     --section2-query "<query>" --section2-index <N>
   ```
   Devuelve `RESULT {"desktop_id":N, "mobile_id":N, "section2_id":N}`.

4. **Actualizar ACF si el post ya existe:**
   Usar los IDs devueltos para actualizar los campos de imagen en el post (manual o via script).

### Opción B: Gemini Web UI (cuando Pexels no alcanza)

1. **Abrir/reutilizar chat de Gemini:**
   - Usar `claude-in-chrome` para navegar a `gemini.google.com`.
   - Si ya hay un chat abierto de imágenes previas, reutilizarlo (no crear nuevo).

2. **Generar imagen de BANNER:**
   - Escribir prompt siguiendo las **Reglas de prompts** (abajo).
   - Esperar a que Gemini genere la imagen (~10-30 seg).
   - Descargar la imagen (click en ícono de descarga o botón de download).
   - Guardar en `.tmp/imagenes/<num>-banner.png`.

3. **Generar imagen de SECCIÓN 2:**
   - En el MISMO chat, escribir el segundo prompt (tema visual distinto al banner).
   - Descargar y guardar como `.tmp/imagenes/<num>-seccion2.png`.

4. **Procesar y subir:**
   ```
   py execution/subir_imagenes_locales.py --slug <slug> \
     --banner .tmp/imagenes/<num>-banner.png \
     --section2 .tmp/imagenes/<num>-seccion2.png \
     --post-id <post_id>
   ```
   El script hace: crop a 3 tamaños → sube a WP → actualiza campos ACF de imagen.

5. **Actualizar JSON local:** anotar los media IDs en el archivo de `outputs/`.

## Reglas de prompts para Gemini

### Variedad de sujetos (OBLIGATORIO)
Alternar entre artículos para que NO se repita el mismo tipo de protagonista:
- **Grupo de viajeros** (2-4 personas, diverso)
- **Hombre joven viajando solo**
- **Pareja viajera**
- **Mujer joven viajando sola**
- **Paisaje/objeto sin personas** (cuando el tema lo permite)

Llevar un ciclo: si el artículo anterior usó "mujer sola", el siguiente usa "grupo" o "hombre solo", etc. **Nunca 2 artículos consecutivos con el mismo tipo.**

### Estructura del prompt
```
Genera una fotografía realista de [SUJETO] [ACCIÓN relacionada al tema].
Escena: [LUGAR/CONTEXTO concreto].
Estilo: fotografía editorial de viajes, luz natural, colores cálidos.
Formato: horizontal/landscape, alta resolución.
[DETALLE ESPECÍFICO del tema del artículo].
```

### Ejemplos por tipo de artículo
- **Transporte público:** "grupo de 3 amigos jóvenes latinos consultando un mapa del metro en una estación europea moderna"
- **Licencia de conducir:** "pareja joven latina conduciendo un auto compacto por una carretera costera con vista al mar"
- **Temporada baja:** "hombre joven latino con mochila caminando solo por una plaza vacía de una ciudad europea en otoño"
- **Seguro de viaje:** "mujer joven latina revisando documentos en el lobby de un aeropuerto internacional"

### Para Sección 2 (DISTINTA al banner)
- Si el banner tiene personas → sección 2 puede ser paisaje/objeto.
- Si el banner es paisaje → sección 2 tiene personas.
- Siempre un ángulo visual diferente del mismo tema.

## Salidas
- 3 media IDs en WordPress: `desktop_id`, `mobile_id`, `section2_id`.
- Campos ACF actualizados: `imagen_de_banner_desktop`, `imaben_de_banner_mobile`, `pt_blog_article_section2_image`.
- JSON local actualizado con los IDs.

## Tamaños de recorte
| Uso | Ancho | Alto | Fuente |
|-----|-------|------|--------|
| Banner desktop | 1512 | 640 | Imagen banner |
| Banner mobile | 375 | 600 | Imagen banner (misma) |
| Sección 2 | 1512 | 640 | Imagen sección 2 (diferente) |

## Casos extremos y errores conocidos
- **Gemini no genera imagen:** a veces falla por contenido policy. Reformular prompt o usar Pexels como respaldo.
- **Gemini tarda mucho:** esperar hasta 60 seg. Si no responde, refrescar y reintentar.
- **Botón de envío en Gemini:** a veces Return no envía. Hacer click explícito en el botón azul de enviar.
- **Pexels sin resultados buenos:** cambiar query a sinónimos en inglés, ampliar tema. Si nada sirve, usar Gemini.
- **Imagen descargada es WebP:** Pillow la convierte a JPEG automáticamente.
- **Viajeros del target:** deben verse jóvenes (18-35) y latinos/mexicanos. Rechazar personas mayores o de demografía incongruente con el artículo.

## Historial de cambios
- 2026-08-06: v1.0 — directiva inicial. Flujo Gemini via claude-in-chrome + Pexels como respaldo.
