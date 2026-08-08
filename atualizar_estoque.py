#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_estoque.py — recalcula o bloco `estoque_sao_joao` a partir dos
arquivos do Drive.

Layout (4 colunas, ~67 mil linhas = produto x loja):
    Cod Ean | Desc_Produto | Desc_Filial | Estoque Qtde

REGRAS:
 1. descartar a linha de totalizacao (primeira, "Total" no Cod Ean)
 2. INCLUIR ativos E inativos, marcando cada produto com `ativo: true/false`.
    Decisao do Cristiano (08/08/2026): o inativo precisa aparecer porque
    impacta o dia de estoque geral do cliente — mas marcado, para nao se
    perder tempo analisando.
 3. `lojas`     = lojas com estoque > 0
    `lojas_rup` = lojas com estoque == 0 (ruptura naquela loja)
 4. `giro` vem do sell out (media dos ultimos meses) — a tela calcula
    cob = qtde / giro * 30 e o status:
       sem lojas com estoque -> ruptura
       cob < 30 -> baixo | 30 a 40 -> normal | > 40 -> alto

Uso:
    python3 atualizar_estoque.py --simular
    python3 atualizar_estoque.py [MES]        (default: mes mais recente)
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/ESTOQUE DOS PRINCIPAIS CLIENTES"
)
MESES = ["JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO",
         "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def mix_ativo(html):
    """le o MIX_ATIVO_SAO_JOAO do proprio index.html"""
    i = html.find("const MIX_ATIVO_SAO_JOAO")
    bl = html[i:i + 12000]
    mix = {}
    for m in re.finditer(r"'?([A-Z ]+)'?\s*:\s*new Set\(\[(.*?)\]\)", bl, re.S):
        mix[m.group(1).strip()] = {x.strip().strip('"')
                                   for x in m.group(2).split('","') if x.strip()}
    return mix


def arquivos(mes=None):
    """{empresa: caminho} do mes pedido, ou do mes mais recente disponivel"""
    achados = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xls*"), recursive=True):
        n = norm(os.path.basename(p))
        if "SAO JOAO" not in n or not n.startswith("ESTOQUE"):
            continue
        mm = next((m for m in MESES if m in n), None)
        if not mm:
            continue
        emp = n.replace("ESTOQUE", "").replace("SAO JOAO", "").replace(mm, "")
        # remove sufixos de copia "(1)", ano e extensao ANTES de usar como chave,
        # senao "ESTOQUE ... EVER GREEN JULHO 26 (1).xlsx" vira uma empresa
        # fantasma chamada "EVER GREEN (1)".
        emp = re.sub(r"\(\s*\d+\s*\)", " ", emp)
        emp = re.sub(r"\.(XLSX|XLS|XLSM)\b", " ", emp)
        emp = re.sub(r"\b(26|2026)\b", " ", emp)
        emp = re.sub(r"\s+", " ", emp).strip(" .-_")
        achados.setdefault(mm, {}).setdefault(emp, []).append(p)
    if not achados:
        return None, {}
    if mes:
        mes = norm(mes)
        if mes not in achados:
            return None, {}
    else:  # mes mais recente com arquivos
        mes = max(achados, key=lambda m: MESES.index(m))
    return mes, achados[mes]


def escolher(lista):
    """quando ha duplicata ('... (1).xlsx'), fica o mais recente e avisa"""
    if len(lista) == 1:
        return lista[0], None
    lista = sorted(lista, key=lambda p: os.path.getmtime(p), reverse=True)
    return lista[0], "%d arquivos para o mesmo mes; usando o mais recente: %s" % (
        len(lista), os.path.basename(lista[0]))


def ler(path, ativos):
    """devolve (produtos, total_lojas)"""
    d = pd.read_excel(path)
    cE = next((c for c in d.columns if "EAN" in norm(c)), None)
    cP = next((c for c in d.columns if "PRODUTO" in norm(c) and "COD" not in norm(c)), None)
    cF = next((c for c in d.columns if "FILIAL" in norm(c) and "COD" not in norm(c)), None)
    # ATENCAO: alguns arquivos tem 9 colunas, incluindo 'Estoque a Custo'
    # (dinheiro), 'Dias Estoque' e 'Giro 030 dias'. Pegar a primeira coluna
    # com "ESTOQUE" traz o CUSTO e multiplica a quantidade por ~10.
    cQ = next((c for c in d.columns
               if "QTDE" in norm(c) or "QUANTIDADE" in norm(c)), None)
    if cQ is None:
        cQ = next((c for c in d.columns if norm(c) == "ESTOQUE"), None)
    # giro e dias nativos, quando o arquivo trouxer
    cG = next((c for c in d.columns if "GIRO" in norm(c)), None)
    cD = next((c for c in d.columns if "DIAS" in norm(c)), None)
    if not all([cP, cF, cQ]):
        return None, 0
    d = d[d[cF].notna() & d[cP].notna()].copy()
    d = d[d[cF].astype(str).map(norm) != "TOTAL"]
    d["_q"] = pd.to_numeric(d[cQ], errors="coerce").fillna(0)
    d["_n"] = d[cP].astype(str).str.upper().str.strip()
    d["_g"] = pd.to_numeric(d[cG], errors="coerce").fillna(0) if cG else 0

    prods = []
    for nome, g in d.groupby("_n"):
        ean = str(g[cE].iloc[0]) if cE else ""
        item = {
            "ean": ean,
            "nome": nome,
            "lojas": int((g["_q"] > 0).sum()),
            "lojas_rup": int((g["_q"] == 0).sum()),
            "qtde": int(g["_q"].sum()),
            "ativo": (nome in ativos) if ativos else True,
        }
        if cG:                      # giro nativo do arquivo, quando houver
            item["giro"] = round(float(g["_g"].sum()), 2)
        prods.append(item)
    prods.sort(key=lambda x: -x["qtde"])
    return prods, int(d[cF].nunique())


def main():
    simular = "--simular" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    h = open("index.html", encoding="utf-8").read()
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
    D = json.loads(h[i:j + 1])
    MIX = mix_ativo(h)
    # giro por produto vem do sell out (avg3m ja calculado la)
    sj = D.get("sellout_sao_joao", {})

    mes, porEmp = arquivos(args[0] if args else None)
    if not mes:
        print("nenhum arquivo de estoque encontrado.")
        return 1

    print("=" * 74)
    print("  ESTOQUE SAO JOAO — %s/2026%s" % (mes, "  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    antigo = D.get("estoque_sao_joao", {})
    novo = {"periodo": antigo.get("periodo")}
    avisos = []

    for emp in sorted(porEmp):
        p, aviso = escolher(porEmp[emp])
        if aviso:
            avisos.append("%s: %s" % (emp, aviso))
        ativos = MIX.get(emp, set())
        prods, nlojas = ler(p, ativos)
        if prods is None:
            avisos.append("%s: layout nao reconhecido" % emp)
            continue
        avg = (sj.get(emp, {}) or {}).get("avg3m", {}) or {}
        avgU = {k.upper().strip(): v for k, v in avg.items()}
        for pr in prods:
            # O giro vem SEMPRE do sell out, que temos atualizado e no mesmo
            # criterio para todas as empresas. O giro nativo do arquivo de
            # estoque so existe em alguns layouts — usa-lo tornaria a cobertura
            # incomparavel entre empresas e meses. Fica so como fallback.
            g = avgU.get(pr["nome"])
            if g:
                pr["giro"] = round(float(g), 2)
            elif not pr.get("giro"):
                pr["giro"] = 0.0

        nat = sum(1 for x in prods if x["ativo"])
        qat = sum(x["qtde"] for x in prods if x["ativo"])

        # contadores de status — a tela os exibe no resumo por empresa.
        # Mesma regra do getStatusCob() (index.html ~8548):
        #   sem loja com estoque ou cobertura zero -> ruptura
        #   cob < 30 -> baixo | 30 a 40 -> normal | > 40 -> alto
        # Contamos apenas os ATIVOS: item fora de mix nao e ruptura comercial.
        nrup = nbai = nnor = nalt = 0
        for x in prods:
            if not x["ativo"]:
                continue
            giro = x.get("giro") or 0
            cob = (x["qtde"] / giro * 30) if giro else None
            x["cob"] = round(cob, 1) if cob is not None else None
            if x["lojas"] == 0 or not cob:
                x["st"] = "ruptura"; nrup += 1
            elif cob < 30:
                x["st"] = "baixo"; nbai += 1
            elif cob < 40:
                x["st"] = "normal"; nnor += 1
            else:
                x["st"] = "alto"; nalt += 1

        novo[emp] = {
            "tem_giro": any(x.get("giro") for x in prods),
            "total_lojas": nlojas,
            "total_produtos": nat,          # a tela usa isso no % de ruptura
            "total_produtos_geral": len(prods),
            "total_produtos_ativos": nat,
            "total_qtde": sum(x["qtde"] for x in prods),
            "total_qtde_ativos": qat,
            "n_ruptura": nrup, "n_baixo": nbai,
            "n_normal": nnor, "n_alto": nalt,
            "produtos": prods,
        }
        print("%-11s qtde %10s | produtos %3d (%d ativos, %d inativos) | lojas %d"
              % (emp, "{:,}".format(novo[emp]["total_qtde"]),
                 len(prods), nat, len(prods) - nat, nlojas))
        print("%-11s   status dos ativos: %d ruptura · %d baixo · %d normal · %d alto"
              % ("", nrup, nbai, nnor, nalt))

    if avisos:
        print("\nATENCAO:")
        for x in avisos:
            print("  ! %s" % x)

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    ult = {"JANEIRO":"01-31","FEVEREIRO":"02-28","MARCO":"03-31","ABRIL":"04-30",
           "MAIO":"05-31","JUNHO":"06-30","JULHO":"07-31","AGOSTO":"08-31",
           "SETEMBRO":"09-30","OUTUBRO":"10-31","NOVEMBRO":"11-30","DEZEMBRO":"12-31"}
    novo["periodo"] = "2026-" + ult.get(mes, "06-30")
    D["estoque_sao_joao"] = novo
    os.makedirs("_backups", exist_ok=True)
    bkp = "_backups/index.html.bak_estoque_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("index.html", bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open("index.html", "w", encoding="utf-8").write(h[:i] + txt + h[j + 1:])
    print("\ngravado (periodo %s). backup em %s" % (novo["periodo"], bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
