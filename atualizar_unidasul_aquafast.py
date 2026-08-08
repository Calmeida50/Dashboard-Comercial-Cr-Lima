#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_unidasul_aquafast.py — incorpora a AQUAFAST ao bloco sellout_unidasul.

REGIMES DIFERENTES DENTRO DO MESMO CLIENTE:
  - GRANADO / PRUDENCE / EVER GREEN: vem num arquivo CONSOLIDADO
    ("SELL OUT UNIDASUL .xlsx"), uma coluna por mes fechado. O dashboard
    acumula. Historico de 2018 a 2026 ja publicado.
  - AQUAFAST: um arquivo POR MES ("SELL OUT UNIDASUL AQUAFAST <MES> 26.xlsx").
    So existe 2026, de janeiro a julho. NAO tem base de 2025.

Layout AQUAFAST (cabecalho em 2 linhas):
    linha 0: Categoria | Emb. | 2026 | Jul | (vazio)
    linha 1:           |      | Codigo | Qtd Vda | Vlr Vda
    linha 2+: dados

Por nao ter 2025, a AQUAFAST fica MARCADA como sem base comparativa — o KPI
consolidado da tela nao deve usar o crescimento dela.
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]
SIGLA = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def ler(path):
    """devolve (valor, qtd, [(produto, qtd, valor)])"""
    d = pd.read_excel(path, header=1)
    cQ = next((c for c in d.columns if "QTD" in norm(c)), None)
    cV = next((c for c in d.columns if "VLR" in norm(c)), None)
    cP = d.columns[2]                      # coluna do codigo/descricao
    if cV is None:
        return None, None, []
    d = d[d[cP].notna()]
    v = pd.to_numeric(d[cV], errors="coerce").fillna(0)
    q = pd.to_numeric(d[cQ], errors="coerce").fillna(0) if cQ else None
    itens = []
    for _, r in d.iterrows():
        vv = pd.to_numeric(r[cV], errors="coerce")
        qq = pd.to_numeric(r[cQ], errors="coerce") if cQ else 0
        itens.append((str(r[cP]).strip(),
                      0 if pd.isna(qq) else int(qq),
                      0.0 if pd.isna(vv) else float(vv)))
    return float(v.sum()), (int(q.sum()) if q is not None else 0), itens


def main():
    simular = "--simular" in sys.argv
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
    D = json.loads(h[i:j + 1])
    uni = D.setdefault("sellout_unidasul", {})

    print("=" * 68)
    print("  UNIDASUL / AQUAFAST%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 68)

    meses, prods = [], {}
    tv = tq = 0.0
    for k, mes in enumerate(MESES):
        f = [p for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True)
             if "AQUAFAST" in norm(os.path.basename(p))
             and "UNIDASUL" in norm(os.path.basename(p))
             and mes in norm(os.path.basename(p))]
        if not f:
            continue
        v, q, itens = ler(f[0])
        if v is None:
            print("  ! %s: nao foi possivel ler" % mes[:3])
            continue
        # Formato do bloco (confirmado no exportador da tela, linha ~9568):
        #   [num, sigla, VAREJO, ATACADO, TOTAL, q_varejo, q_atacado, q_total]
        # A Unidasul opera VAREJO (lojas fisicas) e ATACADO (equipe externa).
        # Granado, Prudence e Ever Green estao nos DOIS. A AQUAFAST esta
        # APENAS NO VAREJO -> atacado fica zerado.
        meses.append([k + 1, SIGLA[k], round(v, 2), 0.0, round(v, 2), q, 0, q])
        tv += v; tq += q
        for nome, qq, vv in itens:
            a = prods.setdefault(nome, {"q": 0, "v": 0.0})
            a["q"] += qq; a["v"] += vv
        print("  %s  %14s  qtd %8d" % (SIGLA[k], "{:,.2f}".format(v), q))

    if not meses:
        print("nenhum arquivo da AQUAFAST encontrado.")
        return 1

    bloco = {
        "anos": {"2026": {"tv": round(tv, 2), "tq": int(tq), "m": meses}},
        # produtos: mesmo formato dos demais — [varejo, atacado, total, ...]
        # AQUAFAST so tem varejo, entao atacado zerado.
        "prods": {"2026": sorted(
            [{"nome": n, "qtd": a["q"], "val": round(a["v"], 2),
              "val_varejo": round(a["v"], 2), "val_atacado": 0.0,
              "qtd_varejo": a["q"], "qtd_atacado": 0}
             for n, a in prods.items()],
            key=lambda x: -x["val"])},
        # marca usada pela tela: nao ha base de 2025 para comparar
        "sem_base_2025": True,
        "somente_varejo": True,
    }
    antigo = uni.get("AQUAFAST")
    print("\ntotal 2026: %s em %d meses | %d produtos"
          % ("{:,.2f}".format(tv), len(meses), len(prods)))
    print("status: %s" % ("ATUALIZA existente" if antigo else "EMPRESA NOVA no bloco"))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    uni["AQUAFAST"] = bloco
    os.makedirs("_backups", exist_ok=True)
    bkp = "_backups/index.html.bak_aquafast_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("index.html", bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open("index.html", "w", encoding="utf-8").write(h[:i] + txt + h[j + 1:])
    print("\ngravado. backup em %s" % bkp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
