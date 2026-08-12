#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_renner.py — grava o bloco `sellout_renner` no index.html.

Estrutura gravada:
  periodo_semana     numero da semana mais recente
  meses[]            {mes, semana, val, val_aa, un, un_aa}
  resumo             {venda_sem, venda_sem_aa, ytd, ytd_aa, estoque,
                      transito, ruptura_pct, ecom_ytd, ecom_pct}
  produtos[]         {cod, nome, so_ecom, vl_sem, vl_sem_aa, vl_mtd, vl_ytd,
                      un_sem, un_sem_aa, un_mtd, un_ytd,
                      lojas_com, lojas_rup, rup_pct}
  lojas[]            {cod, nome, oficial, estoque[], total, zerados, rup_pct}
  skus_ordem[]       codigos na ordem em que as colunas devem aparecer
  ecom               {produtos[], semanal[], por_posicao[]}
  extras             {lojas, ytd}   as 22 que receberam por engano
  sem_historico[]    lojas oficiais que nunca receberam produto

SO LEITURA do Drive — nao mexe em nenhum outro bloco.
"""
import os, re, sys, json, shutil, datetime
import pandas as pd
import renner as R

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
NOMES_MES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


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


def serie_semanal():
    """[(semana, mes, posicao_no_mes, ecom, lojas)] das 31 semanas"""
    out = []
    mes_idx = 0
    pos = 0
    ant = None
    for n, p in R.semanas():
        d = R.ler(p)
        of, ex, ec = R.grupos(d)
        mtd = d["vl_mtd"].sum()
        if ant is not None and mtd < ant:
            mes_idx += 1
            pos = 0
        pos += 1
        ant = mtd
        out.append({
            "semana": n,
            "mes": NOMES_MES[mes_idx] if mes_idx < 12 else "?",
            "pos": pos,
            "ecom": round(float(ec["vl_sem"].sum()), 2),
            "lojas": round(float(of["vl_sem"].sum() + ex["vl_sem"].sum()), 2),
        })
    return out


def montar():
    sem, d = R.ultima_semana()
    of, ex, ec = R.grupos(d)
    ofp = of[of["cod"].isin(R.PERFUME_LOJA)]
    exp_ = ex[ex["cod"].isin(R.PERFUME_LOJA)]

    # --- meses: TRES series.
    # Em 2025 nao havia perfume na Renner, entao o total mistura duas
    # operacoes: o perfume que entrou (sem base de comparacao) e a linha
    # antiga que encolheu. Somados, o valor sobe 352% e a unidade cai 36%.
    def _serie(flag):
        return [{"mes": nome, "semana": s, "val": round(v, 2),
                 "val_aa": round(vaa, 2), "un": int(u), "un_aa": int(uaa)}
                for nome, s, v, vaa, u, uaa in R.meses_fechados(apenas_perfume=flag)]

    meses = _serie(None)
    meses_perfume = _serie(True)
    meses_linha_antiga = _serie(False)

    # --- produtos
    g = d.groupby("cod").agg(
        item=("item", "first"),
        vl_sem=("vl_sem", "sum"), vl_sem_aa=("vl_sem_aa", "sum"),
        vl_mtd=("vl_mtd", "sum"), vl_ytd=("vl_ytd", "sum"),
        vl_ytd_aa=("vl_ytd_aa", "sum"),
        un_sem=("un_sem", "sum"), un_sem_aa=("un_sem_aa", "sum"),
        un_mtd=("un_mtd", "sum"), un_ytd=("un_ytd", "sum")).to_dict("index")

    n_lojas = ofp["loja_cod"].nunique()
    est_por_sku = ofp.pivot_table(index="loja_cod", columns="cod",
                                  values="estoque", aggfunc="sum", fill_value=0)
    produtos = []
    for cod, nome in R.MIX_PERFUME.items():
        r = g.get(cod, {})
        so_ecom = cod in R.PERFUME_SO_ECOM
        com = rup = 0
        if not so_ecom and cod in est_por_sku.columns:
            com = int((est_por_sku[cod] > 0).sum())
            rup = n_lojas - com
        produtos.append({
            "cod": cod, "nome": nome, "so_ecom": so_ecom,
            "vl_sem": round(float(r.get("vl_sem", 0)), 2),
            "vl_sem_aa": round(float(r.get("vl_sem_aa", 0)), 2),
            "vl_mtd": round(float(r.get("vl_mtd", 0)), 2),
            "vl_ytd": round(float(r.get("vl_ytd", 0)), 2),
            "un_sem": int(r.get("un_sem", 0)),
            "un_sem_aa": int(r.get("un_sem_aa", 0)),
            "un_mtd": int(r.get("un_mtd", 0)),
            "un_ytd": int(r.get("un_ytd", 0)),
            "lojas_com": com, "lojas_rup": rup,
            "rup_pct": round(rup / n_lojas * 100, 1) if n_lojas and not so_ecom else None,
        })
    produtos.sort(key=lambda x: (x["so_ecom"], -x["vl_ytd"]))
    skus_ordem = [p["cod"] for p in produtos if not p["so_ecom"]]

    # --- lojas
    piv = ofp.pivot_table(index=["loja_cod", "loja_nome"], columns="cod",
                          values="estoque", aggfunc="sum", fill_value=0)
    for c in skus_ordem:
        if c not in piv.columns:
            piv[c] = 0
    piv = piv[skus_ordem].reset_index()
    lojas = []
    for _, r in piv.iterrows():
        vals = [int(r[c]) for c in skus_ordem]
        zer = sum(1 for v in vals if v <= 0)
        lojas.append({"cod": int(r["loja_cod"]), "nome": r["loja_nome"],
                      "oficial": True, "estoque": vals, "total": sum(vals),
                      "zerados": zer,
                      "rup_pct": round(zer / len(skus_ordem) * 100, 1)})
    lojas.sort(key=lambda x: (-x["zerados"], x["cod"]))

    # --- e-commerce
    ge = ec.groupby("cod").agg(
        est=("estoque", "sum"), tr=("transito", "sum"),
        vs=("vl_sem", "sum"), vm=("vl_mtd", "sum"),
        vy=("vl_ytd", "sum")).to_dict("index")
    ecom_prod = []
    for cod, nome in R.MIX_PERFUME.items():
        r = ge.get(cod, {})
        ecom_prod.append({"cod": cod, "nome": nome,
                          "so_ecom": cod in R.PERFUME_SO_ECOM,
                          "estoque": int(r.get("est", 0)),
                          "transito": int(r.get("tr", 0)),
                          "vl_sem": round(float(r.get("vs", 0)), 2),
                          "vl_mtd": round(float(r.get("vm", 0)), 2),
                          "vl_ytd": round(float(r.get("vy", 0)), 2)})
    ecom_prod.sort(key=lambda x: (x["so_ecom"], -x["vl_ytd"]))

    semanal = serie_semanal()
    por_pos = {}
    for s in semanal:
        a = por_pos.setdefault(s["pos"], {"n": 0, "ecom": 0.0, "lojas": 0.0})
        a["n"] += 1
        a["ecom"] += s["ecom"]
        a["lojas"] += s["lojas"]
    posicao = [{"pos": k, "n": v["n"],
                "ecom_medio": round(v["ecom"] / v["n"], 2),
                "lojas_medio": round(v["lojas"] / v["n"], 2)}
               for k, v in sorted(por_pos.items())]

    # --- resumo
    ytd_tot = float(ofp["vl_ytd"].sum() + exp_["vl_ytd"].sum() + ec["vl_ytd"].sum())
    ytd_aa = float(ofp["vl_ytd_aa"].sum() + exp_["vl_ytd_aa"].sum() + ec["vl_ytd_aa"].sum())
    sem_tot = float(ofp["vl_sem"].sum() + exp_["vl_sem"].sum() + ec["vl_sem"].sum())
    sem_aa = float(ofp["vl_sem_aa"].sum() + exp_["vl_sem_aa"].sum() + ec["vl_sem_aa"].sum())
    pares = len(ofp)
    zer = int((ofp["estoque"] <= 0).sum())

    return {
        "periodo_semana": sem,
        "atualizado": datetime.date.today().isoformat(),
        "meses": meses,
        "meses_perfume": meses_perfume,
        "meses_linha_antiga": meses_linha_antiga,
        "resumo": {
            "venda_sem": round(sem_tot, 2), "venda_sem_aa": round(sem_aa, 2),
            "ytd": round(ytd_tot, 2), "ytd_aa": round(ytd_aa, 2),
            "estoque": int(ofp["estoque"].sum()),
            "transito": int(ofp["transito"].sum()),
            "ruptura_pct": round(zer / pares * 100, 1) if pares else 0,
            "lojas_ativas": int(n_lojas),
            "ecom_ytd": round(float(ec["vl_ytd"].sum()), 2),
            "ecom_pct": round(float(ec["vl_ytd"].sum()) / ytd_tot * 100, 1) if ytd_tot else 0,
        },
        "produtos": produtos,
        "skus_ordem": skus_ordem,
        "lojas": lojas,
        "ecom": {"produtos": ecom_prod, "semanal": semanal, "por_posicao": posicao},
        "extras": {"lojas": int(exp_["loja_cod"].nunique()),
                   "ytd": round(float(exp_["vl_ytd"].sum()), 2)},
        "sem_historico": sorted(R.LOJAS_SEM_HISTORICO),
    }


def main():
    simular = "--simular" in sys.argv
    print("=" * 70)
    print("  SELL OUT RENNER%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 70)
    b = montar()
    r = b["resumo"]
    print("  semana %s | %d lojas ativas" % (b["periodo_semana"], r["lojas_ativas"]))
    print("  venda semana %s (AA %s)"
          % ("{:,.2f}".format(r["venda_sem"]), "{:,.2f}".format(r["venda_sem_aa"])))
    print("  YTD %s (AA %s)  crescimento %.1f%%"
          % ("{:,.2f}".format(r["ytd"]), "{:,.2f}".format(r["ytd_aa"]),
             (r["ytd"] / r["ytd_aa"] - 1) * 100 if r["ytd_aa"] else 0))
    print("  estoque %s un | transito %s un | ruptura %.1f%%"
          % ("{:,}".format(r["estoque"]), "{:,}".format(r["transito"]),
             r["ruptura_pct"]))
    print("  e-commerce %s (%.1f%% do total)"
          % ("{:,.2f}".format(r["ecom_ytd"]), r["ecom_pct"]))
    print("  meses reconstruidos: %d | produtos: %d | lojas: %d"
          % (len(b["meses"]), len(b["produtos"]), len(b["lojas"])))
    print("\n  e-commerce por posicao no mes:")
    for p in b["ecom"]["por_posicao"]:
        print("     %da semana (n=%d): e-com %s | lojas %s"
              % (p["pos"], p["n"], "{:,.2f}".format(p["ecom_medio"]),
                 "{:,.2f}".format(p["lojas_medio"])))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    h, ini, fim, D = carregar()
    D["sellout_renner"] = b
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_renner_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open(INDEX, "w", encoding="utf-8").write(h[:ini] + txt + h[fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
