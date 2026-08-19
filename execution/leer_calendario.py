#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
leer_calendario.py — Lee SOLO la pestaña "Calendario 2026" del Sheet de Mundo
Joven (exportación CSV pública, sin volcar el archivo completo) y devuelve los
artículos de blog pendientes ("Sin iniciar", vertical no-Optimización).

Uso:
    py execution/leer_calendario.py                 -> imprime pendientes (todas las fechas)
    py execution/leer_calendario.py --fecha 7/31/2026 -> filtra por semana

Salida: JSON compacto a stdout (barato en tokens), una línea por artículo:
[{"fila": 237, "titulo": "...", "vertical": "...", "fecha": "...", "estado": "..."}]
"""
import sys, csv, io, argparse, json, time
from urllib import request

SHEET_ID = "1pPuIhgHzl4-p-7sVm0r9dayqHluDvvL17s63auXEvrE"
GID = "913428203"  # pestaña "Calendario 2026"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"


def descargar():
    for i in range(6):
        try:
            req = request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            return request.urlopen(req, timeout=60).read().decode("utf-8")
        except Exception:
            if i == 5:
                raise
            time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", help='Filtra por fecha exacta de la columna, ej. "7/31/2026"')
    ap.add_argument("--estado", default="Sin iniciar")
    a = ap.parse_args()

    texto = descargar()
    filas = list(csv.reader(io.StringIO(texto)))

    # Nota: el número de fila del Sheet NO se puede deducir de forma 100% fiable
    # desde el CSV (alguna celda anterior puede tener saltos de línea internos
    # que desalinean el conteo). Usamos el TÍTULO como identificador y un
    # orden secuencial dentro del resultado, que es lo que de verdad se necesita.
    pendientes = []
    for row in filas:
        if len(row) < 9:
            continue
        _, num, titulo, _, vertical, _url, fecha, tipo, resp = row[:9]
        estado = row[9] if len(row) > 9 else ""
        if vertical.strip().lower() == "optimizaciones/ajustes":
            continue  # no es blog
        if not titulo or not fecha:
            continue
        if estado.strip() != a.estado:
            continue
        if a.fecha and fecha.strip() != a.fecha:
            continue
        pendientes.append({
            "orden": len(pendientes) + 1, "titulo": titulo.strip(), "vertical": vertical.strip(),
            "fecha": fecha.strip(), "estado": estado.strip(),
        })

    print(json.dumps(pendientes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
