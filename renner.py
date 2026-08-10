#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renner.py — leitura do sell out semanal das Lojas Renner (Granado).

DIFERENTE DOS OUTROS CLIENTES: o relatorio da Renner e SEMANAL, nao mensal.
Uma planilha por semana, na pasta propria dentro de
`SELL OUT PRINCIPAIS CLIENTES`.

LAYOUT (cabecalho na linha 2, colunas A..V):
    A  Week            semana no formato AAAASS (202631 = semana 31 de 2026)
    B,C,D              nao usar
    E  Item            descricao do produto
    F  Item UDA        codigo do produto
    G  Location        codigo da loja
    H  (nome)          nome da loja
    J  Sales Value                     venda da semana em R$
    K  Sales Value (Last Year)         mesma semana do ano anterior
    L  Sales Value (MTD)               mes corrente ate a semana
    M  Sales Value (MTD, Last Year)    mesmo periodo do ano anterior
    N  Sales Value (YTD)               acumulado do ano
    O  Sales Value (YTD, Last Year)    acumulado do ano anterior
    P  Sales Units                     venda da semana em unidades
    Q  Sales Units (Last Year)
    R  Sales Units (MTD)
    S  Sales Units (MTD, Last Year)
    T  Sales Units (YTD)               (NAO ha YTD de unidades do ano anterior)
    U  EOH - In Transit Units          estoque atual (lojas, e-commerce e CD)
    V  In Transit Units                em transito para as lojas

'NA' e vazio contam como ZERO.

FECHAMENTO MENSAL — o MTD ZERA na virada do mes, entao a ULTIMA semana de cada
mes carrega o total fechado. Isso e melhor que agrupar de 4 em 4 semanas:
segue o calendario real da Renner E traz o comparativo com o ano anterior.
Confirmado nas 31 semanas de 2026.

E-COMMERCE separado das lojas fisicas: a loja 574 e o e-commerce, e so os
PERFUMES ficam em loja fisica. O restante do mix e so site.
"""
import os, re, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
LOJA_ECOM = 574

# As 80 lojas que DEVEM ter a linha de perfume (lista oficial do Cristiano).
# REGRA (10/08/2026): o relatorio traz 102 lojas com perfume — as 22 extras
# receberam produto POR ENGANO. Entao:
#   - FATURAMENTO / performance: conta TODAS (as 22 entram como grupo a parte)
#   - ESTOQUE e RUPTURA: SO estas 80. Nao se cobra abastecimento de loja que
#     nao deveria ter o produto.
LOJAS_OFICIAIS = {
    1, 2, 4, 6, 11, 13, 27, 29, 30, 31, 33, 37, 39, 40, 41, 43, 44, 45, 46,
    47, 49, 50, 53, 56, 59, 60, 62, 66, 67, 69, 73, 76, 77, 81, 84, 85, 87,
    88, 89, 91, 96, 100, 102, 105, 106, 110, 112, 119, 126, 127, 132, 141,
    146, 159, 163, 168, 170, 172, 182, 193, 234, 236, 257, 260, 269, 271,
    277, 278, 286, 287, 291, 295, 300, 307, 322, 326, 360, 426, 458, 509,
}

# Loja da lista oficial que NUNCA recebeu produto — nao aparece em nenhuma
# linha do relatorio. Fica no radar: se aparecer estoque nas proximas semanas,
# e sinal de que o abastecimento finalmente chegou.
LOJAS_SEM_HISTORICO = {88}

# colunas por posicao (0-based apos header=2)
COL = {"week": 0, "item": 4, "cod": 5, "loja_cod": 6, "loja_nome": 7,
       "vl_sem": 9, "vl_sem_aa": 10, "vl_mtd": 11, "vl_mtd_aa": 12,
       "vl_ytd": 13, "vl_ytd_aa": 14,
       "un_sem": 15, "un_sem_aa": 16, "un_mtd": 17, "un_mtd_aa": 18,
       "un_ytd": 19, "estoque": 20, "transito": 21}

# mix de perfume: os 4 ultimos saem de loja fisica e ficam SO no e-commerce
PERFUME_LOJA = {
    "931438297": "AMAZONICO 75ML",
    "929848107": "Boemia Parfum 75ml",
    "931116714": "BOSSA EDT 100ML",
    "931116693": "CARIOCA EDT 100ML",
    "930803432": "CITRUS BRASILIS 75ML",
    "929848027": "Epoque Tropical Parfum 75ml",
    "929848140": "Esplendor Parfum 75ml",
    "929848043": "Fervo Intenso Parfum 75ml",
    "930606990": "Flora Magnifica 75ML",
    "929848182": "Imperial Parfum 75ml",
    "929848086": "Jardim Real Parfum 75ml",
    "929848203": "Nostalgia Parfum 75ml",
    "930607010": "Oasis 75ML",
    "931311042": "ROSA APOTECARIO 75ML",
    "930803459": "ROSA SUBLIME 75ML",
    "930607036": "Tropicalia 75ML",
}
PERFUME_SO_ECOM = {
    "929848060": "Infusao Botanica Parfum 75ml",
    "929848220": "Folia Parfum 75ml",
    "929848166": "Expedicao Parfum 75ml",
    "929848123": "Elixir 1870 Parfum 75ml",
}
MIX_PERFUME = {**PERFUME_LOJA, **PERFUME_SO_ECOM}


def semanas():
    """[(numero, caminho)] ordenado"""
    out = []
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        if "RENNER" not in p.upper():
            continue
        m = re.search(r"Semana\s+(\d+)", os.path.basename(p), re.I)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out)


def ler(path):
    """DataFrame normalizado de uma semana; NA vira 0.

    As colunas sao identificadas pelo NOME, nao pela posicao: a semana 28/2026
    veio com 21 colunas em vez de 22 (faltou 'Sales Value'), e ler por posicao
    deslocava tudo — o ano anterior entrava no lugar da venda e o YTD de 2025
    no lugar do de 2026."""
    d = pd.read_excel(path, header=2)

    def acha(*termos, excl=()):
        for c in d.columns:
            n = str(c).upper()
            if all(t in n for t in termos) and not any(e in n for e in excl):
                return c
        return None

    MAP = {
        "vl_sem":    acha("SALES VALUE", excl=("LAST YEAR", "MTD", "YTD")),
        "vl_sem_aa": acha("SALES VALUE", "LAST YEAR", excl=("MTD", "YTD")),
        "vl_mtd":    acha("SALES VALUE", "MTD", excl=("LAST YEAR",)),
        "vl_mtd_aa": acha("SALES VALUE", "MTD", "LAST YEAR"),
        "vl_ytd":    acha("SALES VALUE", "YTD", excl=("LAST YEAR",)),
        "vl_ytd_aa": acha("SALES VALUE", "YTD", "LAST YEAR"),
        "un_sem":    acha("SALES UNITS", excl=("LAST YEAR", "MTD", "YTD")),
        "un_sem_aa": acha("SALES UNITS", "LAST YEAR", excl=("MTD", "YTD")),
        "un_mtd":    acha("SALES UNITS", "MTD", excl=("LAST YEAR",)),
        "un_mtd_aa": acha("SALES UNITS", "MTD", "LAST YEAR"),
        "un_ytd":    acha("SALES UNITS", "YTD", excl=("LAST YEAR",)),
        "estoque":   acha("EOH"),
        "transito":  acha("IN TRANSIT", excl=("EOH",)),
    }

    out = pd.DataFrame()
    out["week"] = d.iloc[:, COL["week"]]
    out["item"] = d.iloc[:, COL["item"]]
    out["cod"] = d.iloc[:, COL["cod"]]
    out["loja_cod"] = d.iloc[:, COL["loja_cod"]]
    out["loja_nome"] = d.iloc[:, COL["loja_nome"]]
    for nome, col in MAP.items():
        out[nome] = (pd.to_numeric(d[col], errors="coerce").fillna(0.0)
                     if col is not None else 0.0)

    out = out[out["cod"].notna()]
    out["cod"] = out["cod"].apply(
        lambda x: str(int(x)) if isinstance(x, float) and not pd.isna(x) else str(x).strip())
    out["loja_cod"] = pd.to_numeric(out["loja_cod"], errors="coerce").fillna(0).astype(int)
    out["item"] = out["item"].astype(str).str.strip()
    out["loja_nome"] = out["loja_nome"].astype(str).str.strip()
    return out


def meses_fechados(todas=None):
    """Reconstroi os meses a partir da virada do MTD.
    O MTD zera quando o mes vira, entao a semana ANTERIOR a virada carrega o
    total fechado daquele mes. Devolve [(nome_mes, semana, dados_da_semana)].
    """
    if todas is None:
        todas = semanas()
    NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    resumo = []
    ant_mtd = None
    ant = None          # (semana, soma_mtd, soma_mtd_aa, soma_un, soma_un_aa)
    idx_mes = 0
    for n, p in todas:
        d = ler(p)
        mtd = float(d["vl_mtd"].sum())
        # semana incompleta (arquivo veio sem dados) — nao serve de fechamento
        if mtd == 0:
            continue
        if ant_mtd is not None and mtd < ant_mtd:
            # virou o mes: a semana ANTERIOR fechou
            resumo.append((NOMES[idx_mes], ant[0], ant[1], ant[2], ant[3], ant[4]))
            idx_mes += 1
        ant_mtd = mtd
        ant = (n, mtd, float(d["vl_mtd_aa"].sum()),
               float(d["un_mtd"].sum()), float(d["un_mtd_aa"].sum()))
    if ant:   # mes corrente, ainda aberto
        resumo.append((NOMES[idx_mes] + " (parcial)", ant[0], ant[1], ant[2],
                       ant[3], ant[4]))
    return resumo


def ultima_semana():
    """(numero, DataFrame) da semana mais recente COM dados completos"""
    for n, p in reversed(semanas()):
        d = ler(p)
        if d["estoque"].sum() > 0 or d["vl_sem"].sum() > 0:
            return n, d
    return None, None


def separa_operacao(d):
    """(lojas_fisicas, ecommerce)"""
    ecom = d[d["loja_cod"] == LOJA_ECOM]
    fisica = d[d["loja_cod"] != LOJA_ECOM]
    return fisica, ecom


def grupos(d):
    """Separa nos TRES grupos que o Cristiano definiu:
        oficiais  — as 80 que devem ter perfume (base de estoque e ruptura)
        extras    — receberam produto por engano; contam no faturamento,
                    mas NAO entram na cobranca de abastecimento
        ecommerce — loja 574
    """
    ecom = d[d["loja_cod"] == LOJA_ECOM]
    fis = d[d["loja_cod"] != LOJA_ECOM]
    oficiais = fis[fis["loja_cod"].isin(LOJAS_OFICIAIS)]
    extras = fis[~fis["loja_cod"].isin(LOJAS_OFICIAIS)]
    return oficiais, extras, ecom


if __name__ == "__main__":
    print("semanas no Drive:", len(semanas()))
    print("\nFECHAMENTO MENSAL (pela virada do MTD):")
    print(f"{'MES':16} {'sem':>4} {'VALOR':>14} {'VALOR AA':>13} {'UN':>8} {'UN AA':>8}")
    for nome, sem, v, vaa, u, uaa in meses_fechados():
        var = ((v / vaa - 1) * 100) if vaa else None
        s = f"{var:+.1f}%" if var is not None else "  n/d"
        print(f"{nome:16} {sem:>4} {v:>14,.2f} {vaa:>13,.2f} {u:>8,.0f} {uaa:>8,.0f}  {s}")
    n, d = ultima_semana()
    if d is not None:
        f, e = separa_operacao(d)
        print(f"\nultima semana completa: {n}")
        print(f"   lojas fisicas: {f['loja_cod'].nunique()} lojas | estoque {f['estoque'].sum():,.0f} un")
        print(f"   e-commerce   : estoque {e['estoque'].sum():,.0f} un")
