# -*- coding: utf-8 -*-
"""
atualizar_parametros_sao_joao.py — grava PARAMS_SAO_JOAO (categoria por item).

PARAMETRO, NAO MOVIMENTO. O relatorio de sell out da Sao Joao NAO traz
categoria; ela vem de planilhas mantidas pelo Cristiano em
`SELL OUT PRINCIPAIS CLIENTES/PARAMETRO SAO JOAO/`:

    MIX <EMPRESA> SAO JOAO COM CATEGORIA.xlsx
        colunas: Categoria | Produto
        contem SOMENTE OS ITENS ATIVOS (confirmado em 14/08/2026).

Muda so quando um item novo e cadastrado. Basta acrescentar a linha na
planilha — nao precisa mexer em codigo.

A chave e o NOME do produto normalizado: a Sao Joao nao traz codigo de item no
sell out, ao contrario da Panvel.

Item do sell out que NAO estiver na planilha fica sem categoria e aparece com
"—" na tela: sao os inativos, que ainda vendem estoque residual.

Uso:
    python3 atualizar_parametros_sao_joao.py --simular
    python3 atualizar_parametros_sao_joao.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
PASTA = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES/PARAMETRO SAO JOAO"
)
EMPRESAS = ["GRANADO", "PRUDENCE", "BELLIZ", "CLESS", "PAYOT", "EVER GREEN"]


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).upper()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def acha_col(d, *chaves):
    for c in d.columns:
        k = norm(c)
        if any(x in k for x in chaves):
            return c
    return None


def ler(path):
    """{nome_normalizado: categoria}, lista de ativos e conflitos.

    Dois layouts convivem (14/08/2026):
      BELLIZ  -> Categoria | Produto           (so os ativos)
      GRANADO -> Status | CATEGORIA | DESCRICAO (ativos E inativos)
    Quando houver coluna Status, os ativos saem dela; senao, TODOS os itens do
    arquivo sao considerados ativos, que e a convencao do arquivo da Belliz.
    """
    d = pd.read_excel(path)
    cProd = acha_col(d, "PRODUTO", "DESCRICAO", "ITEM")
    cCat = acha_col(d, "CATEGORIA")
    cSt = acha_col(d, "STATUS")
    if cProd is None or cCat is None:
        return None, None, []
    out, ativos, conflitos = {}, [], []
    for _, r in d.iterrows():
        n = norm(r[cProd])
        c = norm(r[cCat])
        if not n or not c or n == "NAN":
            continue
        if n in out and out[n] != c:
            conflitos.append((n, out[n], c))
        out[n] = c
        if cSt is None or norm(r[cSt]).startswith("ATIV"):
            ativos.append(str(r[cProd]).strip())
    return out, ativos, conflitos


def main():
    simular = "--simular" in sys.argv
    if not os.path.isdir(PASTA):
        print("pasta de parametros nao encontrada:\n  %s" % PASTA)
        return 1

    print("=" * 74)
    print("  PARAMETROS SAO JOAO — categoria por item%s"
          % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)

    arqs = [p for p in glob.glob(os.path.join(PASTA, "*.xls*"))
            if not os.path.basename(p).startswith("~$")]
    out = {}
    for emp in EMPRESAS:
        alvo = next((p for p in arqs if emp in norm(os.path.basename(p))), None)
        if not alvo:
            continue
        cats, ativos, conf = ler(alvo)
        if cats is None:
            print("  ! %s: nao achei as colunas Produto/Categoria em %s"
                  % (emp, os.path.basename(alvo)))
            continue
        if conf:
            print("  ! %s: %d itens com categoria divergente na planilha"
                  % (emp, len(conf)))
            for n, a, b in conf[:5]:
                print("      %s -> %s / %s" % (n[:44], a, b))
        out[emp] = {"categoria": cats, "ativos": sorted(set(ativos)),
                    "arquivo": os.path.basename(alvo)}
        print("  %-11s %3d itens (%d ativos) · %2d categorias · %s"
              % (emp, len(cats), len(set(ativos)), len(set(cats.values())),
                 os.path.basename(alvo)[:38]))

    if not out:
        print("nenhum arquivo reconhecido em %s" % PASTA)
        return 1

    # confere contra o sell out: quantos itens ficam sem categoria
    # (o esperado sao os INATIVOS, que vendem estoque residual)
    try:
        s0 = open(INDEX, encoding="utf-8").read()
        j = s0.index("{", s0.index("const DADOS_EMBEDDED ="))
        D, _ = json.JSONDecoder().raw_decode(s0[j:])
        sj = D.get("sellout_sao_joao", {})
        for emp, b in out.items():
            prods = [p["nome"] for p in (sj.get(emp, {}).get("produtos") or [])]
            sem = [n for n in prods if norm(n) not in b["categoria"]]
            print("     %s: %d de %d produtos do sell out sem categoria (inativos)"
                  % (emp, len(sem), len(prods)))
            # CONFERENCIA: o mix ativo tambem vive escrito a mao no index.html
            # (MIX_ATIVO_SAO_JOAO). Se a planilha traz Status, os dois tem de
            # concordar — senao o selo ATIVO e a categoria contam historias
            # diferentes na mesma linha.
            m = re.search(r"%s: new Set\(\[(.*?)\]\)" % re.escape(emp),
                          s0[s0.index("const MIX_ATIVO_SAO_JOAO"):
                             s0.index("\n};", s0.index("const MIX_ATIVO_SAO_JOAO"))],
                          re.S)
            if m and b.get("ativos"):
                cod = {norm(x) for x in re.findall(r'"([^"]+)"', m.group(1))}
                pla = {norm(x) for x in b["ativos"]}
                if cod != pla:
                    print("     ! %s: mix ativo do codigo (%d) x planilha (%d) NAO batem"
                          % (emp, len(cod), len(pla)))
                    for n in sorted(cod - pla)[:4]:
                        print("        so no codigo  : %s" % n[:52])
                    for n in sorted(pla - cod)[:4]:
                        print("        so na planilha: %s" % n[:52])
                else:
                    print("     %s: mix ativo bate com o codigo (%d itens)" % (emp, len(cod)))
    except Exception as e:
        print("  (nao consegui conferir contra o sell out: %s)" % e)

    out["atualizado_em"] = datetime.date.today().isoformat()

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    novo = "const PARAMS_SAO_JOAO = " + json.dumps(out, ensure_ascii=False,
                                                   separators=(",", ":")) + ";"
    marca = "const PARAMS_SAO_JOAO = "
    if marca in s:
        i = s.index(marca)
        j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        alvo = "const MIX_ATIVO_SAO_JOAO = "
        i = s.index(alvo)
        s = s[:i] + novo + "\n" + s[i:]

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_paramssj_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
