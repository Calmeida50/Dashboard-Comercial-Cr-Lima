# -*- coding: utf-8 -*-
"""
atualizar_parametros_panvel.py — grava PARAMS_PANVEL (cluster + mix).

PARAMETRO, NAO MOVIMENTO. Estes arquivos mudam no maximo 2x por ano; ficam
FORA das pastas de mes, em `SELL OUT PRINCIPAIS CLIENTES/PARAMETROS PANVEL/`.

    CLUSTER PANVEL <EMPRESA> ATUALIZADO.xlsx
        uma linha por FILIAL x ITEM = onde a Panvel entende que o item deve
        estar. `lojas_liberadas` = filiais distintas por item.
    MIX PANVEL COM FAMILIA E CATEGORIA <EMPRESA>.xlsx
        familia e categoria na NOSSA nomenclatura. O relatorio de sell out da
        Panvel traz familia/categoria proprias, com outra nomenclatura — por
        decisao do Cristiano (13/08/2026) valem SEMPRE as daqui.

Grava em index.html:

    const PARAMS_PANVEL = {
      "atualizado_em": "AAAA-MM-DD",
      "GRANADO": {"lojas_liberadas": {"481280": 655, ...},
                  "familia":   {"481280": "GRANADO"},
                  "categoria": {"481280": "BARRA"},
                  "nome":      {"481280": "SAB ENXOFRE GRANADO 90G"},
                  "arquivos": {...}, "n_filiais": 701}
    }

A chave e SEMPRE o codigo do item — e o que casa sell out, estoque e cluster.

Uso:
    python3 atualizar_parametros_panvel.py --simular
    python3 atualizar_parametros_panvel.py
"""
import os, re, sys, json, glob, shutil, datetime
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
PASTA = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES/PARAMETROS PANVEL"
)
EMPRESAS = ["GRANADO", "PRUDENCE", "CLESS"]


def cod(v):
    """codigo como texto, sem o .0 que o Excel cria ao ler como numero"""
    return re.sub(r"\.0$", "", str(v).strip())


def acha_col(d, *chaves, excl=()):
    """casa nome de coluna SEM acento: 'Cód. do Item' vira 'COD. DO ITEM'.
    Comparar com acento era o motivo de o cluster nao ser reconhecido."""
    import unicodedata
    def norm(s):
        s = unicodedata.normalize("NFKD", str(s))
        return "".join(c for c in s if not unicodedata.combining(c)).upper()
    for c in d.columns:
        k = norm(c)
        if all(x in k for x in chaves) and not any(e in k for e in excl):
            return c
    return None


def ler_cluster(path):
    """{cod: n_filiais}, nome do item e total de filiais do arquivo"""
    d = pd.read_excel(path)
    cItem = acha_col(d, "COD", "ITEM", excl=("BARRA", "FORNECEDOR"))
    cFil = acha_col(d, "COD", "FILIAL")
    cNome = acha_col(d, "DESCRICAO") or acha_col(d, "DESCRIÇÃO")
    if cItem is None or cFil is None:
        return None, None, 0
    d["_c"] = d[cItem].map(cod)
    d = d[d["_c"].str.len() > 0]
    lib = d.groupby("_c")[cFil].nunique().to_dict()
    nomes = {}
    if cNome is not None:
        for c, g in d.groupby("_c"):
            nomes[c] = str(g[cNome].iloc[0]).strip()
    return {k: int(v) for k, v in lib.items()}, nomes, int(d[cFil].nunique())


def ler_mix(path):
    """{cod: {linha, categoria, grupo}} — na NOSSA nomenclatura.

    HIERARQUIA FLEXIVEL (15/08/2026), igual a Sao Joao:
        GRANADO   LINHA > CATEGORIA > GRUPO
        CLESS     LINHA > CATEGORIA
        PRUDENCE  CATEGORIA
    O arquivo tambem pode trazer `Status`, que manda no ativo/inativo — mas na
    Panvel quem decide isso e o CLUSTER, entao aqui o Status e so referencia.
    """
    d = pd.read_excel(path)
    cItem = acha_col(d, "COD", "ITEM", excl=("BARRA", "FORNECEDOR", "GRUPO"))
    if cItem is None:
        cItem = acha_col(d, "CODIGO", excl=("BARRA", "FORNECEDOR"))
    cFam = acha_col(d, "FAMILIA") or acha_col(d, "LINHA")
    cCat = acha_col(d, "CATEGORIA")
    cGru = acha_col(d, "GRUPO")
    if cItem is None:
        return {}, {}, {}
    d["_c"] = d[cItem].map(cod)
    fam, cat, hier = {}, {}, {}
    conflitos = []
    for c, g in d.groupby("_c"):
        if not c:
            continue
        def uni(col):
            if col is None:
                return []
            return sorted({str(x).strip().upper() for x in g[col].dropna()
                           if str(x).strip() and str(x).strip().upper() != "NAN"})
        fs, cs, gs = uni(cFam), uni(cCat), uni(cGru)
        if len(fs) > 1 or len(cs) > 1 or len(gs) > 1:
            conflitos.append((c, fs, cs, gs))
        item = {}
        if fs:
            fam[c] = fs[0]; item["linha"] = fs[0]
        if cs:
            cat[c] = cs[0]; item["categoria"] = cs[0]
        if gs:
            item["grupo"] = gs[0]
        if item:
            hier[c] = item
    if conflitos:
        print("  ! %d codigos com classificacao divergente na planilha:"
              % len(conflitos))
        for c, fs, cs, gs in conflitos[:5]:
            print("      %s -> linha %s | categoria %s | grupo %s" % (c, fs, cs, gs))
    return fam, cat, hier


def main():
    simular = "--simular" in sys.argv
    if not os.path.isdir(PASTA):
        print("pasta de parametros nao encontrada:\n  %s" % PASTA)
        return 1

    print("=" * 74)
    print("  PARAMETROS PANVEL — cluster e mix%s"
          % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)

    arqs = [p for p in glob.glob(os.path.join(PASTA, "*.xls*"))
            if not os.path.basename(p).startswith("~$")]
    # mix SEM empresa no nome vale para todas: em 13/08/2026 o arquivo passou
    # de "...CATEGORIA GRANADO.xlsx" para "...CATEGORIA.xlsx" e o coletor
    # deixou de encontra-lo. Casar so por empresa era fragil demais.
    mix_geral = next((p for p in arqs
                      if "MIX" in os.path.basename(p).upper()
                      and not any(e in os.path.basename(p).upper()
                                  for e in EMPRESAS)), None)
    out = {}
    for emp in EMPRESAS:
        cl = next((p for p in arqs if "CLUSTER" in os.path.basename(p).upper()
                   and emp in os.path.basename(p).upper()), None)
        mx = next((p for p in arqs if "MIX" in os.path.basename(p).upper()
                   and emp in os.path.basename(p).upper()), None) or mix_geral
        if not cl and not mx:
            continue
        bloco = {"lojas_liberadas": {}, "familia": {}, "categoria": {},
                 "nome": {}, "n_filiais": 0, "arquivos": {}}
        if cl:
            lib, nomes, nfil = ler_cluster(cl)
            if lib is None:
                print("  ! %s: cluster com layout nao reconhecido" % emp)
            else:
                bloco["lojas_liberadas"] = lib
                bloco["nome"] = nomes
                bloco["n_filiais"] = nfil
                bloco["arquivos"]["cluster"] = os.path.basename(cl)
        if mx:
            fam, cat, hier = ler_mix(mx)
            bloco["familia"] = fam
            bloco["categoria"] = cat
            bloco["hier"] = hier
            bloco["niveis"] = [n for n in ("linha", "categoria", "grupo")
                               if any(n in v for v in hier.values())]
            bloco["arquivos"]["mix"] = os.path.basename(mx)
        out[emp] = bloco
        lib = bloco["lojas_liberadas"]
        print("  %-9s cluster %3d SKUs (%d filiais) | classificacao %3d SKUs | niveis: %s"
              % (emp, len(lib), bloco["n_filiais"], len(bloco.get("hier") or {}),
                 " > ".join(n.upper() for n in (bloco.get("niveis") or [])) or "—"))
        if lib:
            top = sorted(lib.items(), key=lambda x: -x[1])[:3]
            print("            mais liberados: %s"
                  % ", ".join("%s=%d lojas" % (bloco["nome"].get(c, c)[:28], n)
                              for c, n in top))

    if not out:
        print("nenhum arquivo de parametro reconhecido em %s" % PASTA)
        return 1

    out["atualizado_em"] = datetime.date.today().isoformat()

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    novo = "const PARAMS_PANVEL = " + json.dumps(out, ensure_ascii=False,
                                                 separators=(",", ":")) + ";"
    marca = "const PARAMS_PANVEL = "
    if marca in s:
        i = s.index(marca)
        fim = s.index(";", s.index("}", i))   # fim do objeto
        # recorta ate o fim da linha da declaracao anterior
        j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        # cria logo antes de DADOS_PANVEL, para carregar junto
        alvo = "const DADOS_PANVEL = "
        i = s.index(alvo)
        s = s[:i] + novo + "\n" + s[i:]

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_paramspv_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
