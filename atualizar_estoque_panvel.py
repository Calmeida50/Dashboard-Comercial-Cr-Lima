#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_estoque_panvel.py — recalcula o estoque dentro de `DADOS_PANVEL`.

A Panvel tem estrutura PROPRIA, fora do DADOS_EMBEDDED, e o arquivo mais rico
de todos (19 colunas):

    Periodo | Item - Codigo | Item - Nomenclatura Varejo | EAN |
    Filial - Uf | Filial - Codigo | Filial - Cidade |
    Qtd Est Loja | Qtd Est Cd EDS | Qtd Est Cd PRN |
    Item - Descricao Marca | ... | Est - Dias Sem Venda

Particularidades:
  - separa estoque de LOJA e de DOIS CDs (EDS e PRN) -> a tela mostra
    "EST. LOJAS" e "EST. CD" em cards distintos
  - traz `Est - Dias Sem Venda` por item/loja -> alimenta "Sem Venda +60 dias"
  - o giro vem do sell out (avg3m_map), como no resto do projeto

DIMED = PANVEL (mesmo cliente). Aceitar os dois nomes.

Uso:
    python3 atualizar_estoque_panvel.py --simular
    python3 atualizar_estoque_panvel.py [MES]
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/ESTOQUE DOS PRINCIPAIS CLIENTES"
)
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]
FIM = {"JANEIRO":"01-31","FEVEREIRO":"02-28","MARCO":"03-31","ABRIL":"04-30",
       "MAIO":"05-31","JUNHO":"06-30","JULHO":"07-31","AGOSTO":"08-31",
       "SETEMBRO":"09-30","OUTUBRO":"10-31","NOVEMBRO":"11-30","DEZEMBRO":"12-31"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def arquivos(mes=None):
    achados = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if not n.startswith("ESTOQUE"):
            continue
        if "PANVEL" not in n and "DIMED" not in n:   # DIMED = PANVEL
            continue
        mm = next((m for m in MESES if m in n), None)
        if not mm:
            continue
        emp = n.replace("ESTOQUE", "").replace("PANVEL", "").replace("DIMED", "")
        emp = emp.replace(mm, "")
        # QUALQUER coisa entre parenteses sai: era "(1)" das copias do Drive e
        # agora tambem "( 12.08 )", a data da coleta semanal que o Cristiano
        # passou a escrever no nome. Sem isso o coletor criou as empresas
        # fantasma "CLESS ( 12.08 )" em 13/08/2026.
        emp = re.sub(r"\([^)]*\)", " ", emp)
        emp = re.sub(r"\.(XLSX|XLS|XLSM)\b", " ", emp)
        emp = re.sub(r"\b(26|2026)\b", " ", emp)
        # sobra de data solta no nome, tipo "12.08" ou "12-08" sem parenteses
        emp = re.sub(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", " ", emp)
        emp = re.sub(r"\s+", " ", emp).strip(" .-_")
        achados.setdefault(mm, {}).setdefault(emp, []).append(p)
    if not achados:
        return None, {}
    if mes:
        mes = norm(mes)
        return (mes, achados.get(mes, {})) if mes in achados else (None, {})
    mes = max(achados, key=lambda m: MESES.index(m))
    return mes, achados[mes]


def ler(path, avg, avg_nome=None):
    """devolve (produtos, total_rede, sem_venda_60)"""
    d = _ler_excel(path)
    col = {norm(c): c for c in d.columns}
    def ache(*chaves, excl=()):
        for k, orig in col.items():
            if all(x in k for x in chaves) and not any(e in k for e in excl):
                return orig
        return None

    cCod  = ache("ITEM", "CODIGO", excl=("FORNECEDOR",))
    cNome = ache("NOMENCLATURA") or ache("ITEM", "NOME")
    cEan  = ache("EAN")
    cFil  = ache("FILIAL", "CODIGO")
    cCid  = ache("FILIAL", "CIDADE")
    cLoja = ache("EST", "LOJA")
    cCds  = [col[k] for k in col if "EST CD" in k or ("EST" in k and "CD" in k)]
    cDias = ache("DIAS", "SEM", "VENDA")
    if cNome is None or cLoja is None:
        return None, 0, [], {}

    d["_loja"] = pd.to_numeric(d[cLoja], errors="coerce").fillna(0)
    d["_cd"] = 0
    for c in cCds:
        d["_cd"] = d["_cd"] + pd.to_numeric(d[c], errors="coerce").fillna(0)
    d["_n"] = d[cNome].astype(str).str.strip()
    d = d[d["_n"].str.len() > 0]

    total_rede = int(d[cFil].nunique()) if cFil else 0
    # avg vem do sell out: chaveado por CODIGO. `avg_nome` e a reserva.
    avgCod = {str(k).strip(): v for k, v in (avg or {}).items()}
    avgU = {norm(k): v for k, v in (avg_nome or {}).items()}

    prods, semvenda = [], []
    # DISTRIBUICAO DE ESTOQUE por loja: quantas filiais tem 0, 1, 2, 3 ou 4+
    # unidades do item EM LOJA. Ate 13/08/2026 a tela chamava de "distribuicao
    # por loja" um dado que na verdade vinha do arquivo de VENDA por loja, em
    # faixas de quantidade VENDIDA — dizia "em estoque" e nao era.
    dist = {}
    for nome, g in d.groupby("_n"):
        qloja = int(g["_loja"].sum())
        # ATENCAO: o estoque de CD e da REDE, nao da loja — vem REPETIDO em
        # todas as linhas do mesmo produto. Somar multiplicaria pelo numero de
        # lojas (664x). Pegar o valor UMA vez por produto.
        qcd = int(g["_cd"].max())
        cod = str(g[cCod].iloc[0]) if cCod else ""
        cod = re.sub(r"\.0$", "", cod)
        item = {
            "cod": cod,
            "nome": nome,
            "ean": str(g[cEan].iloc[0]) if cEan else "",
            "qtde_lojas": qloja,
            "qtde_cd": qcd,
            "qtde": qloja + qcd,
            "lojas": int((g["_loja"] > 0).sum()),
            "lojas_rup": int((g["_loja"] == 0).sum()),
            # giro casa primeiro pelo CODIGO (chave real entre sell out e
            # estoque); o nome fica como reserva para arquivo sem codigo.
            "giro": round(float(avgCod.get(cod) or avgU.get(norm(nome)) or 0), 1),
        }
        un = g["_loja"]
        dist[cod or nome] = {
            "nome": nome,
            "n0": int((un == 0).sum()),
            "n1": int((un == 1).sum()),
            "n2": int((un == 2).sum()),
            "n3": int((un == 3).sum()),
            "n4": int((un >= 4).sum()),
        }
        if cDias is not None:
            dias = pd.to_numeric(g[cDias], errors="coerce").dropna()
            if len(dias):
                item["avg_dias_sem_venda"] = int(dias.mean())
                # "Sem venda +60 dias" e por PRODUTO, nao por produto x loja.
                # Contar cada linha daria ~15 mil em vez de ~100.
                paradas = g[pd.to_numeric(g[cDias], errors="coerce") > 60]
                if len(paradas):
                    semvenda.append({
                        "produto": nome,
                        "cod": item["cod"],
                        "lojas": int(len(paradas)),
                        "dias": int(pd.to_numeric(paradas[cDias], errors="coerce").max()),
                        "dias_medio": int(pd.to_numeric(paradas[cDias], errors="coerce").mean()),
                        "qtde": int(pd.to_numeric(paradas[cLoja], errors="coerce").fillna(0).sum()),
                    })
        prods.append(item)

    prods.sort(key=lambda x: -x["qtde"])
    semvenda.sort(key=lambda x: -x["dias"])
    return prods, total_rede, semvenda, dist


def main():
    simular = "--simular" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    s = open(os.path.join(PROJ, "index.html"), encoding="utf-8").read()
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

    mes, porEmp = arquivos(args[0] if args else None)
    if not mes:
        print("nenhum arquivo de estoque da Panvel encontrado.")
        return 1

    print("=" * 72)
    print("  ESTOQUE PANVEL — %s/2026%s" % (mes, "  [SIMULACAO]" if simular else ""))
    print("=" * 72)
    periodo = "2026-" + FIM.get(mes, "07-31")
    novas = []

    for emp in sorted(porEmp):
        caminho = sorted(porEmp[emp], key=os.path.getmtime, reverse=True)[0]
        antigo = P.get(emp, {})
        avg = (antigo.get("estoque", {}) or {}).get("avg3m_map", {})
        avg_nome = (antigo.get("estoque", {}) or {}).get("avg3m_nome", {})
        prods, rede, sv, dist = ler(caminho, avg, avg_nome)
        if prods is None:
            print("  ! %s: layout nao reconhecido" % emp)
            continue
        if emp not in P:
            P[emp] = {"empresa": emp}
            novas.append(emp)
        est_ant = (antigo.get("estoque") or {})
        P[emp]["estoque"] = {
            "total_rede": rede or est_ant.get("total_rede", 0),
            "periodo": periodo,
            # data REAL do arquivo, por empresa — a Panvel manda toda semana,
            # entao o fim do mes da pasta nao serve como "atualizado em".
            "atualizado_em": datetime.date.fromtimestamp(
                os.path.getmtime(caminho)).isoformat(),
            "arquivo": os.path.basename(caminho),
            "produtos": prods,
            "avg3m_map": avg,
            "avg3m_nome": avg_nome,
            "avg3m_meses": est_ant.get("avg3m_meses"),
            "dist_estoque": dist,
            "sem_venda_60": sv,
        }
        marca = "   << EMPRESA NOVA" if emp in novas else ""
        print("  %-10s %4d SKUs | lojas %5d | est.loja %9s | est.CD %9s | sem venda>60d %4d%s"
              % (emp, len(prods), rede,
                 "{:,}".format(sum(x["qtde_lojas"] for x in prods)),
                 "{:,}".format(sum(x["qtde_cd"] for x in prods)),
                 len(sv), marca))
        if est_ant.get("periodo"):
            print("  %-10s   periodo %s -> %s" % ("", est_ant["periodo"], periodo))

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_estpanvel_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(os.path.join(PROJ, "index.html"), bkp)
    txt = json.dumps(P, ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(PROJ, "index.html"), "w", encoding="utf-8").write(
        s[:ini] + txt + s[j + 1:])
    print("\ngravado (periodo %s). backup em _backups/%s"
          % (periodo, os.path.basename(bkp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
