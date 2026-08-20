# -*- coding: utf-8 -*-
"""
atualizar_mix_minimo.py — quais clientes NAO tem o mix minimo da Granado.

A pergunta que responde: "quais farmacias/supermercados ativos ainda nao
cadastraram os itens do mix minimo, e quais itens sao esses?"

FONTES (pasta `RELATORIO GRANADO/` no Drive):
  CR LIMA COM E REPRESENTACOES.xlsx   tabela dinamica, aba POR PRODUTO.
      Cliente | Marca | Familia | Categoria | Grupo_Itens | EAN | Dados | meses
      Cabecalho na linha 9; rotulos so aparecem na 1a linha de cada bloco
      (precisa ffill); linhas 'Vol (un)' e subtotais sao descartadas.
      ATENCAO: e o RESULTADO da dinamica. O que estiver filtrado no Excel na
      hora de salvar e o que este script enxerga. Manter tudo em "(Tudo)".
  MIX MINIMO CANAL FARMA GRANADO.xlsx (aba FARMA)      46 itens
  MIX MINIMO CANAL ALIMENTAR.xlsx (aba Tabela RS 2025) 35 itens
      EAN / DUN | Produto | Apresentacao | Unid. de Embarque
      Linhas sem Produto sao titulos de linha (LINHA BEBE etc).
  CLIENTES SEM CANAL - GRANADO.xlsx   de-para preenchido pelo Cristiano para
      os nomes que divergem entre a dinamica e a carteira.

  CARTEIRA DE CLIENTES CR LIMA.xlsx (aba 'Base de Clientes', cabecalho linha 4)
      da o CANAL de cada cliente.

REGRAS (combinadas com o Cristiano em 15/08/2026):
  1. SO CLIENTES ATIVOS — quem nao comprou em 2026 fica de fora, mesmo estando
     na carteira. O objetivo e o que falta cadastrar em quem esta comprando.
  2. So os canais FARMA e ALIMENTAR neste primeiro momento.
  3. Item que o cliente compra e NAO esta no mix minimo nao e problema — a
     lista mostra so o que FALTA do mix.
  4. O casamento de produto e por EAN (bate 46/46 e 35/35). O de cliente e por
     nome normalizado, com o de-para para os divergentes.

Uso:
    python3 atualizar_mix_minimo.py --simular
    python3 atualizar_mix_minimo.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata, difflib
import pandas as pd
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
PASTA = os.path.join(DRIVE, "RELATORIO GRANADO")
CARTEIRA = os.path.join(DRIVE, "CARTEIRA DE CLIENTES CR LIMA.xlsx")
CANAIS = ["farma", "alimentar"]


def nrm(t):
    t = unicodedata.normalize("NFD", str(t or "")).upper()
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]", "", t).strip()


def chave(t):
    return re.sub(r"\s+", "", nrm(t))


def ean(v):
    """EAN so digitos, sem zeros a esquerda (a dinamica e o mix divergem nisso)"""
    s = re.sub(r"\D", "", str(v))
    return s.lstrip("0") if s else ""


def acha(padrao):
    for p in glob.glob(os.path.join(PASTA, "*.xls*")):
        if os.path.basename(p).startswith("~$"):
            continue
        if padrao in nrm(os.path.basename(p)):
            return p
    return None


def ler_dinamica(path):
    """{cliente: {ean: {'v26':x,'v25':y}}} + total por cliente"""
    d = _ler_excel(path, sheet_name="POR PRODUTO", header=None)
    lin = None
    # O cabecalho REAL e a linha que tem 'Dados' e as colunas de mes. Nao dá
    # para procurar por 'Cliente': quando ele esta como FILTRO da dinamica (e
    # nao como campo de linha), a palavra aparece la em cima, na area de
    # filtros, e a leitura pegaria a linha errada.
    for i in range(25):
        vals = [str(x) for x in d.iloc[i].tolist()]
        if "Dados" in vals and any(v.startswith("2026/") or v.startswith("2025/") for v in vals):
            lin = i
            break
    if lin is None:
        print("  ! nao achei o cabecalho da aba POR PRODUTO")
        return None, None, None
    cab = [str(c) for c in d.iloc[lin].tolist()]
    # A planilha que a Granado envia toda semana vem SEM Cliente e SEM EAN
    # (Cliente entra como filtro, nao como campo de linha). Sem os dois a
    # analise e impossivel: nao da para saber quem compra o que. Aconteceu em
    # 17/08/2026, quando a atualizacao semanal sobrescreveu o layout montado.
    faltando = [c for c in ("Cliente", "EAN") if c not in cab]
    if faltando:
        print("  ! A aba POR PRODUTO esta sem: %s" % ", ".join(faltando))
        print("    Campos encontrados: %s" % ", ".join(c for c in cab[:8] if c != "nan"))
        print("    Reinclua na tabela dinamica (lista de campos) e salve de novo:")
        print("      Cliente e EAN como campos de LINHA, junto com Grupo_Itens.")
        return None, None, None
    iCli = cab.index("Cliente")
    iEan = cab.index("EAN")
    iDad = cab.index("Dados")
    c26 = [i for i, c in enumerate(cab) if c.startswith("2026/")]
    c25 = [i for i, c in enumerate(cab) if c.startswith("2025/")]

    body = d.iloc[lin + 1:].copy()
    body.columns = range(body.shape[1])
    # A dinamica escreve o rotulo so na 1a linha de cada bloco — o resto vem
    # vazio e precisa ser preenchido para baixo.
    # A ORDEM DAS COLUNAS MUDA conforme o Cristiano monta a dinamica:
    #   15/08: Cliente | Marca | ... | Grupo_Itens | EAN | Dados | meses
    #   17/08: EAN | Marca | ... | Grupo_Itens | Dados | Cliente | meses
    # Por isso o ffill vai por NOME de coluna, nunca por posicao fixa.
    for i, c in enumerate(cab):
        if c in ("Cliente", "EAN", "Marca", "Família", "Categoria",
                 "Grupo_Itens", "Dados"):
            body[i] = body[i].ffill()
    fat = body[body[iDad] == "Fat Bruto ($)"].copy()   # descarta Vol e subtotais
    fat["v26"] = fat[c26].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    fat["v25"] = fat[c25].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    fat["_cli"] = fat[iCli].astype(str).str.strip()
    fat["_ean"] = fat[iEan].map(ean)

    compras, totais = {}, {}
    for cli, g in fat.groupby("_cli"):
        m = {}
        for _, r in g.iterrows():
            if not r["_ean"]:
                continue
            a = m.setdefault(r["_ean"], {"v26": 0.0, "v25": 0.0})
            a["v26"] += r["v26"]; a["v25"] += r["v25"]
        compras[cli] = m
        totais[cli] = {"v26": round(float(g["v26"].sum()), 2),
                       "v25": round(float(g["v25"].sum()), 2)}
    meses26 = [c for c in cab if c.startswith("2026/")]
    return compras, totais, meses26


def ler_mix(path, aba):
    """[{ean, produto, apres, unid, linha}] — respeitando os titulos de linha"""
    d = _ler_excel(path, sheet_name=aba)
    itens, linha_atual = [], ""
    for _, r in d.iterrows():
        prod = r.get("Produto")
        if pd.isna(prod) or not str(prod).strip():
            # linha de titulo: o nome vem na coluna do EAN
            t = str(r.get("EAN / DUN") or "").strip()
            if t and not t.isdigit():
                linha_atual = t
            continue
        e = ean(r.get("EAN / DUN"))
        if not e:
            continue
        itens.append({"ean": e, "produto": str(prod).strip(),
                      "apres": "" if pd.isna(r.get("Apresentação")) else str(r.get("Apresentação")).strip(),
                      "unid": None if pd.isna(r.get("Unid. de Embarque")) else int(r.get("Unid. de Embarque")),
                      "linha": linha_atual})
    return itens


def ler_canais():
    """{chave_do_nome: (canal, vendedor)} da carteira"""
    d = _ler_excel(CARTEIRA, sheet_name="Base de Clientes", header=3)
    d = d[d["CLIENTE"].notna()]
    out = {}
    for _, r in d.iterrows():
        c = str(r.get("CANAL") or "").strip().lower()
        out[chave(r["CLIENTE"])] = (c, str(r.get("VENDEDOR") or "").strip())
    return out


def ler_depara(carteira):
    """{chave_dinamica: (canal, vendedor, nome_carteira)} do arquivo que o
    Cristiano preencheu. Ordem de prioridade, do mais explicito ao automatico:
      1. coluna CANAL preenchida a mao
      2. coluna NOME NA CARTEIRA (busca o canal daquele nome)
      3. sugestao automatica que ele deixou em branco = aceita
    'NAO ENCONTRADO' fica de fora: sao clientes que nao estao na carteira, e
    13 dos 14 nao compram desde 2025."""
    p = acha("SEM CANAL")
    if not p:
        return {}, []
    d = _ler_excel(p)
    out, ignorados = {}, []
    for _, r in d.iterrows():
        cli = str(r.get("CLIENTE NA DINAMICA GRANADO") or "").strip()
        if not cli:
            continue
        nome = str(r.get("NOME NA CARTEIRA") or "").strip()
        canal = str(r.get("CANAL") or "").strip().lower()
        sug = str(r.get("NOME NA CARTEIRA (sugestao)") or "").strip()
        sugc = str(r.get("CANAL DA SUGESTAO") or "").strip().lower()
        if nome.upper() == "NAO ENCONTRADO" and not canal:
            ignorados.append(cli)
            continue
        if canal and canal != "nan":
            vend = carteira.get(chave(nome), ("", ""))[1] if nome else ""
            out[chave(cli)] = (canal, vend, nome or sug or cli)
        elif nome and nome.upper() != "NAO ENCONTRADO" and chave(nome) in carteira:
            c, v = carteira[chave(nome)]
            out[chave(cli)] = (c, v, nome)
        elif sug and chave(sug) in carteira:
            c, v = carteira[chave(sug)]
            out[chave(cli)] = (c or sugc, v, sug)
    return out, ignorados


def main():
    simular = "--simular" in sys.argv
    din = acha("CR LIMA COM E REPRESENTACOES")
    if not din:
        print("nao achei a dinamica em %s" % PASTA)
        return 1

    print("=" * 74)
    print("  MIX MINIMO — GRANADO%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    print("dinamica: %s (%s)" % (os.path.basename(din),
          datetime.date.fromtimestamp(os.path.getmtime(din)).strftime("%d/%m")))

    compras, totais, meses26 = ler_dinamica(din)
    if compras is None:
        print("ABORTOU: a aba POR PRODUTO precisa ter Cliente e EAN como campos.")
        return 1
    print("  %d clientes · %d meses de 2026" % (len(compras), len(meses26)))

    carteira = ler_canais()
    depara, ignorados = ler_depara(carteira)
    print("  carteira: %d clientes · de-para: %d · ignorados (inativos): %d"
          % (len(carteira), len(depara), len(ignorados)))

    # DOIS TIPOS de lista (20/08/2026):
    #   minimo      — o que cada canal deveria ter (46 farma, 35 alimentar)
    #   obrigatorio — o subconjunto que a Granado trata como inegociavel
    # Mesmo layout de arquivo, mesma analise; a tela alterna entre os dois.
    LISTAS = {
        "minimo": {
            "farma": ("MIX MINIMO CANAL FARMA", "FARMA"),
            "alimentar": ("MIX MINIMO CANAL ALIMENTAR", "Tabela RS 2025"),
        },
        # A MESMA lista de obrigatorios vale para os DOIS canais (confirmado
        # pelo Cristiano em 20/08/2026). A planilha tem uma aba so, chamada
        # FARMA, mas isso e o nome da aba — nao o escopo da lista.
        "obrigatorio": {
            "farma": ("MIX OBRIGATORIO", "FARMA"),
            "alimentar": ("MIX OBRIGATORIO", "FARMA"),
        },
    }
    mixes = {}
    for canal, (padrao, aba) in LISTAS["minimo"].items():
        p = acha(padrao)
        if not p:
            print("  ! nao achei o mix minimo do canal %s" % canal)
            continue
        mixes[canal] = {"itens": ler_mix(p, aba), "arquivo": os.path.basename(p)}

    out = {"atualizado_em": datetime.date.today().isoformat(),
           "meses_2026": len(meses26), "canais": {}}
    def analisa_canal(canal, itens):
        """clientes do canal com o que TEM e o que FALTA daquela lista"""
        eans = {i["ean"] for i in itens}
        clientes = []
        for cli, m in compras.items():
            k = chave(cli)
            if k in depara:
                cn, vend, nome = depara[k]
            elif k in carteira:
                cn, vend = carteira[k]; nome = cli
            else:
                continue
            if cn != canal:
                continue
            if totais[cli]["v26"] <= 0:      # REGRA 1: só ativos em 2026
                continue
            tem = sorted({e for e, v in m.items() if v["v26"] > 0} & eans)
            falta = sorted(eans - set(tem))
            clientes.append({"nome": nome, "cliente_din": cli, "vendedor": vend,
                             "v26": totais[cli]["v26"], "v25": totais[cli]["v25"],
                             "tem": tem, "falta": falta})
        clientes.sort(key=lambda c: -c["v26"])
        return clientes

    for canal, mx in mixes.items():
        itens = mx["itens"]
        clientes = analisa_canal(canal, itens)
        out["canais"][canal] = {"itens": itens, "clientes": clientes,
                                "arquivo": mx["arquivo"]}
        comp = sum(1 for c in clientes if not c["falta"])
        print()
        print("  CANAL %-10s %d itens no mix · %d clientes ativos · %d com mix completo"
              % (canal.upper(), len(itens), len(clientes), comp))
        if clientes:
            print("     falta em media %.1f itens"
                  % (sum(len(c["falta"]) for c in clientes) / len(clientes)))
            for c in clientes[:5]:
                print("     %-44s R$ %10s  tem %2d  falta %2d"
                      % (c["nome"][:44], format(round(c["v26"]), ",d").replace(",", "."),
                         len(c["tem"]), len(c["falta"])))

    # -- mix OBRIGATORIO: mesma analise, lista mais curta ------------------
    out["obrigatorio"] = {}
    for canal, (padrao, aba) in LISTAS["obrigatorio"].items():
        pa = acha(padrao)
        if not pa:
            print("  ! nao achei o mix obrigatorio do canal %s" % canal)
            continue
        itens = ler_mix(pa, aba)
        if not itens:
            print("  ! mix obrigatorio %s: nenhum item lido" % canal)
            continue
        clientes = analisa_canal(canal, itens)
        out["obrigatorio"][canal] = {"itens": itens, "clientes": clientes,
                                     "arquivo": os.path.basename(pa)}
        comp = sum(1 for c in clientes if not c["falta"])
        print()
        print("  OBRIGATORIO %-6s %d itens - %d clientes ativos - %d com o mix completo"
              % (canal.upper(), len(itens), len(clientes), comp))
        if clientes:
            print("     falta em media %.1f itens"
                  % (sum(len(c["falta"]) for c in clientes) / len(clientes)))
            for c in clientes[:5]:
                print("     %-44s R$ %10s  tem %2d  falta %2d"
                      % (c["nome"][:44], format(round(c["v26"]), ",d").replace(",", "."),
                         len(c["tem"]), len(c["falta"])))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    novo = "const MIX_MINIMO = " + json.dumps(out, ensure_ascii=False,
                                              separators=(",", ":")) + ";"
    marca = "const MIX_MINIMO = "
    if marca in s:
        i = s.index(marca); j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        alvo = "const DADOS_PANVEL = "
        i = s.index(alvo)
        s = s[:i] + novo + "\n" + s[i:]
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_mixminimo_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
