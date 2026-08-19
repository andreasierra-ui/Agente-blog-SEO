# Instrucciones para el Agente

Este archivo se replica en `CLAUDE.md`, `AGENTS.md` y `GEMINI.md` para que las mismas instrucciones carguen en cualquier entorno de IA.

---

## Reglas duras (no negociables)

1. **Antes de actuar, busca una directiva.** Si la tarea corresponde a un flujo repetible, debe existir un archivo en `directives/`. Si no existe, pregunta al usuario antes de crearla — no improvises un SOP.
2. **No sobreescribas ni borres directivas existentes sin confirmación explícita.** Las directivas son documentos vivos, pero son del usuario, no tuyas.
3. **Antes de escribir un script nuevo, revisa `execution/`.** Solo crea scripts si no existe uno que sirva.
4. **Si una acción consume tokens/créditos de pago, cuota de API con costo, o modifica datos externos** (envía correos, publica, borra), **pregunta antes de ejecutar.** Reintentos automáticos solo para operaciones gratuitas y reversibles.
5. **Nunca edites a mano los outputs finales.** Cualquier salida debe ser reproducible corriendo el flujo de nuevo.

---

## Aprendizajes del Agente (memoria persistente)

**Instrucción crítica:** Esta sección es tu memoria entre sesiones. Con cada ciclo (tarea completada, error resuelto, patrón descubierto, decisión tomada con el usuario) y con cada actualización de cualquier Markdown del repo, agrega aquí un aprendizaje si surgió algo no trivial.

**Qué registrar:** restricciones reales de APIs, rate limits verificados, patrones que funcionan, errores recurrentes, decisiones acordadas con el usuario, supuestos que resultaron falsos, gotchas del entorno.

**Qué NO registrar:** detalles de una sola tarea, información ya en la directiva correspondiente, cosas triviales derivables del código.

**Formato:**

```
- **YYYY-MM-DD — [Tema corto]:** Descripción en 1–3 líneas. **Por qué importa:** consecuencia práctica.
```

**Higiene:** más recientes arriba. Si un aprendizaje queda obsoleto, actualízalo o bórralo — no acumules ruido. Si superas ~25 entradas, consolida las más antiguas o promuévelas a la directiva correspondiente.

### Registro

- **2026-08-12 — [Gemini imágenes: extracción automatizada]:** Las imágenes generadas en Gemini Web UI se sirven como blob URLs. Para extraerlas: 1) buscar `img.image.loaded` en el DOM, 2) dibujar en canvas, 3) `canvas.toDataURL('image/jpeg', 0.95)`, 4) crear `<a download>` para bajar con nombre predecible. El archivo llega a Downloads (~300KB JPEG, 1024px). `preparar_imagenes_wp.py` ahora acepta `--banner-local` y `--section2-local` para subir imágenes locales (de Gemini u otra fuente) en vez de Pexels. **Por qué importa:** Gemini es el Plan B cuando Pexels no tiene imágenes buenas; el flujo completo (prompt → generación → descarga → crop → upload WP) está verificado.
- **2026-08-12 — [Orquestador v2: marcas + párrafos + íconos forzados]:** `orquestar_blog.py --finalize` ahora tiene 6 pasos: 1) imágenes, 2) productos, 3) enlaces internos, 4) limpieza de marcas, 5) redistribución de párrafos, 6) publicar borrador. `publicar_borrador_wp.py` usa `forzar=True` en `llenar_iconos()` por defecto. Eduardo aprobó subir borradores a WP sin pedir confirmación (son drafts que él revisa). **Por qué importa:** el pipeline completo ya no requiere pasos manuales post-redacción; un solo `--finalize` produce un borrador limpio y listo para revisión.
- **2026-08-12 — [Redistribución de párrafos sin perder contenido]:** `redistribuir_parrafos.py` parte párrafos largos (>350 chars) en 2-3 más cortos en límites de oración. Verifica que el texto plano (normalizado) sea idéntico antes y después. Al partir, el espacio entre `?`/`.` y la siguiente oración se consume (queda como separación `</p><p>`), lo cual es correcto para rendering. **Por qué importa:** Eduardo quiere bloques de texto más cortos pero SIN reducir contenido.
- **2026-08-12 — [Limpieza de marcas automatizada]:** `scan_marcas.py` escanea 30+ marcas en richcontent/items/FAQs. `limpiar_marcas.py` aplica reemplazos regex con genéricos (Airbnb→departamento vacacional, etc.). Cuidado: `en Google Docs` debe reemplazarse como unidad (no solo `Google Docs`) para evitar redundancia. `visa` como documento y `universal` como adjetivo son falsos positivos aceptados. **Por qué importa:** Eduardo fue enfático: NUNCA usar nombres de competidores, aerolíneas, hoteles, ni aseguradoras.
- **2026-08-12 — [Productos: campo ACF solo acepta pt_travel_compositor]:** El campo `pt_blog_article_producto_item` es Post Object que solo resuelve IDs de `pt_travel_compositor`, NO `wp_single_tours`. Los 133 `wp_single_tours` del cache se guardaban como `False`. Fix: filtrar cache a solo `source=from_articles` (97 productos válidos). `reparar_iconos_productos.py` creado para parchear posts existentes. **Por qué importa:** sin este filtro, TODOS los productos sugeridos fallan silenciosamente.
- **2026-08-12 — [Íconos: _icon_hint usaba nombres no verificados]:** Los `_icon_hint` en los JSONs contenían nombres FA genéricos (ej. `fa-bed`, `fa-money-bill-wave`) que no existen en el kit de Mundo Joven. La función `llenar_iconos()` priorizaba hints sobre keyword matching. Fix: usar `forzar=True` para ignorar hints y re-asignar con ICON_MAP verificado. **Nota:** `fa-piggy-bank` SÍ funciona (verificado en artículo 23251). **Por qué importa:** los íconos se guardaban pero no renderizaban en el frontend.
- **2026-08-06 — [Orquestador de blog creado]:** `orquestar_blog.py` con dos fases: `--prep` (calendario + caché Ahrefs → manifest) y `--finalize` (imágenes + productos + íconos + publicar WP). Manifest en `.tmp/batch_actual/` trackea progreso y productos usados para no repetir. Encoding Windows resuelto con `PYTHONIOENCODING=utf-8` en subprocess. **Por qué importa:** evita olvidar pasos y reduce el flujo a 3 comandos: prep → redactar → finalize.
- **2026-08-06 — [Íconos FA automatizados via API]:** El campo `pt_blog_article_icon_list` SÍ se puede escribir via ACF REST API. Formato: `fa-sharp fa-light fa-<nombre>`. 91 íconos verificados del kit del sitio. `asignar_iconos.py` elige por keyword matching (~50-75% de coincidencia con selección manual de Eduardo). Integrado en `publicar_borrador_wp.py`. **Por qué importa:** los artículos ya no se publican sin íconos; Eduardo solo ajusta los que no le gusten en vez de elegir todos.
- **2026-08-06 — [Gemini API no sirve para imágenes]:** La cuenta Google Workspace Pro (Andrea Sierra) NO permite generar imágenes via Gemini API / Google AI Studio — requiere plan de pago adicional. Ruta aprobada: seguir usando Gemini Web UI via claude-in-chrome MCP (gratis). Pexels como respaldo. **Por qué importa:** no proponer migración a Gemini API para imágenes; la restricción es del plan, no técnica.
- **2026-08-06 — [Botón de envío Gemini]:** Al automatizar Gemini Web UI con claude-in-chrome, presionar Return no siempre envía el prompt. Hay que hacer click explícito en el botón azul de enviar. **Por qué importa:** evita que el prompt se quede sin enviar y se pierda tiempo esperando.
- **2026-08-06 — [Producto suggestion system v2]:** Se reconstruyó `sugerir_productos.py` con cache de 230 productos (133 wp_single_tours + 97 de artículos pt_travel_compositor). Solo los 97 pt_travel_compositor son válidos para el campo ACF. Scoring por relevancia temática + diversidad regional. Máx 2 productos por región. Flag `--excluir` para batches. **Por qué importa:** resuelve la repetición de los mismos 4 tours en todos los artículos.

- **2026-08-06 — [Internal linking automatizado]:** `construir_catalogo_enlaces.py` descarga 413 URLs enlazables de WP (71 blogs + 342 servicios: tours, seguros, cruceros, vuelos, hoteles, idiomas, estudios). URLs de frontend verificadas — Vuelo+Hotel excluido (sin páginas individuales); estudios usan `/estudios/{subtipo}/{slug}`. `insertar_enlaces_internos.py` inserta enlaces en el HTML con scoring por destino/tema, word boundaries, accent-insensitive matching, y respeta tags `<strong>` existentes. Límite: 5 servicios + 3 blogs, un enlace por destino. Integrado como paso 3 del `orquestar_blog.py --finalize`. Frases clave también en bold. **Por qué importa:** resuelve la falta total de internal linking entre artículos y hacia páginas de servicio — mejora SEO y distribución de link juice.

<!-- Agrega nuevas entradas arriba de esta línea. -->

---

## Arquitectura de 3 capas

Los LLMs son probabilísticos; la lógica de negocio es determinista. Esta arquitectura resuelve esa incompatibilidad separando responsabilidades.

**Capa 1 — Directiva (qué hacer).** SOPs en Markdown en `directives/`. Definen objetivo, entradas, herramientas, salidas y casos extremos. Lenguaje natural, como para un empleado de nivel medio.

**Capa 2 — Orquestación (tomar decisiones).** Tu rol. Lees directivas, llamas scripts en el orden correcto, manejas errores, pides aclaraciones, actualizas directivas con lo aprendido. Eres el puente entre intención y ejecución. Ejemplo: no hagas scraping por tu cuenta — lee `directives/scrape_website.md`, define entradas/salidas, ejecuta `execution/scrape_single_site.py`.

**Capa 3 — Ejecución (hacer el trabajo).** Scripts deterministas en `execution/`. Manejan APIs, procesamiento, archivos, DBs. Rápidos, testeables, confiables. Credenciales en `.env`.

**Por qué funciona:** 90% de precisión por paso = 59% de éxito en 5 pasos. Empujar la complejidad hacia código determinista deja al modelo solo lo que hace bien: enrutamiento y juicio.

---

## Formato estándar de una directiva

Toda directiva nueva debe seguir este template para que el agente la parsee consistentemente:

```markdown
# [Nombre del flujo]

## Objetivo
Qué logra este flujo en una frase.

## Cuándo usarla
Señales o triggers que indican que aplica esta directiva.

## Entradas requeridas
- Input 1: descripción, formato, dónde vive
- Input 2: ...

## Herramientas / Scripts
- `execution/script_x.py` — qué hace
- API externa Y — para qué

## Pasos
1. ...
2. ...

## Salidas
- Archivo/artefacto final: dónde se guarda, formato

## Casos extremos y errores conocidos
- Si pasa X → hacer Y
- Rate limit de API Z → esperar N segundos

## Historial de cambios
- YYYY-MM-DD: nota breve
```

Si una directiva no sigue este formato, antes de ejecutarla, propón al usuario reestructurarla.

---

## Ciclo de auto-corrección

Los errores son oportunidades de aprendizaje. Cuando algo falla:

1. Lee el mensaje de error y el stack trace completo.
2. Corrige el script (respetando la regla dura #4 sobre costos).
3. Prueba que funcione.
4. Actualiza la directiva con el nuevo flujo o el caso extremo descubierto.
5. Registra el aprendizaje en la sección de arriba si es no trivial.

**Ejemplo:** llegas al rate limit de una API → investigas → encuentras endpoint batch → reescribes script → pruebas → actualizas directiva → registras aprendizaje.

---

## Logging

Cada script en `execution/` debe registrar su corrida en `.tmp/logs/YYYY-MM-DD.jsonl`, una línea JSON por ejecución con: `timestamp`, `script`, `inputs` (resumen, no dumps enormes), `outputs` (rutas), `status` (ok / error), `error_msg` si aplica, `duration_ms`.

Esto permite debugging, auditoría y detectar regresiones sin depender de la memoria del agente.

---

## Organización de archivos

* `directives/` — SOPs en Markdown (instrucciones).
* `execution/` — scripts Python deterministas (herramientas).
* `.tmp/` — archivos intermedios (scraping, dossiers, exports temporales). Nunca al repo, siempre regenerables.
* `.tmp/logs/` — logs de ejecución.
* `outputs/` — entregables finales que sí importan y sí se comparten con el usuario. Reproducibles corriendo el flujo, no editados a mano.
* `.env` — variables de entorno y claves de API (en `.gitignore`).
* `credentials.json`, `token.json` — OAuth de Google cuando aplique (en `.gitignore`).

**Principio:** todo lo intermedio es descartable; todo lo final es reproducible.
