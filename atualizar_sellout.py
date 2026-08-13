#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_sellout.py — recalcula o bloco `sellout_sao_joao` a partir dos
arquivos do Drive e grava no index.html.

Regras (ROTEIRO_AUTOMACAO.md, etapa 2):
  1. descartar total geral (sem filial) E subtotais por loja (sem produto)
  2. devolucoes EXCLUIDAS (valor negativo ignorado)
  3. SEMPRE valor liquido, mesmo quando existe Vl Bruto

Recalcula: mensal_2025, mensal_2026, val26, val25_ytd, qtd26, qtd25_ytd,
           n_meses, top_lojas, produtos (val/qtd).
PRESERVA:  cobertura_mensal (dentro de produtos) e avg3m — dependem de cruzar
           com a pasta de estoque, tratados em sub-etapa separada.

Uso:
    python3 atualizar_sellout.py --simular
    python3 atualizar_sellout.py
"""
import os, re, sys, json, glob, shutil, datetime
import pandas as pd
import coletar_faturamento as C
import conferir_sellout as S

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
EMPRESAS = S.EMPRESAS
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def detalhe(path):
    """devolve o DataFrame ja limpo pelas regras 1 e 2, com colunas padrao"""
    d = C._abrir_excel(path)
    # ATENCAO: varios arquivos tem Cod. Filial E Desc_Filial. Pegar a primeira
    # coluna com "FILIAL" traz o CODIGO e arruina o ranking de lojas.
    # Sempre excluir as colunas de codigo.
    fil = next((c for c in d.columns if "FILIAL" in C.norm(c)
                and "COD" not in C.norm(c)), None)
    prod = next((c for c in d.columns if "PRODUTO" in C.norm(c)
                 and "COD" not in C.norm(c)), None)
    val = next((c for c in d.columns if "LIQUID" in C.norm(c)), None)
    qtd = next((c for c in d.columns if "GIRO" in C.norm(c)), None)
    if val is None or fil is None or prod is None:
        return None
    d = d[d[fil].notna() & d[prod].notna()].copy()
    # alguns arquivos rotulam a linha de total como "Total" na propria filial
    d = d[~d[fil].astype(str).str.strip().str.upper().isin(["TOTAL", "TOTAL GERAL"])]
    d["_v"] = pd.to_numeric(d[val], errors="coerce").fillna(0)
    d["_q"] = pd.to_numeric(d[qtd], errors="coerce").fillna(0) if qtd else 0
    d = d[d["_v"] > 0]
    d["_loja"] = d[fil].astype(str).str.strip()
    d["_prod"] = d[prod].astype(str).str.strip()
    return d[["_loja", "_prod", "_v", "_q"]]


def coletar_empresa(emp):
    """le todos os meses disponiveis dos dois anos para uma empresa"""
    dados = {"25": {}, "26": {}}
    for ano2 in ("25", "26"):
        for k, mes in enumerate(MESES):
            arqs = S.achar(emp, mes, ano2)
            if not arqs:
                continue
            df = detalhe(arqs[0])
            if df is None or df.empty:
                continue
            dados[ano2][ABREV[k]] = {
                "val": float(df["_v"].sum()),
                "qtd": int(df["_q"].sum()),
                "lojas": df.groupby("_loja")["_v"].sum().to_dict(),
                "prod_v": df.groupby("_prod")["_v"].sum().to_dict(),
                "prod_q": df.groupby("_prod")["_q"].sum().to_dict(),
                # POSITIVACAO CALCULADA: quantas LOJAS distintas venderam o SKU
                # no mes. A Sao Joao nao manda esse dado; aqui ele e derivado do
                # detalhe por loja. NAO e o mesmo que a positivacao da Dartora,
                # que conta CLIENTES. Rotular sempre como "lojas".
                "prod_lojas": df.groupby("_prod")["_loja"].nunique().to_dict(),
                "lojas_ativas": int(df["_loja"].nunique()),
            }
    return dados


def montar(emp, dados, antigo):
    """monta o bloco novo preservando cobertura_mensal e avg3m"""
    m26 = dados["26"]
    m25 = dados["25"]
    if not m26:
        return None, "sem arquivos de 2026"
    meses26 = [a for a in ABREV if a in m26]
    n = len(meses26)
    # YTD de 2025 sempre com o MESMO numero de meses, para comparacao justa
    meses25 = [a for a in ABREV if a in m25][:n]

    novo = dict(antigo)   # preserva o que nao for recalculado
    novo["mensal_2026"] = {a: round(m26[a]["val"], 2) for a in meses26}
    novo["mensal_2025"] = {a: round(m25[a]["val"], 2) for a in meses25}
    novo["val26"] = round(sum(m26[a]["val"] for a in meses26), 2)
    novo["val25_ytd"] = round(sum(m25[a]["val"] for a in meses25), 2)
    novo["qtd26"] = int(sum(m26[a]["qtd"] for a in meses26))
    novo["qtd25_ytd"] = int(sum(m25[a]["qtd"] for a in meses25))
    novo["n_meses"] = n
    # lojas ativas por mes (quantas venderam algo). Metrica de capilaridade,
    # equivalente da Sao Joao a positivacao da Dartora — mas conta LOJAS.
    novo["lojas_ativas_2026"] = {a: m26[a]["lojas_ativas"] for a in meses26}
    novo["lojas_ativas_2025"] = {a: m25[a]["lojas_ativas"] for a in meses25}

    # lojas: uniao dos dois anos
    lj26, lj25 = {}, {}
    for a in meses26:
        for k, v in m26[a]["lojas"].items():
            lj26[k] = lj26.get(k, 0.0) + v
    for a in meses25:
        for k, v in m25[a]["lojas"].items():
            lj25[k] = lj25.get(k, 0.0) + v
    novo["top_lojas"] = sorted(
        [{"nome": k, "val26": round(lj26.get(k, 0.0), 2), "val25": round(lj25.get(k, 0.0), 2)}
         for k in set(lj26) | set(lj25)],
        key=lambda x: -x["val26"])

    # ── VENDA MEDIA MENSAL (avg3m): 3 ULTIMOS MESES FECHADOS ──────────────
    # Alimenta a cobertura da tela de estoque: cobertura = estoque / avg3m * 30.
    # Ate 13/08/2026 estava CONGELADO em abr-jun — nenhum script calculava, os
    # tres que citavam o campo apenas preservavam (mesmo caso do
    # cobertura_mensal). Agora rola sozinho quando o mes fecha.
    # O MES CORRENTE FICA DE FORA, mesmo que ja tenha arquivo salvo: mes
    # parcial derrubaria a media e a cobertura pareceria melhor do que e.
    hoje = datetime.date.today()
    corrente = ABREV[hoje.month - 1] if hoje.year == 2026 else None
    fechados = [a for a in meses26 if a != corrente]
    ult3 = fechados[-3:]
    avg = {}
    if ult3:
        for a in ult3:
            for k, v in m26[a]["prod_q"].items():
                avg[k] = avg.get(k, 0) + v
        avg = {k: round(v / len(ult3), 1) for k, v in avg.items() if v}
    novo["avg3m"] = avg
    novo["avg3m_meses"] = ult3
    return novo, (lj26, lj25, m26, m25, meses26, meses25)


def montar_produtos(antigo, m26, m25, meses26, meses25):
    """produtos com val/qtd recalculados, preservando cobertura_mensal"""
    pv26, pq26, pv25, pq25 = {}, {}, {}, {}
    for a in meses26:
        for k, v in m26[a]["prod_v"].items(): pv26[k] = pv26.get(k, 0.0) + v
        for k, v in m26[a]["prod_q"].items(): pq26[k] = pq26.get(k, 0) + v
    for a in meses25:
        for k, v in m25[a]["prod_v"].items(): pv25[k] = pv25.get(k, 0.0) + v
        for k, v in m25[a]["prod_q"].items(): pq25[k] = pq25.get(k, 0) + v

    # cobertura_mensal do bloco antigo, indexada por nome
    cob = {p["nome"]: p["cobertura_mensal"]
           for p in antigo.get("produtos", []) if "cobertura_mensal" in p}

    saida = []
    for nome in set(pv26) | set(pv25):
        item = {"nome": nome,
                "val26": round(pv26.get(nome, 0.0), 2),
                "val25": round(pv25.get(nome, 0.0), 2),
                "qtd26": int(pq26.get(nome, 0)),
                "qtd25": int(pq25.get(nome, 0)),
                # valor e quantidade MES A MES — permite abrir a performance
                # de cada SKU num mes especifico, nao so no acumulado
                "val_2026": {a: round(m26[a]["prod_v"].get(nome, 0.0), 2)
                             for a in meses26 if m26[a]["prod_v"].get(nome)},
                "val_2025": {a: round(m25[a]["prod_v"].get(nome, 0.0), 2)
                             for a in meses25 if m25[a]["prod_v"].get(nome)},
                "qtd_2026": {a: int(m26[a]["prod_q"].get(nome, 0))
                             for a in meses26 if m26[a]["prod_q"].get(nome)},
                "qtd_2025": {a: int(m25[a]["prod_q"].get(nome, 0))
                             for a in meses25 if m25[a]["prod_q"].get(nome)},
                # lojas distintas que venderam o SKU em cada mes
                "lojas_2026": {a: int(m26[a]["prod_lojas"].get(nome, 0))
                               for a in meses26 if m26[a]["prod_lojas"].get(nome)},
                "lojas_2025": {a: int(m25[a]["prod_lojas"].get(nome, 0))
                               for a in meses25 if m25[a]["prod_lojas"].get(nome)}}
        if nome in cob:
            item["cobertura_mensal"] = cob[nome]     # preservado
        saida.append(item)
    return sorted(saida, key=lambda x: -x["val26"])


def carregar():
    h = open(INDEX, encoding="utf-8").read()
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
    return h, i, j + 1, json.loads(h[i:j + 1])


def main():
    simular = "--simular" in sys.argv
    print("=" * 72)
    print("  SELL OUT SAO JOAO — recalculo%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 72)

    h, ini, fim, dados = carregar()
    sj = dados["sellout_sao_joao"]
    mudou = False

    for emp in EMPRESAS:
        antigo = sj.get(emp, {})
        col = coletar_empresa(emp)
        novo, extra = montar(emp, col, antigo)
        if novo is None:
            print("\n%-11s  %s" % (emp, extra))
            continue
        lj26, lj25, m26, m25, meses26, meses25 = extra
        novo["produtos"] = montar_produtos(antigo, m26, m25, meses26, meses25)

        v_antes = antigo.get("val26", 0.0)
        v_depois = novo["val26"]
        dif = v_depois - v_antes
        marca = "" if abs(dif) < 0.05 else "   <-- MUDOU"
        print("\n%-11s val26 %14s -> %14s  (%s meses)%s"
              % (emp, "{:,.2f}".format(v_antes), "{:,.2f}".format(v_depois),
                 novo["n_meses"], marca))
        print("            val25_ytd %10s -> %14s"
              % ("{:,.2f}".format(antigo.get("val25_ytd", 0.0)),
                 "{:,.2f}".format(novo["val25_ytd"])))
        print("            lojas %d | produtos %d | cobertura preservada em %d"
              % (len(novo["top_lojas"]), len(novo["produtos"]),
                 sum(1 for p in novo["produtos"] if "cobertura_mensal" in p)))
        if abs(dif) >= 0.05 or novo != antigo:
            mudou = True
        sj[emp] = novo

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    if not mudou:
        print("\nNada mudou.")
        return 0

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_sellout_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    novo_json = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    open(INDEX, "w", encoding="utf-8").write(h[:ini] + novo_json + h[fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
