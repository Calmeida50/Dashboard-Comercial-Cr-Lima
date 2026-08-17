# -*- coding: utf-8 -*-
"""
atualizar_ruptura_loja.py — RUPTURA POR LOJA (Must Stock List) da Sao Joao.

A pergunta: "quais lojas PARARAM de vender cada item, ha quanto tempo, e
quanto isso custa por mes?"

Inspirado no modelo MSL que a Prudence monta a partir do IQVIA, com duas
vantagens que o IQVIA nao tem:
  1. Cruza com o ESTOQUE da loja, separando dois problemas que o modelo
     original necessariamente mistura:
        parada COM estoque  -> execucao (exposicao, preco, validade) -> visita
        parada SEM estoque  -> abastecimento -> central de compras
  2. Alcanca as lojas que NUNCA venderam o item (o export do IQVIA so traz
     quem ja vendeu alguma vez).

CONCEITOS (iguais aos do modelo da Prudence, para os numeros conversarem):
  ruptura (meses) = meses consecutivos sem venda contando do mes mais recente
                    para tras
  curva ABC       = por volume no periodo: A = lojas que somam ate 50% do
                    volume do item, B = 50-80%, C = cauda
  perda estimada  = media mensal da loja (nos meses em que vendeu) x meses de
                    ruptura
  prioridade      = CRITICA (curva A parada) · ALTA (curva B, ou 3+ meses) ·
                    MEDIA (1-2 meses) · MONITORAR (gaps historicos)

FONTES (por empresa, mes a mes):
  SELL OUT PRINCIPAIS CLIENTES/2026/<MES>/SELL OUT SAO JOAO <EMP> <MES> 26.xlsx
      Cod Barras | Desc_Produto | Desc_Filial | Vl Liquido | Qt Giro
  ESTOQUE DOS PRINCIPAIS CLIENTES/2026/<MES>/ESTOQUE SAO JOAO <EMP> ...
      Cod Ean | Desc_Produto | Desc_Filial | Estoque Qtde

Grava `RUPTURA_LOJA` no index.html, com os produtos ordenados por FATURAMENTO
(o Cristiano escolhe o que tratar pelo tamanho do item).

Uso:
    python3 atualizar_ruptura_loja.py --simular
    python3 atualizar_ruptura_loja.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
SELLOUT = os.path.join(DRIVE, "SELL OUT PRINCIPAIS CLIENTES", "2026")
ESTOQUE = os.path.join(DRIVE, "ESTOQUE DOS PRINCIPAIS CLIENTES", "2026")
EMPRESAS = ["GRANADO", "PRUDENCE", "BELLIZ", "CLESS", "PAYOT", "EVER GREEN"]
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO",
         "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul",
         "ago", "set", "out", "nov", "dez"]
# quantos produtos por empresa entram na analise (os maiores em faturamento)
TOPN = int(os.environ.get("RUPTURA_TOPN", "40"))


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).upper()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def col(d, *chaves):
    """Acha a coluna pelo nome NORMALIZADO e SEM PONTUACAO.

    O mesmo campo muda de grafia entre as empresas:
        GRANADO/PRUDENCE/CLESS/EVER GREEN -> "Cod Barras"
        BELLIZ/PAYOT                      -> "Cod. Barras"
    Procurar a expressao exata fazia a Belliz inteira ser descartada, e como
    o EAN nao era achado TODA loja parecia parada — 1.275 de 1.275 (17/08)."""
    # Percorre as CHAVES na ordem dada, nao as colunas: a primeira chave tem
    # prioridade. Sem isso, no arquivo da Payot (que tem "Cod. Filial" ANTES
    # de "Desc_Filial") a loja virava o codigo em alguns meses e o nome em
    # outros — o universo de lojas dobrava, 2.433 em vez de 1.235 (17/08).
    cols = [(c, re.sub(r"[^A-Z0-9 ]", "", norm(c))) for c in d.columns]
    for x in chaves:
        xn = re.sub(r"[^A-Z0-9 ]", "", x)
        for c, k in cols:
            if xn in k:
                return c
    return None


def arquivos(base, empresa, marcador):
    """{indice_do_mes: caminho} — o mais recente de cada mes.

    A pasta de marco se chama "MARCO 26" COM CEDILHA no Drive; comparar por
    glob literal fazia o mes inteiro sumir da analise (17/08/2026). Por isso a
    comparacao e feita com o nome NORMALIZADO da pasta."""
    out = {}
    pastas = [d for d in glob.glob(os.path.join(base, "*")) if os.path.isdir(d)]
    for i, mes in enumerate(MESES):
        for pasta in [d for d in pastas if norm(os.path.basename(d)).startswith(mes)]:
            for p in glob.glob(os.path.join(pasta, "*.xls*")):
                b = norm(os.path.basename(p))
                if b.startswith("~$"):
                    continue
                if "SAO JOAO" in b and empresa in b and marcador in b:
                    if i not in out or os.path.getmtime(p) > os.path.getmtime(out[i]):
                        out[i] = p
    return out


def ler_sellout(path):
    """[(ean, produto, filial, qtd, valor)]"""
    d = pd.read_excel(path)
    # A chave do item e SEMPRE o EAN. A Payot nao traz codigo de barras em
    # janeiro e fevereiro; nesses meses o arquivo e PULADO, com aviso. Usar o
    # codigo interno como reserva pareceu boa ideia, mas cria uma segunda
    # identidade para o mesmo produto e quebra o cruzamento com o estoque —
    # o item aparecia com "0 lojas com estoque" (17/08/2026).
    cE = col(d, "COD BARRAS", "COD EAN", "EAN")
    cP = col(d, "DESC_PRODUTO", "DESC PRODUTO")
    cF, cQ = col(d, "DESC_FILIAL", "FILIAL"), col(d, "QT GIRO", "QTD", "QUANT")
    cV = col(d, "VL LIQUIDO", "VALOR")
    if not all([cE, cP, cF, cQ]):
        falta = "EAN" if not cE else "colunas"
        print("     ~ %s: sem %s — mes ignorado"
              % (os.path.basename(path)[:44], falta))
        return []
    out = []
    for _, r in d.iterrows():
        f = norm(r[cF])       # NORMALIZA: a Payot muda a grafia entre meses
        e = re.sub(r"\D", "", str(r[cE]))
        if not f or f == "NAN" or not e:
            continue          # pula a linha "Total" e filtros do rodape
        q = pd.to_numeric(r[cQ], errors="coerce")
        v = pd.to_numeric(r[cV], errors="coerce") if cV else 0
        out.append((e, str(r[cP]).strip(), f,
                    0 if pd.isna(q) else float(q), 0 if pd.isna(v) else float(v)))
    return out


def ler_estoque(path):
    """{(ean, filial): qtde}"""
    d = pd.read_excel(path)
    cE, cF = col(d, "COD EAN", "COD BARRAS", "EAN"), col(d, "DESC_FILIAL", "FILIAL")
    cQ = col(d, "ESTOQUE QTDE", "ESTOQUE", "QTDE")
    if not all([cE, cF, cQ]):
        return {}
    out = {}
    for _, r in d.iterrows():
        f = norm(r[cF])
        e = re.sub(r"\D", "", str(r[cE]))
        if not f or f == "NAN" or not e:
            continue
        q = pd.to_numeric(r[cQ], errors="coerce")
        out[(e, f)] = 0 if pd.isna(q) else int(q)
    return out


def analisa(emp, simular=False):
    so = arquivos(SELLOUT, emp, "SELL OUT")
    if not so:
        return None
    vendas = {}          # {ean: {filial: {mes: qtd}}}
    valor = {}           # {ean: valor total}
    nomes = {}
    meses = []
    for i in sorted(so):
        linhas = ler_sellout(so[i])
        if not linhas:
            continue     # mes ignorado (sem EAN) nao entra no horizonte
        meses.append(i)
        for e, prod, fil, q, v in linhas:
            nomes.setdefault(e, prod)
            valor[e] = valor.get(e, 0) + v
            vendas.setdefault(e, {}).setdefault(fil, {})[i] = \
                vendas.get(e, {}).get(fil, {}).get(i, 0) + q

    # estoque: a foto mais recente
    est = arquivos(ESTOQUE, emp, "ESTOQUE")
    estoque = ler_estoque(est[max(est)]) if est else {}
    mes_est = max(est) if est else None

    # universo de lojas da empresa: toda filial que apareceu em qualquer mes
    todas = set()
    for e in vendas:
        todas |= set(vendas[e])
    for (e, f) in estoque:
        todas.add(f)

    ult = meses[-1]
    itens = []
    for e in sorted(valor, key=lambda x: -valor[x])[:TOPN]:
        porloja = vendas.get(e, {})
        # curva ABC por volume no periodo
        tot = {f: sum(m.values()) for f, m in porloja.items()}
        volume = sum(tot.values())
        acc, curva = 0, {}
        for f in sorted(tot, key=lambda x: -tot[x]):
            acc += tot[f]
            curva[f] = "A" if acc <= volume * 0.5 else ("B" if acc <= volume * 0.8 else "C")
        lojas = []
        for f in sorted(todas):
            m = porloja.get(f, {})
            comvenda = [i for i in meses if m.get(i, 0) > 0]
            # ruptura por RECENCIA: meses seguidos sem venda a partir do fim
            rup = 0
            for i in reversed(meses):
                if m.get(i, 0) > 0:
                    break
                rup += 1
            media = (sum(m[i] for i in comvenda) / len(comvenda)) if comvenda else 0
            eq = estoque.get((e, f))
            cv = curva.get(f, "C")
            if not comvenda:
                pri = "NUNCA VENDEU"
            elif rup == 0:
                gaps = len(meses) - len(comvenda)
                pri = "MONITORAR" if gaps >= 2 else "REGULAR"
            elif cv == "A":
                pri = "CRITICA"
            elif cv == "B" or rup >= 3:
                pri = "ALTA"
            else:
                pri = "MEDIA"
            lojas.append({"loja": f, "curva": cv, "rup": rup,
                          "meses": {ABREV[i]: m.get(i, 0) for i in meses if m.get(i, 0)},
                          "total": round(sum(m.values())),
                          "media": round(media, 1),
                          "perda": round(media * rup),
                          "estoque": eq,
                          "ult": ABREV[max(comvenda)] if comvenda else None,
                          "pri": pri})
        # SO AS LOJAS COM PROBLEMA vao para o index.html. Guardar as 1.276
        # lojas de cada item somaria dezenas de MB — e a loja que vende bem
        # nao precisa aparecer numa tela de ruptura. As saudaveis viram
        # contagem.
        emrup = [l for l in lojas if l["rup"] > 0]
        nunca = [l for l in lojas if l["pri"] == "NUNCA VENDEU"]
        emrup.sort(key=lambda l: (-l["perda"], -l["total"]))
        prob = emrup[:50]           # as 50 de maior perda; o resto vira contagem
        # 50 mantem o bloco em ~3 MB. O Excel da tela usa esta mesma lista.
        ok = len(lojas) - len(emrup) - len(nunca)
        itens.append({"ean": e, "nome": nomes.get(e, e),
                      "valor": round(valor[e], 2), "volume": int(volume),
                      "n_lojas": len(lojas), "n_ok": ok,
                      "n_rup": len(emrup), "n_nunca": len(nunca),
                      "n_com_est": sum(1 for l in emrup if (l["estoque"] or 0) > 0),
                      "perda": sum(l["perda"] for l in emrup),
                      "curvas": {c: sum(1 for l in emrup if l["curva"] == c)
                                 for c in "ABC"},
                      "lojas": prob})
    return {"itens": itens, "meses": [ABREV[i] for i in meses],
            "mes_estoque": ABREV[mes_est] if mes_est is not None else None,
            "n_lojas": len(todas)}


def main():
    simular = "--simular" in sys.argv
    print("=" * 74)
    print("  RUPTURA POR LOJA — SAO JOAO%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    out = {"atualizado_em": datetime.date.today().isoformat(), "empresas": {}}
    for emp in EMPRESAS:
        r = analisa(emp, simular)
        if not r:
            print("  %-11s sem arquivos" % emp)
            continue
        out["empresas"][emp] = r
        # panorama
        n_rup = n_crit = n_alta = n_nunca = 0
        perda = 0
        for it in r["itens"]:
            for l in it["lojas"]:
                if l["pri"] == "NUNCA VENDEU":
                    n_nunca += 1
                elif l["rup"] > 0:
                    n_rup += 1
                    perda += l["perda"]
                    if l["pri"] == "CRITICA":
                        n_crit += 1
                    elif l["pri"] == "ALTA":
                        n_alta += 1
        print("  %-11s %2d itens · %d lojas · %s" %
              (emp, len(r["itens"]), r["n_lojas"], "-".join(r["meses"])))
        print("               %d pares item-loja em ruptura (%d criticas, %d altas) · "
              "%d nunca venderam · perda %d un/mes"
              % (n_rup, n_crit, n_alta, n_nunca, perda))
        if r["itens"]:
            it = r["itens"][0]
            rl = [l for l in it["lojas"] if l["rup"] > 0]
            comest = [l for l in rl if (l["estoque"] or 0) > 0]
            print("               ex.: %-38s %d lojas paradas, %d COM estoque"
                  % (it["nome"][:38], len(rl), len(comest)))

    if simular:
        tam = len(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        print("\ntamanho do bloco: %.1f MB" % (tam / 1024 / 1024))
        print("SIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    novo = "const RUPTURA_LOJA = " + json.dumps(out, ensure_ascii=False,
                                                separators=(",", ":")) + ";"
    marca = "const RUPTURA_LOJA = "
    if marca in s:
        i = s.index(marca); j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        alvo = "const MIX_MINIMO = "
        i = s.index(alvo) if alvo in s else s.index("const DADOS_PANVEL = ")
        s = s[:i] + novo + "\n" + s[i:]
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_ruptura_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado (%.1f MB). backup em _backups/%s"
          % (len(novo) / 1024 / 1024, os.path.basename(bkp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
