#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_imec.py — valida o sell out da IMEC contra o dashboard.

Layout (3 colunas): DESCPRODUTO CODIGO | Qtd Item | Vlr Venda

ARMADILHA: cada arquivo tem DUAS linhas de totalizacao — uma no TOPO marcada
"Total" e outra no RODAPE sem descricao. Somar tudo triplica o mes.
Aplicar os DOIS criterios: descartar celula "Total" E descricao vazia.

O dashboard tem 4 empresas; a BELLIZ existe nos arquivos e NAO esta publicada.
"""
import os, re, json, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["PRUDENCE", "EVER GREEN", "DEPIMIEL", "GRANADO", "BELLIZ"]
MESES = {"JANEIRO":"JAN","FEVEREIRO":"FEV","MARCO":"MAR","ABRIL":"ABR",
         "MAIO":"MAI","JUNHO":"JUN","JULHO":"JUL","AGOSTO":"AGO",
         "SETEMBRO":"SET","OUTUBRO":"OUT","NOVEMBRO":"NOV","DEZEMBRO":"DEZ"}
# Variantes com erro de digitacao ja vistas no Drive. Sem isso o mes fica
# invisivel e a empresa aparece com um buraco na serie, sem nenhum aviso.
# Ex.: "SELL OUT IMEC BELLIZ FVEREIRO 26.xlsx" (falta o E)
VARIANTES = {"FVEREIRO":"FEV", "FEVERERIO":"FEV", "FEVREIRO":"FEV",
             "JANERIO":"JAN", "MARCO ":"MAR", "ABIL":"ABR",
             "JUHNO":"JUN", "JULO":"JUL", "AGSOTO":"AGO"}
ORDEM = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def arquivos():
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if "IMEC" not in n:
            continue
        emp = next((e for e in EMPRESAS if e in n), None)
        mes = next((v for k, v in MESES.items() if k in n), None)
        if mes is None:
            mes = next((v for k, v in VARIANTES.items() if k in n), None)
            if mes:
                print("  (nome com erro de digitacao aceito: %s)" % os.path.basename(p))
        if emp and mes:
            idx[(emp, mes)] = p
    return idx


def ler(path):
    """devolve (valor, quantidade) sem as linhas de total"""
    d = pd.read_excel(path)
    desc = d.columns[0]
    col = next((c for c in d.columns if "VLR" in norm(c) or "VALOR" in norm(c)), None)
    qtd = next((c for c in d.columns if "QTD" in norm(c) or "QUANT" in norm(c)), None)
    if col is None:
        return None, None
    d = d[d[desc].notna() & (d[desc].astype(str).map(norm) != "TOTAL")]
    v = float(pd.to_numeric(d[col], errors="coerce").fillna(0).sum())
    q = int(pd.to_numeric(d[qtd], errors="coerce").fillna(0).sum()) if qtd else 0
    return v, q


def dashboard_raw():
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
    return h, i, j + 1, json.loads(h[i:j + 1])


def montar():
    """{empresa: bloco no formato do dashboard}"""
    idx = arquivos()
    saida = {}
    prods = {}
    for (emp, mes), p in sorted(idx.items()):
        v, q = ler(p)
        if v is None:
            continue
        b = saida.setdefault(emp, {"total_val": 0.0, "total_qtd": 0, "meses": [], "produtos": []})
        b["meses"].append({"mes": mes, "val": round(v, 2), "qtd": q})
        b["total_val"] += v
        b["total_qtd"] += q
        # produtos acumulados
        d = pd.read_excel(p)
        desc = d.columns[0]
        col = next(c for c in d.columns if "VLR" in norm(c) or "VALOR" in norm(c))
        qtc = next((c for c in d.columns if "QTD" in norm(c)), None)
        d = d[d[desc].notna() & (d[desc].astype(str).map(norm) != "TOTAL")]
        for _, r in d.iterrows():
            nome = str(r[desc]).strip()
            acc = prods.setdefault(emp, {}).setdefault(nome, {"val": 0.0, "qtd": 0})
            # CUIDADO: `NaN or 0` NAO vira 0 em Python — NaN e verdadeiro.
            # Usar pd.isna explicitamente, senao um unico valor vazio
            # contamina o acumulado do produto inteiro.
            vv = pd.to_numeric(r[col], errors="coerce")
            acc["val"] += 0.0 if pd.isna(vv) else float(vv)
            if qtc:
                qv = pd.to_numeric(r[qtc], errors="coerce")
                acc["qtd"] += 0 if pd.isna(qv) else int(qv)
            # abertura mensal: a tela le `meses_val` e `meses_qtd` como LISTAS
            # indexadas pela posicao do mes em `meses` (nao dicionario).
            mm = acc.setdefault("m", {})
            a = mm.setdefault(mes, {"val": 0.0, "qtd": 0})
            a["val"] += 0.0 if pd.isna(vv) else float(vv)
            a["qtd"] += 0 if not qtc or pd.isna(qv) else int(qv)
    for emp, b in saida.items():
        b["meses"].sort(key=lambda x: ORDEM.index(x["mes"]))
        ordem_mes = [x["mes"] for x in b["meses"]]
        b["total_val"] = round(b["total_val"], 2)
        itens = []
        for n, dd in prods.get(emp, {}).items():
            mv = [round(dd.get("m", {}).get(k, {}).get("val", 0.0), 2) for k in ordem_mes]
            mq = [dd.get("m", {}).get(k, {}).get("qtd", 0) for k in ordem_mes]
            itens.append({"nome": n, "val": round(dd["val"], 2), "qtd": dd["qtd"],
                          "val26": round(dd["val"], 2), "qtd26": dd["qtd"],
                          "meses_val": mv, "meses_qtd": mq})
        b["produtos"] = sorted(itens, key=lambda x: -x["val"])
    return saida


def main():
    import shutil, datetime, sys
    simular = "--simular" in sys.argv
    h, ini, fim, D = dashboard_raw()
    antigo = D.get("sellout_imec", {})
    novo = montar()

    print("=" * 70)
    print("  SELL OUT IMEC%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 70)
    ok = div = 0
    for emp in sorted(novo):
        a = antigo.get(emp, {})
        mant = {m["mes"]: m["val"] for m in a.get("meses", [])}
        mnov = {m["mes"]: m["val"] for m in novo[emp]["meses"]}
        novos = [m for m in mnov if m not in mant]
        for m in mant:
            if m in mnov and abs(mnov[m] - mant[m]) > 0.05:
                div += 1
                print("  ! %s %s: %.2f -> %.2f" % (emp, m, mant[m], mnov[m]))
            elif m in mnov:
                ok += 1
        marca = "  << EMPRESA NOVA" if emp not in antigo else ""
        print("\n%-11s total %13s -> %13s  (%d meses)%s"
              % (emp, "{:,.2f}".format(a.get("total_val", 0)),
                 "{:,.2f}".format(novo[emp]["total_val"]),
                 len(novo[emp]["meses"]), marca))
        if novos:
            print("            meses novos: %s" % ", ".join(sorted(novos, key=ORDEM.index)))
        print("            produtos: %d" % len(novo[emp]["produtos"]))

    print("\nmeses que ja existiam: %d conferem, %d divergem" % (ok, div))
    if div:
        print("ABORTADO — ha divergencia em mes ja publicado.")
        return 2
    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    D["sellout_imec"] = novo
    os.makedirs("_backups", exist_ok=True)
    bkp = "_backups/index.html.bak_imec_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("index.html", bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open("index.html", "w", encoding="utf-8").write(h[:ini] + txt + h[fim:])
    print("\ngravado. backup em %s" % bkp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
