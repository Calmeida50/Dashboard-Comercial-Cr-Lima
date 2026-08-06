#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_dartora.py — le os arquivos de sell out da Dartora e compara com o
dashboard. NAO grava nada.

Diferencas em relacao a Sao Joao:
  - nome do arquivo NEM SEMPRE traz o ano -> o ano vem da PASTA (2025/ ou 2026/)
  - dois tipos de relatorio: regular (por produto) e "POR VENDEDOR"
  - o regular ja vem liquido (`Valor líq`), sem coluna bruta
  - traz `Qtd clientes`, que a Sao Joao nao tem
"""
import os, re, json, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["BELLIZ", "CLESS", "EVER GREEN", "GRANADO", "PRUDENCE"]
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper().replace("_", " ")
    return re.sub(r"\s+", " ", s).strip()


def arquivos():
    """indexa todos os arquivos da Dartora por (empresa, mes, ano, tipo)"""
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        nome = norm(os.path.basename(p))
        if "DARTORA" not in nome or "VENDEDORES DO" in nome:
            continue
        tipo = "vendedor" if "POR VENDEDOR" in nome else "produto"
        emp = next((e for e in EMPRESAS if norm(e) in nome), None)
        mes = next((m for m in MESES if m in nome), None)
        if not emp or not mes:
            continue
        # ano: primeiro tenta a pasta, depois o sufixo do nome
        cam = norm(p)
        ano = None
        for a in ("2025", "2026"):
            if "/" + a + "/" in p or "/%s " % a[-2:] in cam:
                ano = a[-2:]
        if ano is None:
            m = re.search(r"\b(25|26)\b", nome)
            ano = m.group(1) if m else None
        if ano is None:
            continue
        idx.setdefault((emp, mes, ano, tipo), []).append(p)
    return idx


def ler_produto(path):
    """soma o valor liquido do relatorio regular.
    Varios arquivos tem um titulo antes do cabecalho ('Relatorio das vendas
    por item'), com o cabecalho real la pela linha 7 — procurar."""
    hdr = None
    cru = pd.read_excel(path, header=None, nrows=15)
    for r in range(len(cru)):
        linha = [norm(x) for x in cru.iloc[r].tolist() if str(x) != "nan"]
        if any("VALOR" in x or "VLR" in x for x in linha) and len(linha) >= 3:
            hdr = r
            break
    if hdr is None:
        return None, "cabecalho nao encontrado"
    d = pd.read_excel(path, header=hdr)
    col = next((c for c in d.columns if "VALOR" in norm(c) or "VLR" in norm(c)), None)
    if col is None:
        return None, "sem coluna de valor: %s" % list(d.columns)[:6]
    v = pd.to_numeric(d[col], errors="coerce").fillna(0)
    desc = next((c for c in d.columns if "DESCRICAO" in norm(c) or "DESCRIC" in norm(c)), None)
    if desc is not None:
        v = v[d[desc].notna()]
    return float(v.sum()), None


def dashboard():
    h = open("index.html", encoding="utf-8").read()
    m = re.search(r"const\s+DADOS_EMBEDDED\s*=\s*", h)
    i = m.end(); d = 0; j = i; ins = False; esc = False
    while j < len(h):
        c = h[j]
        if esc: esc = False
        elif c == "\\": esc = True
        elif c == '"': ins = not ins
        elif not ins:
            if c == "{": d += 1
            elif c == "}":
                d -= 1
                if d == 0: break
        j += 1
    return json.loads(h[i:j + 1])["sellout_dartora"]


def main():
    idx = arquivos()
    da = dashboard()
    print("=" * 76)
    print("  CONFERENCIA SELL OUT DARTORA — arquivos vs dashboard")
    print("=" * 76)
    ok = div = 0
    faltam_arq, faltam_dash = [], []
    for ano2, chave in (("25", "mensal_2025"), ("26", "mensal_2026")):
        print("\n--- 20%s" % ano2)
        for emp in EMPRESAS:
            bloco = da.get(emp, {}).get(chave, {})
            for k, mes in enumerate(MESES):
                alvo = bloco.get(ABREV[k])
                arqs = idx.get((emp, mes, ano2, "produto"), [])
                if not arqs and alvo is None:
                    continue                      # nao existe nem la nem ca
                if not arqs:
                    faltam_arq.append("%s %s/%s (dash tem %.2f)" % (emp, ABREV[k], ano2, alvo))
                    continue
                val, erro = ler_produto(arqs[0])
                if erro:
                    print("  %-11s %-4s ERRO %s" % (emp, ABREV[k], erro))
                    continue
                if alvo is None:
                    faltam_dash.append("%s %s/%s (arquivo tem %.2f)" % (emp, ABREV[k], ano2, val))
                    continue
                dif = val - alvo
                if abs(dif) < 0.05:
                    ok += 1
                else:
                    div += 1
                    print("  %-11s %-4s arquivo %12s  dash %12s  dif %11s"
                          % (emp, ABREV[k], "{:,.2f}".format(val),
                             "{:,.2f}".format(alvo), "{:,.2f}".format(dif)))
    print("\n" + "=" * 76)
    print("conferem: %d   divergem: %d" % (ok, div))
    if faltam_arq:
        print("\nno dashboard mas SEM arquivo (%d):" % len(faltam_arq))
        for x in faltam_arq[:12]: print("   -", x)
    if faltam_dash:
        print("\ncom arquivo mas AUSENTE do dashboard (%d):" % len(faltam_dash))
        for x in faltam_dash[:12]: print("   -", x)


if __name__ == "__main__":
    main()
