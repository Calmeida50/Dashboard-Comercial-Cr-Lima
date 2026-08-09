#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coletar_faturamento.py — le os relatorios de faturamento do Drive e devolve
o total por empresa do mes pedido.

Regras (validadas contra o historico em 05/08/2026, ver ROTEIRO_AUTOMACAO.md):
  1. sempre o valor LIQUIDO; se so houver um valor, ele ja e liquido
  2. faturamento = somente VENDAS; bonificacao vai para bloco proprio
  3. codigos de operacao numericos (FIAT LUX) sao todos venda
  4. devolucoes vem negativas e entram na soma como estao

Uso:
    python3 coletar_faturamento.py JUNHO 2026
    python3 coletar_faturamento.py            (mes corrente)
"""
import os, re, sys, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)

MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]

# nome canonico -> variantes aceitas no nome do arquivo (ja normalizadas)
EMPRESAS = {
    "GRANADO":    ["GRANADO"],
    "EVER GREEN": ["EVER GREEN", "EVERGREEN"],
    "PRUDENCE":   ["PRUDENCE"],
    "BELLIZ":     ["BELLIZ"],
    "FIAT LUX":   ["FIAT LUX", "FIATLUX"],
    "AQUAFAST":   ["AQUAFAST", "AQUA FAST"],
    "CLESS":      ["CLESS"],
    "PAYOT":      ["PAYOT"],
    "KISABOR":    ["KISABOR", "KISSABOR"],
    "DEPIMIEL":   ["DEPIMIEL", "DEPI MIEL"],
    "BOTANICA":   ["BOTANICA"],
}


def norm(s):
    """maiuscula, sem acento, sem espaco duplicado, sem pontuacao solta"""
    s = str(s or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper().replace("\t", " ").replace("_", " ")
    s = re.sub(r"[^A-Z0-9 /%.,-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def to_num(v):
    """converte para float aceitando 1234.56, 'R$ 1.623,02' e 'R$ 3 657,00'"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        try:
            f = float(v)
            return 0.0 if pd.isna(f) else f
        except Exception:
            return 0.0
    t = str(v).strip()
    if not t:
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = re.sub(r"[R$\s\u00a0]", "", t)          # tira R$, espaco comum e nbsp
    t = t.replace("(", "").replace(")", "")
    if "," in t and "." in t:                   # 1.234,56  ->  1234.56
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:                              # 1234,56   ->  1234.56
        t = t.replace(",", ".")
    t = re.sub(r"[^0-9.\-]", "", t)
    if t.count(".") > 1:                        # 1.234.567 sem decimal
        t = t.replace(".", "")
    try:
        f = float(t)
    except Exception:
        return 0.0
    return -f if neg else f


# ---- escolha da coluna de valor -------------------------------------------
# rejeitadas: componentes de imposto, frete, medias, bases de comissao
VETO = ["IPI", "ICMS", "FRETE", "MEDIO", "MEDIA", "BASE", "COMISSAO", "DESCONTO",
        "PRECO", "UNITARIO", "QTDE", "QUANTIDADE", "PARCELA", "TITULO", "SALDO",
        # datas: 'DATA DE FATURAMENTO' nao e valor. o veto vence a preferencia.
        "DATA", "EMISSAO", "VENCIMENTO",
        # PESO/KG nao e dinheiro. 'Peso Líquido Kisabor' casava com LIQUIDO e
        # ganhava prioridade maxima: marco/2026 da KISABOR virava R$ 12.502,84
        # em vez de R$ 97.634,82 — silenciosamente.
        "PESO", "KG", "CX FD", "CAIXA", "VOLUME", "CUBAGEM"]
# ordem de preferencia: liquido ganha de tudo (regra 1)
PREF = [
    (100, ["LIQUIDO"]),
    (100, ["LIQ"]),
    (90,  ["RECEITA"]),
    (70,  ["FATURADO"]),
    (60,  ["VALOR TOTAL"]),
    (55,  ["VALOR NOTA"]),
    (55,  ["VALOR DA NOTA"]),
    (50,  ["VALOR VENDA"]),
    (50,  ["VALOR DO PEDIDO"]),
    (45,  ["VALOR PRODUTOS"]),
    (40,  ["FATURAMENTO"]),
    (35,  ["R$"]),          # KISABOR usa so 'R$' como cabecalho da coluna
    (30,  ["BRUTO"]),
    (20,  ["VALOR"]),
]


def score_col(nome):
    n = norm(nome)
    # 'R$' normaliza para vazio (o cifrao some), mas E a coluna de valor da
    # KISABOR. Tratar antes do teste de vazio.
    bruto = str(nome or "").strip().upper().replace(" ", "")
    if bruto.startswith("R$"):
        return 35
    if not n:
        return -1
    for v in VETO:
        if v in n:
            return -1
    for peso, chaves in PREF:
        for k in chaves:
            if k in n:
                return peso
    return -1


def achar_cabecalho(path, limite=8):
    """acha a linha do cabecalho: a primeira cujas celulas rendem uma coluna
    de valor valida e pelo menos 2 rotulos textuais"""
    try:
        cru = pd.read_excel(path, header=None, nrows=limite)
    except Exception:
        return None
    for r in range(len(cru)):
        celulas = [c for c in cru.iloc[r].tolist() if str(c) != "nan"]
        textuais = [c for c in celulas if isinstance(c, str) and re.search(r"[A-Za-z]", c)]
        if len(textuais) >= 2 and any(score_col(c) > 0 for c in textuais):
            return r
    return None


def ler_arquivo(path):
    """devolve dict com total de vendas, bonificacao, linhas e diagnostico"""
    out = {"arquivo": os.path.basename(path), "vendas": 0.0, "bonificacao": 0.0,
           "linhas": 0, "coluna": None, "erro": None, "aviso": None}
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".xlsx", ".xls", ".xlsm"):
        out["erro"] = "formato nao suportado (%s)" % ext
        return out

    hdr = achar_cabecalho(path)
    if hdr is None:
        out["erro"] = "cabecalho nao encontrado"
        return out
    try:
        df = pd.read_excel(path, header=hdr)
    except Exception as e:
        out["erro"] = "falha ao abrir: %s" % e
        return out

    # descarta colunas totalmente vazias (FIAT LUX intercala vazias)
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.dropna(how="all")
    if df.empty:
        out["erro"] = "planilha sem linhas"
        return out

    # descarta linha de totalizacao: alguns relatorios (AQUAFAST) fecham com uma
    # linha que so tem o somatorio, sem cliente nem documento. Somar junto dobra
    # o mes. Identificamos pelas colunas descritivas (nao numericas) vazias.
    desc = [c for c in df.columns
            if pd.to_numeric(df[c], errors="coerce").notna().sum() < len(df) * 0.5]
    if desc:
        vazias = df[desc].isna().all(axis=1)
        # Alem da linha totalmente vazia, alguns arquivos fecham com estatistica
        # do Excel rotulada: 'Sum', 'Average', 'Total', 'Count'. A KISABOR faz
        # isso — e como o rotulo cai numa coluna descritiva, a linha NAO fica
        # vazia e escapava do filtro acima.
        ROTULOS = {"SUM", "AVERAGE", "TOTAL", "TOTAL GERAL", "COUNT",
                   "SUBTOTAL", "MEDIA", "SOMA", "CONTAGEM", "MAX", "MIN"}
        rotulada = df[desc].apply(
            lambda linha: any(norm(x) in ROTULOS for x in linha.tolist()), axis=1)
        fora = vazias | rotulada
        if fora.any():
            out["totais_descartados"] = int(fora.sum())
            df = df[~fora]
    if df.empty:
        out["erro"] = "planilha so tinha linha de total"
        return out

    # coluna de valor: maior score; empate resolve pela mais a direita.
    # rejeita colunas de data por tipo, alem do veto por nome.
    cand = []
    for i, c in enumerate(df.columns):
        if str(df[c].dtype).startswith("datetime"):
            continue
        s = score_col(c)
        if s > 0:
            cand.append((s, i, c))
    if not cand:
        out["erro"] = "coluna de valor nao identificada; colunas=%s" % list(df.columns)[:10]
        return out
    cand.sort(key=lambda t: (t[0], t[1]))
    col = cand[-1][2]
    out["coluna"] = str(col)
    if len([c for c in cand if c[0] == cand[-1][0]]) > 1:
        out["aviso"] = "mais de uma coluna com mesma prioridade: %s" % \
                       [str(c[2]) for c in cand if c[0] == cand[-1][0]]

    valores = df[col].map(to_num)
    out["linhas"] = int(len(df))

    # coluna de tipo TEXTUAL (Venda / Bonificacao). Codigos numericos nao contam.
    tipo_col = None
    for c in df.columns:
        n = norm(c)
        if ("OPERACAO" in n or "TIPO" in n):
            amostra = " ".join(norm(x) for x in df[c].dropna().astype(str).head(50))
            if "VEND" in amostra or "BONIF" in amostra:
                tipo_col = c
                break

    if tipo_col is not None:
        tn = df[tipo_col].astype(str).map(norm)
        eh_bonif = tn.str.contains("BONIF", na=False)
        out["bonificacao"] = float(valores[eh_bonif].sum())
        out["vendas"] = float(valores[~eh_bonif].sum())
    else:
        out["vendas"] = float(valores.sum())
    return out


def pasta_mes(mes, ano):
    """acha a pasta do mes tolerando 'JULHO', 'JULHO 26', 'JULHO 2026'"""
    raiz = None
    for d in glob.glob(os.path.join(DRIVE, "FATURAMENTO DAS EMPRESAS*")):
        if os.path.isdir(d):
            raiz = d
            break
    if not raiz:
        return None
    base = os.path.join(raiz, str(ano))
    if not os.path.isdir(base):
        return None
    alvo = norm(mes)
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if os.path.isdir(p) and norm(d).startswith(alvo):
            return p
    return None


def identificar_empresa(nome_arquivo):
    n = norm(nome_arquivo)
    achados = []
    for canon, variantes in EMPRESAS.items():
        for v in variantes:
            if v in n:
                achados.append((len(v), canon))
                break
    if not achados:
        return None
    achados.sort()
    return achados[-1][1]          # casa mais longa vence


def coletar(mes, ano):
    pasta = pasta_mes(mes, ano)
    if not pasta:
        return None, {}, ["pasta do mes %s/%s nao encontrada" % (mes, ano)]

    res, problemas = {}, []
    for f in sorted(os.listdir(pasta)):
        if f.startswith(".") or f.startswith("~$"):
            continue
        caminho = os.path.join(pasta, f)
        if not os.path.isfile(caminho):
            continue
        emp = identificar_empresa(f)
        if not emp:
            problemas.append("empresa nao identificada: %s" % f)
            continue
        r = ler_arquivo(caminho)
        if r["erro"]:
            problemas.append("%s: %s (%s)" % (emp, r["erro"], f))
            continue
        if r["aviso"]:
            problemas.append("%s: %s" % (emp, r["aviso"]))
        if emp in res:
            problemas.append("%s: mais de um arquivo no mes" % emp)
        res[emp] = r

    faltando = [e for e in EMPRESAS if e not in res]
    if faltando:
        problemas.append("sem arquivo: %s" % ", ".join(sorted(faltando)))
    return pasta, res, problemas


def main():
    import datetime
    if len(sys.argv) >= 3:
        mes, ano = sys.argv[1].upper(), int(sys.argv[2])
    else:
        hoje = datetime.date.today()
        mes, ano = MESES[hoje.month - 1], hoje.year

    pasta, res, problemas = coletar(mes, ano)
    print("=" * 66)
    print("  FATURAMENTO %s/%s" % (mes, ano))
    print("=" * 66)
    if pasta:
        print("pasta: %s\n" % pasta.replace(os.path.expanduser("~"), "~"))

    if res:
        print("%-12s %16s %14s %7s  %s" % ("EMPRESA", "VENDAS", "BONIFIC.", "LINHAS", "COLUNA"))
        print("-" * 78)
        tv = tb = 0.0
        for emp in sorted(res):
            r = res[emp]
            tv += r["vendas"]; tb += r["bonificacao"]
            print("%-12s %16s %14s %7d  %s" % (
                emp,
                "{:,.2f}".format(r["vendas"]),
                "{:,.2f}".format(r["bonificacao"]) if r["bonificacao"] else "-",
                r["linhas"], str(r["coluna"])[:28]))
        print("-" * 78)
        print("%-12s %16s %14s" % ("TOTAL", "{:,.2f}".format(tv), "{:,.2f}".format(tb)))

    if problemas:
        print("\nATENCAO:")
        for p in problemas:
            print("  - %s" % p)
    return res


if __name__ == "__main__":
    main()
