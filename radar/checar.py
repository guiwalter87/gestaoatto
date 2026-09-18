#!/usr/bin/env python3
"""Confere se hoje tem edicao e valida o edicao.json antes do envio.
  python3 radar/checar.py dia            -> imprime a data de hoje (Brasilia) ou SEM_EDICAO
  python3 radar/checar.py validar DATA   -> lista os problemas do edicao.json (vazio = ok)
"""
import datetime, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from produzir import FERIADOS, validar

BRT = datetime.timezone(datetime.timedelta(hours=-3))
if sys.argv[1] == "dia":
    d = datetime.datetime.now(BRT).date()
    print("SEM_EDICAO" if d.weekday() >= 5 or d.isoformat() in FERIADOS else d.isoformat())
else:
    data = sys.argv[2]
    ed = json.load(open(os.path.join(AQUI, "edicoes", data, "edicao.json"), encoding="utf-8"))
    erros = validar(ed, data)
    print("OK" if not erros else "\n".join("PROBLEMA: " + e for e in erros))
    sys.exit(1 if erros else 0)
