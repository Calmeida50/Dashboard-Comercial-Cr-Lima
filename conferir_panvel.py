#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_panvel.py — valida o sell out da Panvel contra o dashboard.

Particularidades da Panvel:
  - os dados NAO ficam no DADOS_EMBEDDED, e sim numa constante propria
    `DADOS_PANVEL` (empresas GRANADO e PRUDENCE)
  - separa LOJA fisica de CANAL DIGITAL pela coluna `Origem Venda`
    (valores 'Loja' e 'C.Dig') -> ytd_loja / ytd_cdig no dashboard
  - o arquivo ja traz o ano anterior calculado
  - DUAS familias de arquivo: os regulares (20 colunas, por produto) e os
    "POR LOJA" (22 colunas), que alimentam a lista de lojas
  - ARMADILHA: o valor vem como TEXTO em quase todos os meses
    ("'30.038,03'"), com apostrofo, ponto de milhar e virgula decimal.
    Só março/26 veio numérico. Sem conversão o mês soma ZERO em silêncio.
"""
import os, re, json, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["GRANADO", "PRUDENCE", "CLESS"]
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def to_num(v):
    """'30.038,03' -> 30038.03 ; aceita numerico direto"""
    if isinstance(v, (int, float)):
        try:
            f = float(v)
            return 0.0 if pd.isna(f) else f
        except Exception:
            return 0.0
    t = str(v).strip().strip("'\"")
    t = re.sub(r"[R$\s\u00a0]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    t = re.sub(r"[^0-9.\-]", "", t)
    try:
        return float(t)
    except Exception:
        return 0.0


def arquivos(por_loja=False):
    """indexa {(empresa, mes): caminho}. por_loja=True traz a outra familia."""
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if "PANVEL" not in n:
            continue
        eh_loja = "POR LOJA" in n
        if eh_loja != por_loja:
            continue
        emp = next((e for e in EMPRESAS if e in n), None)
        mes = next((m for m in MESES if m in n), None)
        if emp and mes:
            idx[(emp, mes)] = p
    return idx


def ler(path, detalhe=False):
    """devolve (valor_loja, valor_digital, erro).
    Com detalhe=True devolve tambem o ano anterior e a abertura por produto:
    (loja, dig, erro, loja_aa, dig_aa, produtos).
    O arquivo SEMPRE traz 'Venda Efetiva Ano Anterior' — o gravador antigo so
    preservava o que ja existia no bloco e por isso a PRUDENCE ficava sem 2025."""
    d = pd.read_excel(path)
    col = next((c for c in d.columns
                if "VENDA EFETIVA" in norm(c) and "ANTERIOR" not in norm(c)), None)
    col_aa = next((c for c in d.columns
                   if "VENDA EFETIVA" in norm(c) and "ANTERIOR" in norm(c)), None)
    org = next((c for c in d.columns if "ORIGEM" in norm(c)), None)
    cnome = next((c for c in d.columns if "DESCRICAO ITEM" in norm(c)
                  or ("ITEM" in norm(c) and "DESCRICAO" in norm(c))), None)
    cqtd = next((c for c in d.columns if "QTD" in norm(c) and "VENDA" in norm(c)
                 and "ANTERIOR" not in norm(c)), None)
    if col is None:
        return (None, None, "coluna de venda nao encontrada", None, None, None) \
            if detalhe else (None, None, "coluna de venda nao encontrada")

    d["_v"] = d[col].map(to_num)
    d["_vaa"] = d[col_aa].map(to_num) if col_aa is not None else 0.0
    d["_q"] = d[cqtd].map(to_num) if cqtd is not None else 0.0

    if org is None:
        loja, dig = float(d["_v"].sum()), 0.0
        loja_aa, dig_aa = float(d["_vaa"].sum()), 0.0
    else:
        eh_loja = d[org].astype(str).str.strip().map(lambda k: norm(k).startswith("LOJA"))
        loja = float(d.loc[eh_loja, "_v"].sum())
        dig = float(d.loc[~eh_loja, "_v"].sum())
        loja_aa = float(d.loc[eh_loja, "_vaa"].sum())
        dig_aa = float(d.loc[~eh_loja, "_vaa"].sum())

    if not detalhe:
        return loja, dig, None

    produtos = []
    if cnome is not None:
        g = d.groupby(d[cnome].astype(str).str.strip()).agg(
            v=("_v", "sum"), vaa=("_vaa", "sum"), q=("_q", "sum"))
        for nome, r in g.iterrows():
            if not nome or nome.upper() in ("NAN", "TOTAL"):
                continue
            produtos.append({"nome": nome, "val": round(float(r["v"]), 2),
                             "val_aa": round(float(r["vaa"]), 2),
                             "qtd": int(r["q"])})
        produtos.sort(key=lambda x: -x["val"])
    return loja, dig, None, loja_aa, dig_aa, produtos


def dashboard():
    s = open("index.html", encoding="utf-8").read()
    i = s.find("const DADOS_PANVEL = ") + len("const DADOS_PANVEL = ")
    d = 0; j = i; ins = False; esc = False
    while j < len(s):
        c = s[j]
        if esc: esc = False
        elif c == "\\": esc = True
        elif c == '"': ins = not ins
        elif not ins:
            if c == "{": d += 1
            elif c == "}":
                d -= 1
                if d == 0: break
        j += 1
    return json.loads(s[i:j + 1])


def main():
    idx = arquivos()
    dp = dashboard()
    print("=" * 74)
    print("  CONFERENCIA SELL OUT PANVEL")
    print("=" * 74)
    for emp in EMPRESAS:
        alvoL = dp.get(emp, {}).get("ytd_loja")
        alvoD = dp.get(emp, {}).get("ytd_cdig")
        tl = td = 0.0
        meses = []
        for mes in MESES:
            p = idx.get((emp, mes))
            if not p:
                continue
            l, dg, erro = ler(p)
            if erro:
                print("  %s %s: %s" % (emp, mes[:3], erro))
                continue
            tl += l; td += dg
            meses.append(mes[:3].title())
        print("\n%s — %d meses: %s" % (emp, len(meses), ", ".join(meses)))
        print("   %-10s %16s %16s" % ("", "ARQUIVOS", "DASHBOARD"))
        print("   %-10s %16s %16s  %s" % ("loja",
              "{:,.2f}".format(tl), "{:,.2f}".format(alvoL or 0),
              "OK" if alvoL and abs(tl - alvoL) < 0.05 else "DIVERGE"))
        print("   %-10s %16s %16s  %s" % ("digital",
              "{:,.2f}".format(td), "{:,.2f}".format(alvoD or 0),
              "OK" if alvoD and abs(td - alvoD) < 0.05 else "DIVERGE"))
        print("   %-10s %16s %16s" % ("total",
              "{:,.2f}".format(tl + td),
              "{:,.2f}".format(dp.get(emp, {}).get("ytd_total", 0))))

    pl = arquivos(por_loja=True)
    if pl:
        print("\narquivos POR LOJA (alimentam a lista de lojas):")
        for k, v in pl.items():
            print("   %s %s -> %s" % (k[0], k[1][:3], os.path.basename(v)[:46]))


if __name__ == "__main__":
    main()
