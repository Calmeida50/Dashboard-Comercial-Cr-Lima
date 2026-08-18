# -*- coding: utf-8 -*-
"""
atualizar_sellout_ladydiu.py — sell out da LADY DIU.

DIFERENTE DE TODOS OS OUTROS: a LadyDiu reporta SOMENTE QUANTIDADE, sem valor
e sem loja. Por isso ela NAO entra nos totalizadores em R$ do dashboard (card
de total, consolidado por empresa, ranking de lojas) — misturaria unidade com
reais. Ela tem tela propria, so em unidades.

FONTE: uma planilha mestre unica no Drive, dentro de
`SELL OUT PRINCIPAIS CLIENTES/`, com "LADY" e "DIU" no caminho.
Layout (lido do arquivo real em 13/08/2026):
    uma aba por ano ('2026', '2025')
    linha 0: titulo | linha 1: cabecalho PRODUTO | JANEIRO..DEZEMBRO | TOTAL
    9 produtos, um por linha

POR QUE PLANILHA UNICA e nao um arquivo por mes: sao 9 numeros por mes. Manter
os nomes de produto sob controle do Cristiano elimina o risco de o cliente
mandar "SILVERFLEX 380 AG" num mes e "Silverflex Cu 380 Ag" no outro, o que
duplicaria produto. O relatorio mensal do cliente pode ser guardado na pasta do
mes como comprovante — este coletor NAO o le.

ESCREVE em DADOS_EMBEDDED:
    sellout_lady_diu = {
      "atualizado_em": "AAAA-MM-DD",     # data real do arquivo
      "meses_com_dado_2026": ["jan", ...],
      "produtos": [{"nome", "qtd_2025": {"jan":n,...}, "qtd_2026": {...},
                    "tot25", "tot26"}]
    }

TRAVA: a coluna TOTAL da planilha e conferida contra a soma dos meses, produto
a produto. Qualquer divergencia ABORTA sem gravar — e sinal de formula quebrada
ou linha fora do lugar.

Uso:
    python3 atualizar_sellout_ladydiu.py --simular
    python3 atualizar_sellout_ladydiu.py
"""
import os, sys, json, glob, shutil, datetime
import pandas as pd
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
RAIZ = os.path.join(DRIVE, "SELL OUT PRINCIPAIS CLIENTES")

MESES_XLS = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
             "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
MESES_K = ["jan", "fev", "mar", "abr", "mai", "jun",
           "jul", "ago", "set", "out", "nov", "dez"]


def achar_planilha():
    """procura por padrao, nao por caminho fixo: a pasta tem espaco no fim do
    nome e isso muda facil quando alguem renomeia"""
    achados = []
    for p in glob.glob(os.path.join(RAIZ, "**", "*.xls*"), recursive=True):
        base = os.path.basename(p).upper()
        if os.path.basename(p).startswith("~$"):
            continue
        if "LADY" in base and "DIU" in base:
            achados.append(p)
    if not achados:
        return None
    # a mais recente, se houver mais de uma
    return sorted(achados, key=os.path.getmtime, reverse=True)[0]


def ler_ano(path, aba):
    """devolve {nome_produto: {mes_k: qtd}} e a lista de erros de conferencia"""
    d = _ler_excel(path, sheet_name=aba, header=1)
    if "PRODUTO" not in d.columns:
        return None, ["aba %s: nao achei a coluna PRODUTO" % aba]
    d = d[d["PRODUTO"].notna()]
    out, erros = {}, []
    for _, r in d.iterrows():
        nome = str(r["PRODUTO"]).strip()
        if not nome or nome.upper() in ("TOTAL", "NAN"):
            continue
        linha, soma = {}, 0.0
        for i, m in enumerate(MESES_XLS):
            if m not in d.columns:
                continue
            v = r[m]
            v = 0 if pd.isna(v) else int(round(float(v)))
            if v:
                linha[MESES_K[i]] = v
            soma += v
        # TRAVA: a coluna TOTAL tem de fechar com a soma dos meses
        if "TOTAL" in d.columns and not pd.isna(r["TOTAL"]):
            if abs(float(r["TOTAL"]) - soma) > 0.001:
                erros.append("%s / %s: soma dos meses %d x TOTAL %s"
                             % (aba, nome, soma, r["TOTAL"]))
        out[nome] = linha
    return out, erros


def carregar_index():
    src = open(os.path.join(PROJ, "index.html"), encoding="utf-8").read()
    i = src.index("const DADOS_EMBEDDED =")
    j = src.index("{", i)
    obj, fim = json.JSONDecoder().raw_decode(src[j:])
    return src, j, j + fim, obj


def main():
    simular = "--simular" in sys.argv
    path = achar_planilha()
    if not path:
        print("planilha da LadyDiu nao encontrada em %s" % RAIZ)
        print("esperado: arquivo com LADY e DIU no nome, em qualquer subpasta")
        return 1

    print("=" * 74)
    print("  SELL OUT LADY DIU%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    print("arquivo: %s" % os.path.basename(path))
    print("pasta  : %s" % os.path.dirname(path).replace(DRIVE + "/", ""))
    dt = datetime.date.fromtimestamp(os.path.getmtime(path))
    print("gravado: %s\n" % dt.isoformat())

    abas = _abrir_excel(path).sheet_names
    dados, erros = {}, []
    for ano in ("2025", "2026"):
        if ano not in abas:
            print("ABORTOU: falta a aba '%s' (abas: %s)" % (ano, abas))
            return 1
        d, e = ler_ano(path, ano)
        if d is None:
            print("ABORTOU: %s" % "; ".join(e))
            return 1
        dados[ano] = d
        erros += e

    if erros:
        print("ABORTOU — a coluna TOTAL nao fecha com a soma dos meses:")
        for x in erros:
            print("  ! %s" % x)
        print("nada foi gravado.")
        return 2

    # produtos: a uniao dos dois anos, na ordem em que aparecem em 2026
    nomes = list(dados["2026"].keys())
    for n in dados["2025"]:
        if n not in nomes:
            nomes.append(n)

    so_25 = [n for n in nomes if n not in dados["2026"]]
    so_26 = [n for n in nomes if n not in dados["2025"]]
    if so_25:
        print("  aviso: so em 2025 -> %s" % ", ".join(so_25))
    if so_26:
        print("  aviso: so em 2026 -> %s" % ", ".join(so_26))

    produtos = []
    for n in nomes:
        q25 = dados["2025"].get(n, {})
        q26 = dados["2026"].get(n, {})
        produtos.append({"nome": n, "qtd_2025": q25, "qtd_2026": q26,
                         "tot25": sum(q25.values()), "tot26": sum(q26.values())})

    meses_26 = [m for m in MESES_K
                if any(p["qtd_2026"].get(m) for p in produtos)]

    # COMPARACAO JUSTA: 2025 restrito aos MESMOS meses que 2026 ja tem.
    # Sem isso, comparar 12 meses de 2025 com 7 de 2026 mostra queda de 50%
    # que e so diferenca de periodo. `tot25` (ano cheio) fica guardado para
    # quando o ano fechar.
    for p in produtos:
        p["tot25_periodo"] = sum(p["qtd_2025"].get(m, 0) for m in meses_26)

    rot = "%s-%s" % (meses_26[0], meses_26[-1]) if meses_26 else "sem dado"
    print("comparacao no mesmo periodo (%s)\n" % rot)
    print("%-34s %8s %8s %8s" % ("PRODUTO", "2025", "2026", "VAR"))
    for p in sorted(produtos, key=lambda x: -x["tot26"]):
        b = p["tot25_periodo"]
        v = ("%+.1f%%" % ((p["tot26"] / b - 1) * 100)) if b else "—"
        print("%-34s %8d %8d %8s" % (p["nome"][:34], b, p["tot26"], v))
    t25 = sum(p["tot25_periodo"] for p in produtos)
    t26 = sum(p["tot26"] for p in produtos)
    print("%-34s %8d %8d %8s" % ("TOTAL", t25, t26,
                                 ("%+.1f%%" % ((t26 / t25 - 1) * 100)) if t25 else "—"))
    print("(2025 fechado, 12 meses: %d)" % sum(p["tot25"] for p in produtos))
    print("\nmeses com dado em 2026: %s" % ", ".join(meses_26))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    src, ini, fim, D = carregar_index()
    D["sellout_lady_diu"] = {"atualizado_em": dt.isoformat(),
                             "meses_com_dado_2026": meses_26,
                             "produtos": produtos}

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_ladydiu_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(os.path.join(PROJ, "index.html"), bkp)
    novo = src[:ini] + json.dumps(D, ensure_ascii=False, separators=(",", ":")) \
           + src[fim:]
    open(os.path.join(PROJ, "index.html"), "w", encoding="utf-8").write(novo)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
