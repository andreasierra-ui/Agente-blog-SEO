#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache_ahrefs.py — Guarda/lee en caché los resultados de investigación de Ahrefs
por keyword, para no re-consultar la API (ahorra unidades de Ahrefs y tokens)
si el orquestador se vuelve a correr sobre el mismo tema.

No llama a Ahrefs directamente (eso lo hace el agente vía su herramienta MCP);
este script solo administra el archivo de caché en .tmp/ahrefs_cache/.

Uso:
    py execution/cache_ahrefs.py get "mal de altura"      -> imprime el JSON cacheado o "MISS"
    py execution/cache_ahrefs.py set "mal de altura" '<json>'  -> guarda el resultado
"""
import sys, os, json, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, ".tmp", "ahrefs_cache")


def slug(keyword):
    s = re.sub(r"[^a-z0-9]+", "-", keyword.lower().strip())
    h = hashlib.md5(keyword.encode("utf-8")).hexdigest()[:6]
    return f"{s.strip('-')[:60]}-{h}.json"


def main():
    if len(sys.argv) < 3:
        sys.exit('Uso: py cache_ahrefs.py get|set "<keyword>" [json_data]')
    accion, keyword = sys.argv[1], sys.argv[2]
    os.makedirs(CACHE_DIR, exist_ok=True)
    ruta = os.path.join(CACHE_DIR, slug(keyword))

    if accion == "get":
        if os.path.exists(ruta):
            print(open(ruta, encoding="utf-8").read())
        else:
            print("MISS")
    elif accion == "set":
        if len(sys.argv) < 4:
            sys.exit("Falta el JSON a guardar")
        data = json.loads(sys.argv[3])
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"OK -> {ruta}")
    else:
        sys.exit("Acción debe ser 'get' o 'set'")


if __name__ == "__main__":
    main()
