#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_panvel_lojas.py — atualiza o RANKING DE LOJAS da Panvel
(`lojas_junho` e `dist_lojas` dentro de DADOS_PANVEL).

Familia de arquivo SEPARADA da de produto. O nome mudou entre os meses:

    junho: SELL OUT PANVEL <EMP> POR LOJA JUNHO 26.xlsx
    julho: VENDA POR LOJA PANVEL <EMP> JULHO 2026.xlsx   <- padrao novo
           (o da PRUDENCE veio sem o mes no nome)

O layout e o MESMO (22 colunas). Por isso a busca aceita os dois padroes e
le o mes de DENTRO do arquivo (coluna `Mês`), nunca do nome.

`lojas_junho` mantem o nome por compatibilidade com a tela, mas guarda o mes
mais recente disponivel.

Uso:
    python3 atualizar_panvel_lojas.py --simular
    python3 atualizar_panvel_lojas.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def arquivos():
    """{(empresa, mes_num): caminho} — mes lido de DENTRO do arquivo.

    O arquivo e reconhecido pelo CONTEUDO (tem coluna de filial), nao pelo
    nome. Ate 13/08/2026 exigia "POR LOJA" no nome; nesse dia a Panvel passou
    a exportar "SELL OUT PANVEL GRANADO AGOSTO 26 ( 12.08 ).xlsx" loja a loja,
    sem essa expressao, e agosto simplesmente nao entrava.
    """
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if os.path.basename(p).startswith("~$"):
            continue
        if "PANVEL" not in n and "DIMED" not in n:
            continue
        if "PRODUTO" in n:          # a versao consolidada, sem filial
            continue
        emp = None
        for e in ("GRANADO", "PRUDENCE", "CLESS", "EVER GREEN", "BELLIZ", "PAYOT"):
            if e in n:
                emp = e
                break
        if not emp:
            continue
        if "POR LOJA" not in n:
            try:
                cols = [norm(c) for c in pd.read_excel(p, nrows=0).columns]
            except Exception:
                continue
            if not any("FILIAL LOJA" in c for c in cols):
                continue
        try:
            d = pd.read_excel(p, usecols=lambda c: norm(c) in ("ANO", "MES"), nrows=5)
            cm = next((c for c in d.columns if norm(c) == "MES"), None)
            mes = int(pd.to_numeric(d[cm], errors="coerce").dropna().iloc[0]) if cm else None
        except Exception:
            mes = None
        if mes is None:                     # fallback: nome do arquivo
            mm = next((i + 1 for i, m in enumerate(MESES) if m in n), None)
            mes = mm
        if mes:
            idx[(emp, mes)] = p
    return idx


def ler(path):
    """devolve (lojas, dist_lojas) — so LOJA FISICA, sem site"""
    d = pd.read_excel(path)
    col = {norm(c): c for c in d.columns}
    cLoja = col.get("FILIAL LOJA")
    cCid  = col.get("FILIAL CIDADE")
    cUf   = col.get("FILIAL UF")
    cVal  = col.get("VALOR TOTAL DE VENDA")
    cQtd  = col.get("QUANTIDADE VENDIDA")
    cOrig = col.get("OPERACAO")
    cCod  = col.get("COD. DO ITEM") or col.get("COD DO ITEM")
    cDesc = col.get("DESCRICAO DO ITEM")
    if not all([cLoja, cVal]):
        return None, None

    d["_v"] = pd.to_numeric(d[cVal], errors="coerce").fillna(0)
    d["_q"] = pd.to_numeric(d[cQtd], errors="coerce").fillna(0) if cQtd else 0
    # o ranking da tela diz "Apenas lojas fisicas (sem site)"
    if cOrig is not None:
        d = d[~d[cOrig].astype(str).str.upper().str.contains("DIG", na=False)]
    d = d[d[cLoja].notna()]

    lojas = []
    for loja, g in d.groupby(cLoja):
        lojas.append({
            "loja": int(pd.to_numeric(loja, errors="coerce") or 0),
            "cidade": str(g[cCid].iloc[0]).strip() if cCid else "",
            "uf": str(g[cUf].iloc[0]).strip() if cUf else "",
            "val26": round(float(g["_v"].sum()), 2),
            "qtd26": int(g["_q"].sum()),
        })
    lojas.sort(key=lambda x: -x["val26"])

    # distribuicao: em quantas lojas cada item vendeu, por faixa de quantidade
    dist = {}
    if cCod is not None and cDesc is not None:
        for cod, g in d.groupby(cCod):
            por_loja = g.groupby(cLoja)["_q"].sum()
            dist[str(cod)] = {
                "nome": str(g[cDesc].iloc[0]).strip(),
                "n0": int((por_loja == 0).sum()),
                "n1": int(((por_loja >= 1) & (por_loja <= 5)).sum()),
                "n2": int(((por_loja > 5) & (por_loja <= 20)).sum()),
                "n3": int(((por_loja > 20) & (por_loja <= 50)).sum()),
                "n4": int((por_loja > 50).sum()),
            }
    return lojas, dist


def main():
    simular = "--simular" in sys.argv
    s = open(INDEX, encoding="utf-8").read()
    ini = s.find("const DADOS_PANVEL = ") + len("const DADOS_PANVEL = ")
    d = 0; j = ini; ins = False; esc = False
    while j < len(s):
        c = s[j]
        if esc: esc = False
        elif c == "\\": esc = True
        elif c == '"': ins = not ins
        elif not ins:
            if c == "{": d += 1
            elif c == "}":
                d -= 1
                if d == 0: break
        j += 1
    P = json.loads(s[ini:j + 1])
    idx = arquivos()

    print("=" * 72)
    print("  RANKING DE LOJAS — PANVEL%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 72)

    empresas = sorted({e for (e, _m) in idx})
    for emp in empresas:
        meses = sorted(m for (e, m) in idx if e == emp)
        if not meses:
            continue
        # confere o mes ANTERIOR contra o publicado, antes de gravar o novo
        antigo = (P.get(emp) or {}).get("lojas_junho") or []
        if len(meses) > 1:
            lojas_ant, _ = ler(idx[(emp, meses[-2])])
            if lojas_ant and antigo:
                tot_a = round(sum(x["val26"] for x in lojas_ant), 2)
                tot_p = round(sum(x.get("val26", 0) for x in antigo), 2)
                dif = tot_a - tot_p
                print("  %-9s conferencia mes %02d: arquivo %s vs publicado %s (dif %s)"
                      % (emp, meses[-2], "{:,.2f}".format(tot_a),
                         "{:,.2f}".format(tot_p), "{:,.2f}".format(dif)))
                if abs(dif) > max(1.0, tot_p * 0.001):
                    # "%%" escapa o sinal de porcentagem. Com um "%" solto o
                    # print QUEBRAVA o script inteiro na hora de avisar — e a
                    # trava so dispara quando ja ha problema, entao o erro so
                    # aparecia no pior momento. Mesmo defeito do log de 09/08.
                    print("     ! divergencia acima de 0,1%% — NAO vou sobrescrever %s"
                          % emp)
                    continue

        lojas, dist = (None, None)
        caminho = idx[(emp, meses[-1])]
        if not os.path.exists(caminho):
            # o arquivo pode ter sido renomeado entre a indexacao e a leitura
            # (aconteceu em 09/08: "PRUDENCE 2026" virou "PRUDENCE JULHO  2026")
            print("  (arquivo mudou de nome durante a execucao; reindexando %s)" % emp)
            idx2 = arquivos()
            caminho = idx2.get((emp, meses[-1])) or idx2.get((emp, meses[-1]))
        if caminho and os.path.exists(caminho):
            lojas, dist = ler(caminho)
        if lojas is None:
            print("  ! %s: nao foi possivel ler" % emp)
            continue
        if emp not in P:
            P[emp] = {"empresa": emp}
        P[emp]["lojas_junho"] = lojas          # nome mantido por compatibilidade
        if dist:
            P[emp]["dist_lojas"] = dist
        P[emp]["lojas_mes"] = meses[-1]
        print("  %-9s mes %02d -> %4d lojas | total %14s | %d itens na distribuicao"
              % (emp, meses[-1], len(lojas),
                 "{:,.2f}".format(sum(x["val26"] for x in lojas)), len(dist or {})))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_pvlojas_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(
        s[:ini] + json.dumps(P, ensure_ascii=False, separators=(",", ":")) + s[j + 1:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
