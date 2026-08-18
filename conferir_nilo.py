#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_nilo.py — valida o sell out da Nilo Tozzo contra o dashboard.

Layout (xlsx, 7 colunas):
    linha 0: NaN NaN NaN NaN  Total Total Total
    linha 1: Cod | Produto | Marca | Cod Fab | Pos | Fat | Qt Itens   <- cabecalho
    linha 2: Total ... (TOTALIZACAO no TOPO, nao no fim)
    linha 3+: dados

`Pos` = positivacao nativa (clientes por SKU), igual a Dartora.
`Fat` = faturamento. `Qt Itens` = quantidade.
"""
import os, re, json, glob, unicodedata
import pandas as pd
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["GRANADO", "PRUDENCE"]
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]
ABREV = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def arquivos():
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if "NILO" not in n:
            continue
        emp = next((e for e in EMPRESAS if e in n), None)
        mes = next((m for m in MESES if m in n), None)
        if not emp or not mes:
            continue
        ano = None
        for a in ("2025", "2026"):
            if "/" + a + "/" in p:
                ano = a[-2:]
        if ano is None:
            mm = re.search(r"\b(25|26)\b", n)
            ano = mm.group(1) if mm else None
        if ano:
            idx.setdefault((emp, mes, ano), []).append(p)
    return idx


def ler(path):
    """devolve (faturamento, positivacao_total, linhas) descartando o Total"""
    cru = _ler_excel(path, header=None, nrows=6)
    hdr = None
    for r in range(len(cru)):
        linha = [norm(x) for x in cru.iloc[r].tolist()]
        if any(x == "COD" for x in linha) and any("PRODUTO" in x for x in linha):
            hdr = r
            break
    if hdr is None:
        return None, None, "cabecalho nao encontrado"
    d = _ler_excel(path, header=hdr)
    cCod = next((c for c in d.columns if norm(c) == "COD"), None)
    # a coluna de valor muda de nome entre os meses: as vezes 'Fat', na maioria
    # 'Total'. NAO confundir com 'Vl Tabela' (preco de tabela), 'Dif Total'
    # (diferenca) nem 'Bnf' (bonificacao).
    cFat = next((c for c in d.columns if norm(c).startswith("FAT")), None)
    if cFat is None:
        cFat = next((c for c in d.columns if norm(c) == "TOTAL"), None)
    cPos = next((c for c in d.columns if norm(c) == "POS"), None)
    if cFat is None:
        return None, None, "coluna Fat nao encontrada: %s" % list(d.columns)
    # a linha de TOTAL vem no TOPO, marcada na coluna Cod
    if cCod is not None:
        d = d[d[cCod].astype(str).map(norm) != "TOTAL"]
    d = d[d[cFat].notna()]
    fat = float(pd.to_numeric(d[cFat], errors="coerce").fillna(0).sum())
    pos = float(pd.to_numeric(d[cPos], errors="coerce").fillna(0).sum()) if cPos else 0.0
    return fat, pos, None


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
    return json.loads(h[i:j + 1]).get("sellout_nilo_tozzo", {})


def main():
    idx = arquivos()
    nt = dashboard()
    print("=" * 74)
    print("  CONFERENCIA SELL OUT NILO TOZZO")
    print("=" * 74)
    ok = div = 0
    faltam_dash = []
    for ano2, chave in (("25", "mensal_2025"), ("26", "mensal_2026")):
        for emp in EMPRESAS:
            bloco = nt.get(emp, {}).get(chave, {})
            for k, mes in enumerate(MESES):
                alvo = bloco.get(ABREV[k])
                arqs = idx.get((emp, mes, ano2), [])
                if not arqs and alvo is None:
                    continue
                if not arqs:
                    print("  %-9s %-4s/%s  sem arquivo (dash tem %.2f)" % (emp, ABREV[k], ano2, alvo))
                    continue
                fat, pos, erro = ler(arqs[0])
                if erro:
                    print("  %-9s %-4s/%s  ERRO %s" % (emp, ABREV[k], ano2, erro))
                    continue
                if alvo is None:
                    faltam_dash.append("%s %s/%s = %.2f (pos %d)" % (emp, ABREV[k], ano2, fat, pos))
                    continue
                dif = fat - alvo
                if abs(dif) < 0.05:
                    ok += 1
                else:
                    div += 1
                    print("  %-9s %-4s/%s  arquivo %12s  dash %12s  dif %11s"
                          % (emp, ABREV[k], ano2, "{:,.2f}".format(fat),
                             "{:,.2f}".format(alvo), "{:,.2f}".format(dif)))
    print("\nconferem: %d   divergem: %d" % (ok, div))
    if faltam_dash:
        print("\ncom arquivo mas AUSENTE do dashboard (%d):" % len(faltam_dash))
        for x in faltam_dash[:14]:
            print("   -", x)


if __name__ == "__main__":
    main()
