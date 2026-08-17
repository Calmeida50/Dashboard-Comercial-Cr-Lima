# -*- coding: utf-8 -*-
"""
atualizar_fort.py — sell out do FORT ATACADISTA (Ever Green).

FONTE: `SELL OUT PRINCIPAIS CLIENTES/SELL OUT FORT ATACADISTA 2026 E 2026/`
  SELL OUT FORT ATACADISTA EVER GREEN 2025.xlsx          (aba DS 2025 ...)
  SELL OUT FORT ATACADISTA JANEIRO A JULHO 2026 ... .xlsx (aba DS ...)

O relatorio do Fort e mais rico que o dos outros clientes: traz LOJA, MES,
PRODUTO, venda em R$ e Qtd, o MESMO periodo do ano anterior ja calculado, e
ainda ESTOQUE por loja/produto. Colunas relevantes:
    Fornecedor | (cod) | Bandeira | Loja | (cidade) | Mes | Produto | (desc) |
    Part. Venda | R$ Venda | R$ Venda AA | % Cresc | Qtd Venda | Qtd Venda AA |
    ... | Qtd Estoque | Dias Estoque

ARMADILHAS:
  - As duas primeiras linhas sao TOTAIS (Bandeira 'Total' / vazia). Entram em
    dobro se nao forem descartadas.
  - O cabecalho tem celulas mescladas: a descricao do produto vem em
    "Unnamed: 7" e o nome da loja em "Unnamed: 4".
  - `Mes` vem como "Jan/2025".
  - O arquivo de 2026 ja traz o AA (2025); usamos ELE para a comparacao, em vez
    de cruzar os dois arquivos — e o numero que o proprio cliente enxerga.

Grava `sellout_fort` no DADOS_EMBEDDED.

Uso:
    python3 atualizar_fort.py --simular
    python3 atualizar_fort.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
PASTA = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES/"
    "SELL OUT FORT ATACADISTA 2026 E 2026"
)
MES3 = {"JAN": 0, "FEV": 1, "MAR": 2, "ABR": 3, "MAI": 4, "JUN": 5,
        "JUL": 6, "AGO": 7, "SET": 8, "OUT": 9, "NOV": 10, "DEZ": 11}
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).upper()
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def num(v):
    n = pd.to_numeric(v, errors="coerce")
    return 0.0 if pd.isna(n) else float(n)


def ler(path):
    """[(ano, mes_idx, loja, cidade, cod_prod, produto, val, val_aa, qtd, qtd_aa, est)]"""
    x = pd.ExcelFile(path)
    d = pd.read_excel(path, sheet_name=x.sheet_names[0])
    cols = list(d.columns)
    # a descricao do produto e o nome da loja vem em colunas sem nome, logo
    # DEPOIS das colunas 'Produto' e 'Loja'
    iProd = cols.index("Produto") if "Produto" in cols else None
    iLoja = cols.index("Loja") if "Loja" in cols else None
    cDesc = cols[iProd + 1] if iProd is not None and iProd + 1 < len(cols) else None
    cCid = cols[iLoja + 1] if iLoja is not None and iLoja + 1 < len(cols) else None
    cEst = next((c for c in cols if norm(c).startswith("QTD ESTOQUE")), None)
    out = []
    for _, r in d.iterrows():
        mes = str(r.get("Mes") or "").strip()
        if not mes or mes.lower() == "nan":
            continue                      # linhas de Total
        if norm(r.get("Bandeira")) in ("TOTAL", "", "NAN"):
            continue
        m = re.match(r"([A-Za-z]{3})/(\d{4})", mes)
        if not m:
            continue
        mi = MES3.get(norm(m.group(1)))
        if mi is None:
            continue
        out.append((int(m.group(2)), mi,
                    str(r.get("Loja") or "").strip(),
                    str(r.get(cCid) or "").strip() if cCid else "",
                    str(r.get("Produto") or "").strip(),
                    str(r.get(cDesc) or "").strip() if cDesc else "",
                    num(r.get("R$ Venda")), num(r.get("R$ Venda AA")),
                    num(r.get("Qtd Venda")), num(r.get("Qtd Venda AA")),
                    num(r.get(cEst)) if cEst else 0))
    return out


def main():
    simular = "--simular" in sys.argv
    print("=" * 74)
    print("  FORT ATACADISTA — EVER GREEN%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    if not os.path.isdir(PASTA):
        print("pasta nao encontrada:\n  %s" % PASTA)
        return 1

    linhas = []
    for p in sorted(glob.glob(os.path.join(PASTA, "*.xls*"))):
        if os.path.basename(p).startswith("~$"):
            continue
        l = ler(p)
        anos = sorted({x[0] for x in l})
        print("  %-56s %5d linhas · %s" % (os.path.basename(p)[:56], len(l),
                                           "/".join(str(a) for a in anos)))
        linhas += l
    if not linhas:
        print("nada lido.")
        return 1

    ano_atual = max(x[0] for x in linhas)
    ano_ant = ano_atual - 1
    # o arquivo do ano corrente ja traz o AA; o de 2025 serve de reserva
    prods, lojas_mes, nomes = {}, {}, {}
    # detalhe POR LOJA: o relatorio do Fort tem loja, e sao so 8 — cabe no
    # index sem inflar. {loja: {cidade, val{mes}, val_aa{mes}, qtd, est, prods}}
    porloja = {}
    for ano, mi, loja, cid, cod, desc, v, vaa, q, qaa, est in linhas:
        if ano != ano_atual:
            continue
        nomes[cod] = desc
        p = prods.setdefault(cod, {"cod": cod, "nome": desc,
                                   "val": {}, "val_aa": {}, "qtd": {}, "qtd_aa": {},
                                   "lojas": {}, "est": 0})
        a = ABREV[mi]
        p["val"][a] = round(p["val"].get(a, 0) + v, 2)
        p["val_aa"][a] = round(p["val_aa"].get(a, 0) + vaa, 2)
        p["qtd"][a] = int(p["qtd"].get(a, 0) + q)
        p["qtd_aa"][a] = int(p["qtd_aa"].get(a, 0) + qaa)
        if v > 0:
            p["lojas"].setdefault(a, set()).add(loja)
        p["est"] += est
        lojas_mes.setdefault(a, set()).add(loja)
        L = porloja.setdefault(loja, {"loja": loja, "cidade": cid,
                                      "val": {}, "val_aa": {}, "qtd": {},
                                      "est": 0, "prods": {}})
        if cid and not L["cidade"]:
            L["cidade"] = cid
        L["val"][a] = round(L["val"].get(a, 0) + v, 2)
        L["val_aa"][a] = round(L["val_aa"].get(a, 0) + vaa, 2)
        L["qtd"][a] = int(L["qtd"].get(a, 0) + q)
        L["est"] += est
        pr = L["prods"].setdefault(cod, {"nome": desc, "val": 0, "val_aa": 0,
                                         "qtd": 0, "est": 0})
        pr["val"] = round(pr["val"] + v, 2)
        pr["val_aa"] = round(pr["val_aa"] + vaa, 2)
        pr["qtd"] += int(q)
        pr["est"] += int(est)

    # o ano anterior COMPLETO, do outro arquivo (para a visao de 2025 cheio)
    ant = {}
    for ano, mi, loja, cid, cod, desc, v, vaa, q, qaa, est in linhas:
        if ano != ano_ant:
            continue
        ant.setdefault(cod, {})[ABREV[mi]] = round(
            ant.get(cod, {}).get(ABREV[mi], 0) + v, 2)

    saida = []
    for cod, p in prods.items():
        saida.append({
            "cod": cod, "nome": p["nome"],
            "val": p["val"], "val_aa": p["val_aa"],
            "qtd": p["qtd"], "qtd_aa": p["qtd_aa"],
            "lojas": {m: len(s) for m, s in p["lojas"].items()},
            "estoque": int(p["est"]),
            "val25_cheio": ant.get(cod, {}),
            "tot": round(sum(p["val"].values()), 2),
            "tot_aa": round(sum(p["val_aa"].values()), 2),
            "tot_qtd": sum(p["qtd"].values()),
            "tot_qtd_aa": sum(p["qtd_aa"].values())})
    saida.sort(key=lambda x: -x["tot"])

    meses = sorted({m for p in saida for m in p["val"]}, key=ABREV.index)
    lojas = []
    for L in porloja.values():
        lojas.append({"loja": L["loja"], "cidade": L["cidade"],
                      "val": L["val"], "val_aa": L["val_aa"], "qtd": L["qtd"],
                      "estoque": int(L["est"]),
                      "tot": round(sum(L["val"].values()), 2),
                      "tot_aa": round(sum(L["val_aa"].values()), 2),
                      "tot_qtd": sum(L["qtd"].values()),
                      "produtos": sorted(
                          [{"nome": v2["nome"], "val": v2["val"],
                            "val_aa": v2["val_aa"], "qtd": v2["qtd"],
                            "estoque": v2["est"]} for v2 in L["prods"].values()],
                          key=lambda z: -z["val"])})
    lojas.sort(key=lambda z: -z["tot"])

    bloco = {"ano": ano_atual, "meses": meses, "lojas": lojas,
             "lojas_mes": {m: len(s) for m, s in lojas_mes.items()},
             "n_lojas": len(set().union(*lojas_mes.values())) if lojas_mes else 0,
             "produtos": saida,
             "atualizado_em": datetime.date.today().isoformat()}

    tot = sum(p["tot"] for p in saida)
    tot_aa = sum(p["tot_aa"] for p in saida)
    print()
    print("  %d produtos · %d lojas · %s" % (len(saida), bloco["n_lojas"],
                                             "-".join(meses)))
    print("  por loja:")
    for L in lojas:
        var = ((L["tot"] / L["tot_aa"] - 1) * 100) if L["tot_aa"] else None
        print("     %-26s R$ %10s  %s  %d itens"
              % ((L["cidade"] or L["loja"])[:26],
                 format(round(L["tot"]), ",d").replace(",", "."),
                 ("%+.1f%%" % var) if var is not None else "novo",
                 len(L["produtos"])))
    print("  venda %d: R$ %s | mesmo periodo %d: R$ %s | %+.1f%%"
          % (ano_atual, format(round(tot), ",d").replace(",", "."),
             ano_ant, format(round(tot_aa), ",d").replace(",", "."),
             (tot / tot_aa - 1) * 100 if tot_aa else 0))
    for p in saida[:5]:
        var = ((p["tot"] / p["tot_aa"] - 1) * 100) if p["tot_aa"] else None
        print("     %-42s R$ %10s  %s"
              % (p["nome"][:42], format(round(p["tot"]), ",d").replace(",", "."),
                 ("%+.1f%%" % var) if var is not None else "novo"))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    i = s.index("{", s.index("const DADOS_EMBEDDED ="))
    D, fim = json.JSONDecoder().raw_decode(s[i:])
    D["sellout_fort"] = bloco
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_fort_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(
        s[:i] + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + s[i + fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
