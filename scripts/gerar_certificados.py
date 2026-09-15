#!/usr/bin/env python3
"""
Atto · Gerador de certificados validáveis
=========================================

Lê o registro privado (Site da Atto/certificados/registro.json), atribui um
código a cada participante que ainda não tem, e gera:

1. site/certificados/d/<id>.json  (PÚBLICO, vai para o site)
   Dados do certificado cifrados com AES-256-GCM. A chave é derivada do
   próprio código (PBKDF2-SHA256). O nome do arquivo é um hash do código.
   Quem olha o repositório ou o site vê só hashes e texto cifrado: nenhum
   nome, empresa ou programa fica exposto. Só quem tem o código abre.

2. certificados/qr/<codigo>.png e .json  (PRIVADO, fica fora do repositório)
   QR Code para impressão e o desenho vetorial usado no Canva.

3. certificados/codigos.csv  (PRIVADO)
   Lista de conferência: turma, nome, código, URL de validação.

Uso:  python3 scripts/gerar_certificados.py
"""
import base64
import csv
import hashlib
import json
import os
import secrets
import sys
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

REPO = Path(__file__).resolve().parent.parent          # Site da Atto/site
BASE = REPO.parent                                     # Site da Atto
REGISTRO = BASE / "certificados" / "registro.json"
PUBLICO = REPO / "site" / "certificados" / "d"
QR_DIR = BASE / "certificados" / "qr"
CSV_OUT = BASE / "certificados" / "codigos.csv"

URL_BASE = "https://www.gestaoatto.com.br/certificados/#"
ALFABETO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"   # sem 0/O, 1/I/L
ITERACOES = 210_000
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def normalizar(codigo: str) -> str:
    return "".join(ch for ch in codigo.upper() if ch.isalnum() or ch == "-").strip("-")


def novo_codigo(turma_id: str, existentes: set) -> str:
    while True:
        s = "".join(secrets.choice(ALFABETO) for _ in range(8))
        cod = f"{turma_id}-{s[:4]}-{s[4:]}"
        if cod not in existentes:
            return cod


def arquivo_id(codigo: str) -> str:
    return hashlib.sha256(f"atto-cert-v1|{normalizar(codigo)}".encode()).hexdigest()[:40]


def chave(codigo: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERACOES)
    return kdf.derive(normalizar(codigo).encode())


def cifrar(codigo: str, dados: dict) -> dict:
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    ct = AESGCM(chave(codigo, salt)).encrypt(iv, json.dumps(dados, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "it": ITERACOES, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def decifrar(codigo: str, env: dict):
    try:
        d = lambda s: base64.b64decode(s)
        pt = AESGCM(chave(codigo, d(env["salt"]))).decrypt(d(env["iv"]), d(env["ct"]), None)
        return json.loads(pt)
    except Exception:
        return None


def data_extenso(iso: str) -> str:
    y, m, dd = map(int, iso.split("-"))
    return f"{dd} de {MESES[m - 1]} de {y}"


def qr(codigo: str):
    import qrcode
    from qrcode.constants import ERROR_CORRECT_Q
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=0)
    q.add_data(URL_BASE + codigo)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    # Desenho vetorial: um retângulo por sequência horizontal de módulos pretos
    partes = []
    for y, linha in enumerate(m):
        x = 0
        while x < n:
            if linha[x]:
                ini = x
                while x < n and linha[x]:
                    x += 1
                partes.append(f"M{ini} {y}H{x}V{y + 1}H{ini}Z")
            else:
                x += 1
    QR_DIR.mkdir(parents=True, exist_ok=True)
    (QR_DIR / f"{codigo}.json").write_text(json.dumps(
        {"codigo": codigo, "url": URL_BASE + codigo, "modulos": n, "path": "".join(partes)}), encoding="utf-8")
    img = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=2, box_size=24)
    img.add_data(URL_BASE + codigo)
    img.make(fit=True)
    img.make_image(fill_color="#0A0E1A", back_color="white").save(QR_DIR / f"{codigo}.png")


def main():
    if not REGISTRO.exists():
        sys.exit(f"Registro não encontrado: {REGISTRO}")
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))
    existentes = {p["codigo"] for t in reg["turmas"] for p in t["participantes"] if p.get("codigo")}
    PUBLICO.mkdir(parents=True, exist_ok=True)

    novos = gravados = inalterados = 0
    linhas = []
    esperados = set()
    for t in reg["turmas"]:
        for p in t["participantes"]:
            if not p.get("codigo"):
                p["codigo"] = novo_codigo(t["id"], existentes)
                existentes.add(p["codigo"])
                novos += 1
            cod = normalizar(p["codigo"])
            dados = {
                "codigo": cod,
                "status": p.get("status", "valido"),
                "nome": p["nome"],
                "programa": t["programa"],
                "descricao": t.get("descricao", ""),
                "empresa": t.get("empresa", ""),
                "periodo": t["periodo"],
                "carga_horaria": t["carga_horaria"],
                "conteudo_rotulo": t.get("conteudo_rotulo", ""),
                "conteudo": t.get("conteudo", ""),
                "emissao": f'{t["local"]}, {data_extenso(t["emissao"])}',
                "responsavel": t["responsavel"],
                "responsavel_cargo": t.get("responsavel_cargo", ""),
                "emissor": "Atto Estratégias & Educação",
            }
            fid = arquivo_id(cod)
            esperados.add(f"{fid}.json")
            destino = PUBLICO / f"{fid}.json"
            atual = None
            if destino.exists():
                atual = decifrar(cod, json.loads(destino.read_text(encoding="utf-8")))
            if atual == dados:
                inalterados += 1
            else:
                destino.write_text(json.dumps(cifrar(cod, dados)), encoding="utf-8")
                gravados += 1
            qr(cod)
            linhas.append([t["id"], p["nome"], cod, p.get("status", "valido"), URL_BASE + cod])

    REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["turma", "nome", "codigo", "status", "url_validacao"])
        w.writerows(linhas)

    orfaos = sorted(x.name for x in PUBLICO.glob("*.json") if x.name not in esperados)
    print(f"Certificados: {len(linhas)} | códigos novos: {novos} | arquivos gravados: {gravados} | inalterados: {inalterados}")
    if orfaos:
        print("Arquivos públicos sem participante no registro (avaliar remoção):", ", ".join(orfaos))
    print(f"Lista de conferência: {CSV_OUT}")


if __name__ == "__main__":
    main()
