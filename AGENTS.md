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
