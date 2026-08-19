#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae el texto visible de un archivo HTML. Uso: py execution/leer_html.py <ruta.html>"""
import sys, re, html

data = open(sys.argv[1], encoding="utf-8", errors="replace").read()
data = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", data)
data = re.sub(r"(?s)<[^>]+>", " ", data)
data = html.unescape(data)
data = re.sub(r"[ \t]+", " ", data)
data = re.sub(r"\n\s*\n\s*\n+", "\n\n", data)
lines = [l.strip() for l in data.splitlines()]
print("\n".join(l for l in lines if l))
