# -*- coding: utf-8 -*-
"""
atualizar_mix_belliz.py — MIX MINIMO DA BELLIZ, por canal.

A Belliz nao tem lista de mix minimo como a Granado. A regra combinada com o
Cristiano em 20/08/2026: o mix minimo de cada canal sao os **80 SKUs que mais
faturam naquele canal DENTRO DA REGIAO** — o proprio mercado diz o que e
essencial, em vez de uma lista definida a priori.

Por que regional e nao nacional: o que vende em farmacia no Nordeste nao e o
que vende no Rio Grande do Sul. Com o ranking da regiao, a conversa com o
cliente fica defensavel em dois niveis — e o que mais vende no canal DELE e
na regiao DELE.

FONTES (pasta `RELATORIOS BELLIZ` no Drive):
  RANKING ... <CANAL> .xlsx     Item ("2105 - PACK COM 2 ESCOVAS") | Rank |
                                Faturamento | Quantidade
      ATENCAO: os nomes dos arquivos variam ("RANKING BELLIZ FARMA",
      "RANKING CANAL ALIMENTAR BELLIZ", e ha um "RANKIMG" com erro de
      digitacao). Por isso o canal e identificado pelo CONTEUDO — o nome da
      coluna "Rank <Canal>" — e nao pelo nome do arquivo.
  FATURAMENTO BELLIZ 2026 POR PRODUTO E CLIENTE.xlsx
      Cabecalho na linha 2. Cliente | NomeCliente | Canal | Familia | Item |
      Descricao | Primeira Positivacao | pares (Fat, Qtd) por mes.
      A linha "Totals" e descartada.
      O CANAL VEM DA PROPRIA BELLIZ — nao depende da nossa carteira.

Grava `MIX_BELLIZ` no index.html.

Uso:
    python3 atualizar_mix_belliz.py --simular
    python3 atualizar_mix_belliz.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
PASTA = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/RELATORIOS BELLIZ"
)
TOP_N = int(os.environ.get("BELLIZ_TOPN", "80"))
CANAIS = ["farma", "alimentar", "perfumaria", "indireto"]


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).upper()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def cod_item(v):
    """'2105 - PACK COM 2 ESCOVAS' -> '2105'  |  2105.0 -> '2105'"""
    s = str(v).strip()
    if " - " in s:
        s = s.split(" - ")[0]
    s = re.sub(r"\.0$", "", s.strip())
    return re.sub(r"\D", "", s)


def desc_item(v):
    s = str(v).strip()
    return s.split(" - ", 1)[1].strip() if " - " in s else s


def ler_rankings():
    """{canal: [ {cod, nome, rank, fat, qtd} ]} — os TOP_N de cada canal.

    O canal sai do NOME DA COLUNA ("Rank Farma"), nao do nome do arquivo:
    os arquivos tem nomes irregulares e um deles esta escrito "RANKIMG".
    """
    out = {}
    for p in sorted(glob.glob(os.path.join(PASTA, "*.xls*"))):
        b = os.path.basename(p)
        if b.startswith("~$") or "RANK" not in norm(b):
            continue
        d = _ler_excel(p)
        cR = next((c for c in d.columns if norm(c).startswith("RANK ")), None)
        cF = next((c for c in d.columns if norm(c).startswith("FATURAMENTO")), None)
        cQ = next((c for c in d.columns if norm(c).startswith("QUANTIDADE")), None)
        cI = next((c for c in d.columns if norm(c) == "ITEM"), None)
        if not cR or not cI:
            print("  ! %s: sem coluna Rank/Item" % b[:44])
            continue
        canal = norm(cR).replace("RANK ", "").lower()
        d = d[d[cI].notna()].copy()
        d["_r"] = pd.to_numeric(d[cR], errors="coerce")
        d = d.dropna(subset=["_r"]).sort_values("_r")
        itens = []
        for _, r in d.head(TOP_N).iterrows():
            c = cod_item(r[cI])
            if not c:
                continue
            itens.append({"cod": c, "nome": desc_item(r[cI]),
                          "rank": int(r["_r"]),
                          "fat": round(float(pd.to_numeric(r[cF], errors="coerce") or 0), 2) if cF else 0,
                          "qtd": int(pd.to_numeric(r[cQ], errors="coerce") or 0) if cQ else 0})
        out[canal] = itens
        tot = pd.to_numeric(d[cF], errors="coerce").fillna(0).sum() if cF else 0
        topf = sum(i["fat"] for i in itens)
        print("  %-12s %4d SKUs no ranking · top %d = R$ %s (%.0f%% do canal)"
              % (canal, len(d), len(itens),
                 format(round(topf), ",d").replace(",", "."),
                 topf / tot * 100 if tot else 0))
    return out


def ler_faturamento():
    """{(canal, cliente): {cod: valor}} + nome e total por cliente"""
    p = None
    for x in glob.glob(os.path.join(PASTA, "*.xls*")):
        b = norm(os.path.basename(x))
        if b.startswith("~$") or "FATURAMENTO" not in b:
            continue
        if "2026" in b:
            p = x
    if not p:
        return None, None
    d = _ler_excel(p, header=1)
    cols = list(d.columns)
    need = ["Cliente", "NomeCliente", "Canal", "Item"]
    if any(n not in cols for n in need):
        print("  ! o faturamento precisa das colunas %s" % need)
        print("    encontrado: %s" % cols[:8])
        return None, None
    cF = [c for c in cols if str(c).startswith("Fat")]
    d = d[d["Cliente"].notna()].copy()
    d = d[d["Cliente"].astype(str).str.strip().str.upper() != "TOTALS"]
    d["_v"] = d[cF].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    d["_cod"] = d["Item"].map(cod_item)

    compras, info = {}, {}
    for _, r in d.iterrows():
        cli = str(r["Cliente"]).strip()
        cli = re.sub(r"\.0$", "", cli)
        canal = norm(r["Canal"]).lower()
        k = (canal, cli)
        info.setdefault(k, {"nome": str(r["NomeCliente"]).strip(), "tot": 0.0})
        info[k]["tot"] += float(r["_v"])
        if r["_v"] > 0 and r["_cod"]:
            compras.setdefault(k, {})[r["_cod"]] = \
                compras.get(k, {}).get(r["_cod"], 0) + float(r["_v"])
    print("  faturamento: %s" % os.path.basename(p)[:52])
    print("  %d relacoes canal-cliente · %d itens distintos"
          % (len(info), d["_cod"].nunique()))
    return compras, info


def main():
    simular = "--simular" in sys.argv
    print("=" * 74)
    print("  MIX MINIMO BELLIZ — top %d por canal%s"
          % (TOP_N, "  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    if not os.path.isdir(PASTA):
        print("pasta nao encontrada:\n  %s" % PASTA)
        return 1

    rk = ler_rankings()
    if not rk:
        print("nenhum ranking lido.")
        return 1
    print()
    compras, info = ler_faturamento()
    if compras is None:
        return 1

    out = {"atualizado_em": datetime.date.today().isoformat(),
           "top_n": TOP_N, "canais": {}}
    for canal, itens in rk.items():
        if canal not in CANAIS:
            continue
        cods = {i["cod"] for i in itens}
        clientes = []
        for (cn, cli), d in info.items():
            if cn != canal or d["tot"] <= 0:
                continue
            comp = compras.get((cn, cli), {})
            tem = sorted(cods & set(comp))
            falta = sorted(cods - set(tem))
            clientes.append({"cod": cli, "nome": d["nome"],
                             "v26": round(d["tot"], 2),
                             "tem": tem, "falta": falta})
        clientes.sort(key=lambda c: -c["v26"])
        out["canais"][canal] = {"itens": itens, "clientes": clientes}
        comp = sum(1 for c in clientes if not c["falta"])
        med = (sum(len(c["falta"]) for c in clientes) / len(clientes)) if clientes else 0
        print()
        print("  CANAL %-11s %d itens · %d clientes · %d com o mix completo · "
              "falta em media %.1f"
              % (canal.upper(), len(itens), len(clientes), comp, med))
        for c in clientes[:5]:
            print("     %-44s R$ %10s  tem %2d  falta %2d"
                  % (c["nome"][:44], format(round(c["v26"]), ",d").replace(",", "."),
                     len(c["tem"]), len(c["falta"])))

    if simular:
        tam = len(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        print("\ntamanho do bloco: %.2f MB" % (tam / 1024 / 1024))
        print("SIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    # `var` + window: `const` no topo de um script fica no escopo lexical
    # global, que e compartilhado, mas essa sutileza ja custou uma sessao de
    # depuracao (20/08/2026 — a tela nao via MIX_BELLIZ). Com window nao ha
    # duvida: qualquer script enxerga.
    novo = ("var MIX_BELLIZ = " + json.dumps(out, ensure_ascii=False,
                                             separators=(",", ":")) +
            "; window.MIX_BELLIZ = MIX_BELLIZ;")
    marca = "var MIX_BELLIZ = "
    if marca in s:
        i = s.index(marca); j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        alvo = "const MIX_MINIMO = "
        i = s.index(alvo)
        s = s[:i] + novo + "\n" + s[i:]
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_mixbelliz_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
