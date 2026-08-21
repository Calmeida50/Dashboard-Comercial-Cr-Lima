# -*- coding: utf-8 -*-
"""
atualizar_sellin.py — SELL IN (nossa venda) da Granado e da Belliz.

Ate agora o dashboard media sell OUT (o que o cliente vende ao consumidor).
Estas duas industrias mandam o sell IN aberto por CLIENTE, PRODUTO e MES, com
o ano anterior junto — da para responder perguntas que o sell out nao responde:
quem cresce, quem caiu, quem parou de comprar e o quanto o negocio esta
concentrado.

FONTES:
  GRANADO  RELATORIO GRANADO/CR LIMA COM E REPRESENTACOES.xlsx (aba POR PRODUTO)
      Cabecalho na linha 9. Cliente | Marca | Familia | Categoria |
      Grupo_Itens | EAN | Dados | 2025/01..2026/NN
      Rotulo so na 1a linha do bloco (ffill); linhas 'Vol (un)' e subtotais
      sao descartadas; a ORDEM das colunas muda conforme o Cristiano monta a
      dinamica, por isso tudo e localizado por NOME.
  BELLIZ   RELATORIOS BELLIZ/FATURAMENTO BELLIZ 20XX POR PRODUTO E CLIENTE.xlsx
      Cabecalho na linha 2. Cliente | NomeCliente | Canal | Familia | Item |
      Descricao | Primeira Positivacao | pares (Fat, Qtd) por mes.
      Um arquivo por ano. A linha 'Totals' e descartada.
      O CANAL vem da propria Belliz.

Grava `SELL_IN` no index.html (via window, ver nota no fim do arquivo).

Uso:
    python3 atualizar_sellin.py --simular
    python3 atualizar_sellin.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd
from drive_io import ler_excel as _ler_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
ANO = 2026


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).upper()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def num(v):
    n = pd.to_numeric(v, errors="coerce")
    return 0.0 if pd.isna(n) else float(n)


def _monta(regs):
    """regs = [(cliente, canal, cod, produto, familia, ano, mes_idx, valor)]
    -> blocos de clientes e produtos, com o ano anterior junto"""
    cli, prod = {}, {}
    meses = set()
    for c, canal, cod, pnome, fam, ano, mi, v in regs:
        if v == 0:
            continue
        if ano == ANO:
            meses.add(mi)
        a = cli.setdefault(c, {"nome": c, "canal": canal,
                               "m26": {}, "m25": {}, "sk26": set(), "sk25": set()})
        if canal and not a["canal"]:
            a["canal"] = canal
        k = "m26" if ano == ANO else "m25"
        a[k][ABREV[mi]] = round(a[k].get(ABREV[mi], 0) + v, 2)
        a["sk26" if ano == ANO else "sk25"].add(cod)

        p = prod.setdefault(cod, {"cod": cod, "nome": pnome, "familia": fam,
                                  "v26": 0.0, "v25": 0.0,
                                  "m26": {}, "cli26": set(), "cli25": set()})
        if ano == ANO:
            p["v26"] += v
            p["m26"][ABREV[mi]] = round(p["m26"].get(ABREV[mi], 0) + v, 2)
            p["cli26"].add(c)
        else:
            p["v25"] += v
            p["cli25"].add(c)
    return cli, prod, sorted(meses)


def ler_granado():
    p = os.path.join(DRIVE, "RELATORIO GRANADO", "CR LIMA COM E REPRESENTACOES.xlsx")
    if not os.path.exists(p):
        return []
    d = _ler_excel(p, sheet_name="POR PRODUTO", header=None)
    lin = None
    for i in range(25):
        vals = [str(x) for x in d.iloc[i].tolist()]
        if "Dados" in vals and any(v[:5] in ("2025/", "2026/") for v in vals):
            lin = i
            break
    if lin is None:
        print("  ! GRANADO: nao achei o cabecalho")
        return []
    cab = [str(c) for c in d.iloc[lin].tolist()]
    if "Cliente" not in cab or "EAN" not in cab:
        print("  ! GRANADO: a dinamica precisa de Cliente e EAN como campos")
        return []
    iCli, iEan, iDad = cab.index("Cliente"), cab.index("EAN"), cab.index("Dados")
    iFam = cab.index("Familia") if "Familia" in cab else (
        cab.index("Família") if "Família" in cab else None)
    iGru = cab.index("Grupo_Itens") if "Grupo_Itens" in cab else None
    body = d.iloc[lin + 1:].copy()
    body.columns = range(body.shape[1])
    for i, c in enumerate(cab):
        if c in ("Cliente", "EAN", "Marca", "Familia", "Família",
                 "Categoria", "Grupo_Itens", "Dados"):
            body[i] = body[i].ffill()
    fat = body[body[iDad] == "Fat Bruto ($)"]
    regs = []
    for _, r in fat.iterrows():
        cli = str(r[iCli]).strip()
        cod = re.sub(r"\D", "", str(r[iEan])).lstrip("0")
        pnome = str(r[iGru]).strip() if iGru is not None else cod
        fam = str(r[iFam]).strip() if iFam is not None else ""
        for j, c in enumerate(cab):
            if len(c) == 7 and c[4] == "/":
                ano, mes = int(c[:4]), int(c[5:7]) - 1
                v = num(r[j])
                if v:
                    regs.append((cli, "", cod, pnome, fam, ano, mes, v))
    print("  GRANADO  %d registros" % len(regs))
    return regs


def ler_belliz():
    regs = []
    for p in sorted(glob.glob(os.path.join(DRIVE, "RELATORIOS BELLIZ", "*.xls*"))):
        b = norm(os.path.basename(p))
        if b.startswith("~$") or "FATURAMENTO" not in b:
            continue
        ano = 2025 if "2025" in b else ANO
        d = _ler_excel(p, header=1)
        cols = list(d.columns)
        if "Cliente" not in cols or "Item" not in cols:
            print("  ! BELLIZ %s: colunas inesperadas" % os.path.basename(p)[:40])
            continue
        # os meses vem em PARES (Fat, Qtd) na ordem jan..dez; a linha 1 do
        # arquivo traz a data de cada par
        # A linha de datas repete a data para cada par (Fat, Qtd). Sem tirar a
        # repeticao, jan-jul virava jan-abr: cada mes era lido duas vezes e os
        # ultimos meses ficavam de fora. (21/08/2026.)
        crua = _ler_excel(p, header=None, nrows=1)
        datas = []
        for c in crua.iloc[0].tolist():
            if isinstance(c, (pd.Timestamp, datetime.datetime)):
                if not datas or datas[-1].month != c.month or datas[-1].year != c.year:
                    datas.append(c)
        cF = [c for c in cols if str(c).startswith("Fat")]
        d = d[d["Cliente"].notna()]
        d = d[d["Cliente"].astype(str).str.strip().str.upper() != "TOTALS"]
        for _, r in d.iterrows():
            cli = str(r.get("NomeCliente") or "").strip()
            canal = norm(r.get("Canal")).lower()
            cod = re.sub(r"\.0$", "", str(r["Item"]).strip())
            pnome = str(r.get("Descricao") or "").strip()
            fam = str(r.get("Familia") or "").strip()
            for k, c in enumerate(cF):
                v = num(r[c])
                if not v:
                    continue
                mi = datas[k].month - 1 if k < len(datas) else k
                regs.append((cli, canal, cod, pnome, fam, ano, mi, v))
        print("  BELLIZ   %s -> %d linhas" % (os.path.basename(p)[:46], len(d)))
    return regs


def bloco(regs):
    cli, prod, meses = _monta(regs)
    ult = meses[-1] if meses else -1
    clientes = []
    for c, a in cli.items():
        t26 = round(sum(a["m26"].values()), 2)
        t25 = round(sum(a["m25"].values()), 2)
        # mesmo periodo do ano anterior: so os meses que 2026 ja tem
        t25p = round(sum(v for m, v in a["m25"].items()
                         if ABREV.index(m) <= ult), 2)
        clientes.append({
            "nome": c, "canal": a["canal"],
            "m26": a["m26"], "m25": a["m25"],
            "t26": t26, "t25": t25, "t25p": t25p,
            "sk26": len(a["sk26"]), "sk25": len(a["sk25"]),
            # comprou no ULTIMO mes fechado?
            "ativo": (a["m26"].get(ABREV[ult], 0) > 0) if ult >= 0 else False})
    clientes.sort(key=lambda x: -x["t26"])

    produtos = []
    for cod, p in prod.items():
        produtos.append({"cod": cod, "nome": p["nome"], "familia": p["familia"],
                         "v26": round(p["v26"], 2), "v25": round(p["v25"], 2),
                         "m26": p["m26"],
                         "cli26": len(p["cli26"]), "cli25": len(p["cli25"])})
    produtos.sort(key=lambda x: -x["v26"])

    tot26 = sum(c["t26"] for c in clientes)
    # concentracao: quantos clientes fazem 80% da venda
    acc, n80 = 0, 0
    for c in clientes:
        if acc / tot26 >= 0.8 if tot26 else True:
            break
        acc += c["t26"]; n80 += 1
    return {"meses": [ABREV[m] for m in meses], "ult": ABREV[ult] if ult >= 0 else "",
            "clientes": clientes, "produtos": produtos,
            "tot26": round(tot26, 2),
            "tot25p": round(sum(c["t25p"] for c in clientes), 2),
            "tot25": round(sum(c["t25"] for c in clientes), 2),
            "n80": n80}


def main():
    simular = "--simular" in sys.argv
    print("=" * 74)
    print("  SELL IN — GRANADO e BELLIZ%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    out = {"atualizado_em": datetime.date.today().isoformat(), "empresas": {}}
    for emp, fn in (("GRANADO", ler_granado), ("BELLIZ", ler_belliz)):
        regs = fn()
        if not regs:
            print("  %-9s sem dado" % emp)
            continue
        b = bloco(regs)
        out["empresas"][emp] = b
        var = ((b["tot26"] / b["tot25p"] - 1) * 100) if b["tot25p"] else 0
        pararam = sum(1 for c in b["clientes"] if c["t25"] > 0 and c["t26"] == 0)
        print("  %-9s %s | %d clientes | %d produtos" %
              (emp, "-".join(b["meses"]), len(b["clientes"]), len(b["produtos"])))
        print("            R$ %s vs R$ %s no mesmo periodo (%+.1f%%) · "
              "%d clientes fazem 80%% · %d pararam de comprar"
              % (format(round(b["tot26"]), ",d").replace(",", "."),
                 format(round(b["tot25p"]), ",d").replace(",", "."),
                 var, b["n80"], pararam))

    if simular:
        tam = len(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        print("\ntamanho do bloco: %.2f MB" % (tam / 1024 / 1024))
        print("SIMULACAO — nada foi gravado.")
        return 0

    s = open(INDEX, encoding="utf-8").read()
    # `var` + window: ver nota em atualizar_mix_belliz.py — botao/variavel que
    # depende de escopo lexical ja custou uma sessao inteira de depuracao
    novo = ("var SELL_IN = " + json.dumps(out, ensure_ascii=False,
                                          separators=(",", ":")) +
            "; window.SELL_IN = SELL_IN;")
    marca = "var SELL_IN = "
    if marca in s:
        i = s.index(marca); j = s.index("\n", i)
        s = s[:i] + novo + s[j:]
    else:
        i = s.index("const MIX_MINIMO = ")
        s = s[:i] + novo + "\n" + s[i:]
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_sellin_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(s)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
