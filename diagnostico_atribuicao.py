#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_atribuicao.py — lista os clientes que FATURAM mas nao estao
atribuidos a nenhum vendedor no `clientes_detalhado`.

Motivo: as telas por VENDEDOR (YTD por vendedor, ranking de vendedor,
comissoes) so enxergam o que esta atribuido. Hoje ~R$ 1,46 milhao de
faturamento (2,4%) nao aparece nelas.

Le os arquivos de faturamento do Drive (mesma leitura ja validada em
coletar_faturamento.py) e compara cliente a cliente com o dashboard.

Gera: _backups/clientes_sem_vendedor.xlsx
"""
import os, re, sys, json, glob, unicodedata
import pandas as pd
import coletar_faturamento as C

PROJ = os.path.dirname(os.path.abspath(__file__))


def norm_nome(s):
    """normaliza nome de cliente para casar entre o arquivo e o dashboard.
    Os arquivos trazem o codigo colado — as vezes no INICIO ('54816-C E A ...')
    e as vezes no FIM ('BRAIR LTDA-2350917'). Ambos precisam sair, senao o
    cliente parece novo e o diagnostico acusa falso positivo."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper().strip()
    s = re.sub(r"^\d+\s*[-–]\s*", "", s)          # codigo no inicio
    s = re.sub(r"\s*[-–]\s*\d+\s*$", "", s)       # codigo no fim
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(LTDA|S/?A|SA|ME|EPP|EIRELI|CIA|COMERCIO|DISTRIBUIDORA|"
               r"DISTRIB|DE|DA|DO|E)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # nome que virou so numero = a coluna lida era codigo, nao nome
    return "" if s.isdigit() else s


def dashboard():
    h = open(os.path.join(PROJ, "index.html"), encoding="utf-8").read()
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
    return json.loads(h[i:j + 1])


def clientes_do_arquivo(path):
    """{nome_normalizado: (nome_original, valor)} — usa a mesma deteccao de
    coluna ja validada, mas devolve por cliente em vez do total"""
    hdr = C.achar_cabecalho(path)
    if hdr is None:
        return {}
    d = C._abrir_excel(path, header=hdr)
    d = d.loc[:, [c for c in d.columns if not str(c).startswith("Unnamed")]]
    d = d.dropna(how="all")
    # descarta linhas de totalizacao
    desc_cols = [c for c in d.columns
                 if pd.to_numeric(d[c], errors="coerce").notna().sum() < len(d) * 0.5]
    if desc_cols:
        d = d[~d[desc_cols].isna().all(axis=1)]
    cand = [(C.score_col(c), i, c) for i, c in enumerate(d.columns)]
    cand = [x for x in cand if x[0] > 0 and not str(d[x[2]].dtype).startswith("datetime")]
    if not cand:
        return {}
    cand.sort(key=lambda t: (t[0], t[1]))
    col_val = cand[-1][2]
    # coluna do cliente: precisa ser TEXTUAL. Escolher pelo nome da coluna
    # sozinho pegou o CODIGO na PAYOT ('944', '3559') — exigir que a maioria
    # dos valores tenha letra.
    col_cli = None
    melhor = -1
    for c in d.columns:
        n = C.norm(c)
        if "PRODUTO" in n or "COD" in n:
            continue
        if not any(t in n for t in ("CLIENTE", "RAZAO", "CONTA", "FILIAL", "NOME")):
            continue
        am = d[c].dropna().astype(str).head(60)
        if am.empty:
            continue
        pct_txt = sum(1 for x in am if re.search(r"[A-Za-z]{3}", x)) / len(am)
        if pct_txt > 0.7 and pct_txt > melhor:
            melhor = pct_txt
            col_cli = c
    if col_cli is None:
        return {}
    # tipo textual (Venda/Bonificacao) -> so venda
    tipo = None
    for c in d.columns:
        n = C.norm(c)
        if "OPERACAO" in n or "TIPO" in n:
            am = " ".join(C.norm(x) for x in d[c].dropna().astype(str).head(50))
            if "VEND" in am or "BONIF" in am:
                tipo = c
                break
    if tipo is not None:
        d = d[~d[tipo].astype(str).map(C.norm).str.contains("BONIF", na=False)]

    out = {}
    for _, r in d.iterrows():
        nome = str(r[col_cli]).strip()
        if not nome or nome.upper() in ("NAN", "TOTAL"):
            continue
        v = C.to_num(r[col_val])
        k = norm_nome(nome)
        if not k:
            continue
        ant = out.get(k, (nome, 0.0))
        out[k] = (ant[0], ant[1] + v)
    return out


def main():
    D = dashboard()
    cd = D["clientes_detalhado"]
    # quem ja esta atribuido, por empresa
    atribuidos = {}
    for e in cd:
        s = {}
        for v in cd[e]:
            for c in cd[e][v]:
                s[norm_nome(c["nome"])] = v
        atribuidos[e] = s

    linhas = []
    meses = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO"]
    for mes in meses:
        pasta, _res, _p = None, None, None
        pasta = C.pasta_mes(mes, 2026)
        if not pasta:
            continue
        for f in sorted(os.listdir(pasta)):
            if f.startswith(".") or f.startswith("~$"):
                continue
            p = os.path.join(pasta, f)
            if not os.path.isfile(p):
                continue
            emp = C.identificar_empresa(f)
            if not emp:
                continue
            chave = "BOTÂNICA" if emp == "BOTANICA" else emp
            conhecidos = atribuidos.get(chave, {})
            for k, (nome, val) in clientes_do_arquivo(p).items():
                if val <= 0:
                    continue
                if k in conhecidos:
                    continue
                # casamento por similaridade antes de declarar "sem vendedor":
                # os nomes variam entre as fontes ('SA0 JOAO' vs 'SAO JOAO')
                from difflib import SequenceMatcher
                achou = False
                for kc in conhecidos:
                    if not kc:
                        continue
                    if kc in k or k in kc:
                        achou = True
                        break
                    if SequenceMatcher(None, k, kc).ratio() >= 0.88:
                        achou = True
                        break
                if not achou:
                    linhas.append({"EMPRESA": chave, "MES": mes.title(),
                                   "CLIENTE": nome, "VALOR": round(val, 2)})

    if not linhas:
        print("nenhum cliente sem atribuicao encontrado.")
        return 0
    df = pd.DataFrame(linhas)
    resumo = (df.groupby(["EMPRESA", "CLIENTE"], as_index=False)["VALOR"].sum()
                .sort_values("VALOR", ascending=False))
    print("=" * 78)
    print("  CLIENTES QUE FATURAM E NAO TEM VENDEDOR ATRIBUIDO")
    print("=" * 78)
    print("total: R$ %s em %d clientes distintos\n"
          % ("{:,.2f}".format(resumo["VALOR"].sum()), len(resumo)))
    print(resumo.head(25).to_string(index=False))
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    saida = os.path.join(PROJ, "_backups", "clientes_sem_vendedor.xlsx")
    with pd.ExcelWriter(saida) as w:
        resumo.to_excel(w, sheet_name="Resumo", index=False)
        df.to_excel(w, sheet_name="Detalhe por mes", index=False)
    print("\nsalvo em _backups/clientes_sem_vendedor.xlsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
