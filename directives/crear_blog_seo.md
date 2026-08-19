# Crear blog SEO (multi-cliente)

> **ESTADO: v1.0 (rutina semanal en producción).** SOP genérico. Se combina con
> un perfil de cliente en `directives/clientes/<cliente>.md`. Piloto: Mundo
> Joven (WordPress). Diseñado para ser barato en tokens y replicable a otros
> clientes/plataformas (ej. Lease For U / HubSpot).

## Objetivo
Generar los artículos de blog pendientes de la semana, optimizados para SEO con datos reales del mercado, en la voz del cliente, y dejarlos como BORRADOR listos para revisión humana antes de publicar.

## Cuándo usarla
Cada semana, cuando el cliente tiene ~4 artículos "Sin iniciar" en su calendario de contenido.

## Entradas requeridas
- **Cliente:** define qué perfil usar (`directives/clientes/<cliente>.md`) → voz (incluye la Guía de Tono de Voz si existe), audiencia, mercado/SERP, mapa de campos de la plantilla, reglas de imágenes.
- **Calendario del cliente:** para Mundo Joven, pestaña **"Calendario 2026"** del Sheet "Dash SEO" (gid `913428203`), exportable como CSV público. Selección dinámica por **Estado = "Sin iniciar"** (nunca fijar números de fila).

## Herramientas / Scripts (Capa 3 — no gastan tokens del LLM)
- **`execution/orquestar_blog.py`** — **script maestro** que orquesta todo el pipeline:
  - `--prep [--fecha]` → lee calendario, revisa caché Ahrefs, crea manifest en `.tmp/batch_actual/`.
  - `--finalize <json>` → imágenes (Pexels) + productos + íconos + publicar a WP en un solo paso.
  - `--status` → muestra progreso del batch actual.
- **`execution/leer_calendario.py [--fecha "M/D/AAAA"]`** — descarga CSV del calendario, devuelve artículos pendientes como JSON.
- **Ahrefs (MCP, herramienta del agente)** — investigación de mercado real (ver Paso 2). `execution/cache_ahrefs.py get/set "<keyword>"` cachea resultados.
- **`execution/preparar_imagenes_wp.py`** — Pexels: busca fotos, recorta y sube a WP.
- **`execution/subir_imagenes_locales.py`** — recorta imágenes locales (Gemini), sube a WP, actualiza ACF. Ver `directives/generar_imagenes.md`.
- **`execution/sugerir_productos.py`** — sugiere 3-4 tours relevantes por tema/región, con exclusión de batch.
- **`execution/asignar_iconos.py`** — auto-asigna íconos FontAwesome del kit del sitio (91 verificados).
- **`execution/construir_catalogo_enlaces.py`** — construye catálogo de 499 URLs enlazables (blogs + tours + seguros + cruceros + etc.) desde WP API. Guardar en `.tmp/catalogo_enlaces.json`.
- **`execution/insertar_enlaces_internos.py <contenido.json>`** — inserta enlaces internos (bold) y frases clave en bold. Usa el catálogo de enlaces. Dry-run por defecto, `--apply` para guardar.
- **`execution/publicar_borrador_wp.py <contenido.json>`** — crea borrador WP, carga ACF, crea FAQ Single. Auto-asigna íconos.
- **`execution/leer_articulo.py <post_id>`** — lee artículo publicado en texto plano.
- **`execution/leer_html.py <ruta.html>`** — extrae texto plano de HTML.

## Pasos (rutina semanal)

### Inicio rápido (orquestador)
```
py execution/orquestar_blog.py --prep              # Lee calendario + revisa caché
py execution/orquestar_blog.py --status             # Ver progreso
# ... investigar + redactar cada artículo ...
py execution/orquestar_blog.py --finalize <json>    # Imágenes + productos + íconos + publicar
```

### Detalle de cada paso
1. **Preparar batch:** `orquestar_blog.py --prep [--fecha]` → lee calendario, revisa caché Ahrefs, genera manifest en `.tmp/batch_actual/`.
2. **Investigación por artículo (Ahrefs, SIEMPRE, no saltar):**
   a. `serp-overview` (país del perfil, ej. `mx`) sobre la keyword del título → quién rankea y People Also Ask.
   b. `keywords-explorer-matching-terms` con `terms=questions` → **preguntas reales con volumen** para FAQs.
   c. `cache_ahrefs.py get` antes para no re-consultar. `cache_ahrefs.py set` después para guardar.
3. **Redactar** el artículo mapeado a la plantilla del cliente, aplicando la Guía de Tono de Voz y las reglas del perfil. Guardar en `outputs/<cliente>/<slug>.json`.
4. **Finalizar:** `orquestar_blog.py --finalize <json>` → en un solo paso:
   - Imágenes: Pexels primero; Gemini Web UI si Pexels no alcanza (ver `directives/generar_imagenes.md`).
   - Productos: `sugerir_productos.py` con exclusión automática de batch.
   - **Enlaces internos**: `insertar_enlaces_internos.py` auto-enlaza a páginas de servicio (tours, seguros, cruceros, etc.) y blogs relacionados. Los enlaces van en **bold**. También pone en bold frases clave relevantes. Usa catálogo de 499 URLs (`.tmp/catalogo_enlaces.json`).
   - Íconos: `asignar_iconos.py` auto-asigna FontAwesome.
   - Publicar borrador en WordPress.
5. **HITL:** avisar a Eduardo con los enlaces de edición. Publicar-publicar solo tras su OK (regla dura #4). Si algo no gustó, ajustar entrada y regenerar (regla dura #5).

## Salidas
- `outputs/<cliente>/<slug>.json` — contenido mapeado por sección (fuente de verdad, reproducible).
- Borrador creado/actualizado en la plataforma del cliente.
- `.tmp/ahrefs_cache/` — investigación cacheada por keyword.

## Casos extremos y errores conocidos
- **Nunca publicar en estado publicado automáticamente** — siempre BORRADOR + revisión.
- Metadata (Sección 7) se olvidaba seguido → el script ahora **falla si falta**.
- Escribir todo el ACF (contenido + metadata) en una sola llamada puede dar **HTTP 500** por tamaño → separar en 2 llamadas (ya lo hace `publicar_borrador_wp.py`).
- **Comillas rectas dentro del JSON de contenido:** si el texto cita una frase entre `" "` (regla de marca), hay que **escaparlas como `\"`** dentro del string JSON o el archivo queda inválido (`json.decoder.JSONDecodeError`). Validar con `py -c "import json; json.load(open(r'archivo.json', encoding='utf-8'))"` antes de publicar.
- Imágenes reutilizadas de la biblioteca de WP pequeña se ven pixeladas → usar Pexels en alta resolución; banner y Sección 2 deben ser **fotos distintas** y semánticas al tema.
- Íconos FontAwesome: se asignan automáticamente al publicar (`execution/asignar_iconos.py`, 91 íconos verificados del kit). El JSON puede incluir `_icon_hint` para sugerir un ícono específico. Eduardo ajusta en WP admin si alguno no le gusta.
- Productos relacionados (S6): recomendación manual por ahora.
- **Nunca automatizar por navegador/capturas de pantalla** para tareas recurrentes — es lento y carísimo en tokens; usar APIs/scripts (WordPress REST, Ahrefs MCP, exportación CSV de Sheets).
- DNS del sitio del cliente puede fallar de forma intermitente → todos los scripts reintentan solos; no es necesario intervenir.
- No pisar ediciones manuales del cliente: si ya se dio OK a un borrador, actualizar campos puntuales (ej. imágenes) sin regenerar el contenido completo.

## Replicar a otro cliente/plataforma
1. Crear `directives/clientes/<nuevo_cliente>.md` con su voz, audiencia, mercado y mapa de campos de su plantilla (equivalente al de Mundo Joven).
2. Adaptar `leer_calendario.py` a la fuente de su calendario (Sheet propio, o el connector que use).
3. Escribir `execution/publicar_borrador_<plataforma>.py` (ej. HubSpot API) siguiendo el mismo patrón: crear/actualizar en borrador, exigir metadata, separar llamadas grandes.
4. Reusar tal cual: `preparar_imagenes_wp.py` (adaptar solo la llamada de subida a la plataforma), `cache_ahrefs.py`, la investigación con Ahrefs (Paso 2 es agnóstico de plataforma).

## Historial de cambios
- 2026-07-17: versión inicial (borrador).
- 2026-07-18: **v1.0** — rutina semanal probada en producción (calendario vía CSV, Ahrefs con caché, imágenes semánticas por Pexels, publicador blindado); sección de réplica a otros clientes.
- 2026-08-06: **v1.1** — Internal linking automático: catálogo de 413 URLs (blogs + 11 CPTs de servicio), módulo `insertar_enlaces_internos.py` con bold en enlaces y frases clave. Integrado como paso 3 del orquestador `--finalize`. URLs de servicio verificadas en frontend (tours, seguros, cruceros, vuelos, hoteles, idiomas, estudios). Vuelo+Hotel excluido (sin páginas individuales).
