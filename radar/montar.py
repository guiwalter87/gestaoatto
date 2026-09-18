#!/usr/bin/env python3
"""Radar Atto: monta a edicao a partir do edicao.json gravado pela tarefa do Claude.
Valida o texto, gera as 3 artes e copia para a pasta publicada do site.
Uso: python3 radar/montar.py AAAA-MM-DD
"""
import json, os, shutil, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from produzir import validar  # mesmas regras de redacao

data = sys.argv[1]
pasta = os.path.join(AQUI, "edicoes", data)
arq = os.path.join(pasta, "edicao.json")
ed = json.load(open(arq, encoding="utf-8"))
erros = validar(ed, data)
if erros:
    print("EDICAO REPROVADA NA VALIDACAO:")
    for e in erros:
        print(" -", e)
    sys.exit(1)
subprocess.run([sys.executable, os.path.join(AQUI, "gerar_radar_jornal.py"), arq, pasta], check=True)
site = os.path.join(RAIZ, "site", "radar", data)
os.makedirs(site, exist_ok=True)
for i in (1, 2, 3):
    shutil.copy(os.path.join(pasta, f"story_{i}.jpg"), os.path.join(site, f"story_{i}.jpg"))
print("Edicao montada:", data)
