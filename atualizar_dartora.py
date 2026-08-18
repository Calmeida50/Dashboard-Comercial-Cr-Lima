#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_dartora.py — recalcula o bloco `sellout_dartora` e grava no index.html.

Regras validadas (88/88 sem divergencia — ver ROTEIRO_AUTOMACAO.md):
  1. o mes vem de DENTRO do arquivo, nunca do nome
  2. linha de total: celula "TOTAL" OU coluna de descricao vazia
  3. le .xlsx e .txt (largura fixa, Latin-1)
  4. o rotulo "bruto" de 2025 era erro de descricao — o valor sempre foi liquido

NOVO: positivacao por SKU e por mes (`Positivação` em 2025, `Qtd clientes` em
2026) = para quantos clientes o item foi vendido naquele mes.
ATENCAO: somar positivacao entre SKUs NAO da clientes unicos — da pares
item-cliente. Rotular como "positivacoes", nunca como "clientes".

Uso:
    python3 atualizar_dartora.py --simular
    python3 atualizar_dartora.py
"""
import os, re, sys, json, shutil, datetime
import pandas as pd
import conferir_dartora as D
from drive_io import ler_excel as _ler_excel, abrir_excel as _abrir_excel

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
ABREV = D.ABREV
MESES = D.MESES


def detalhe(path):
    """devolve lista de (produto, valor, qtd, positivacao) ja limpa"""
    if path.lower().endswith(".txt"):
        return _detalhe_txt(path)
    hdr = D._achar_hdr(path)
    if hdr is None:
        return []
    d = _ler_excel(path, header=hdr)
    eh_total = d.apply(lambda r: any(D.norm(x) in ("TOTAL", "TOTAL GERAL")
                                     for x in r.tolist()), axis=1)
    desc = next((c for c in d.columns if D.norm(c).startswith("DESC")), None)
    if desc is None:
        return []
    eh_total = eh_total | d[desc].isna()
    d = d[~eh_total]
    val = next((c for c in d.columns if "VALOR" in D.norm(c) or "VLR" in D.norm(c)), None)
    qtd = next((c for c in d.columns if D.norm(c).startswith("QTD")
                or "QUANTIDADE" in D.norm(c)), None)
    pos = next((c for c in d.columns if "POSITIVAC" in D.norm(c)
                or "CLIENT" in D.norm(c)), None)
    if val is None:
        return []
    out = []
    for _, r in d.iterrows():
        out.append((
            str(r[desc]).strip(),
            float(pd.to_numeric(r[val], errors="coerce") or 0),
            float(pd.to_numeric(r[qtd], errors="coerce") or 0) if qtd else 0.0,
            float(pd.to_numeric(r[pos], errors="coerce") or 0) if pos else 0.0,
        ))
    return out


def _detalhe_txt(path):
    """largura fixa: descricao, cod, quantidade, valor [, qtd clientes]"""
    txt = open(path, encoding="latin-1", errors="replace").read()
    re_item = re.compile(r"^\s+(.+?)\s{2,}(\d{4,}-\d)\s+(.*)$")
    out = []
    for l in txt.splitlines():
        it = re_item.match(l)
        if not it:
            continue
        nums = re.findall(r"-?[\d.]+,\d{2}|-?[\d.]+,\d{3}", it.group(3))
        if len(nums) < 2:
            continue
        def num(s):
            return float(s.replace(".", "").replace(",", "."))
        # [0]=quantidade [1]=valor  e, quando existe, [2]=qtd clientes
        pos = num(nums[2]) if len(nums) >= 3 else 0.0
        out.append((it.group(1).strip(), num(nums[1]), num(nums[0]), pos))
    return out


def coletar():
    """{(empresa, ano2, mes_abrev): [(prod, val, qtd, pos)]} + vendedores"""
    idx = D.arquivos()
    prod, vend = {}, {}
    for (emp, mes, ano2, tipo), lista in idx.items():
        p = lista[0]
        if tipo == "vendedor":
            try:
                d = _ler_excel(p)
                cn = next((c for c in d.columns if "VENDEDOR" in D.norm(c)), None)
                cv = next((c for c in d.columns if "VALOR" in D.norm(c)), None)
                if cn and cv:
                    for _, r in d.iterrows():
                        nome = str(r[cn]).strip()
                        if not nome or D.norm(nome) in ("NAN", "TOTAL"):
                            continue
                        v = float(pd.to_numeric(r[cv], errors="coerce") or 0)
                        vend.setdefault((emp, ano2), {})
                        vend[(emp, ano2)][nome] = vend[(emp, ano2)].get(nome, 0.0) + v
            except Exception:
                pass
            continue
        real = D.mes_do_arquivo(p)
        if real:
            m_real, a_real = real
            mes_k, ano_k = ABREV[m_real - 1], str(a_real)[-2:]
        else:
            mes_k, ano_k = ABREV[MESES.index(mes)], ano2
        linhas = detalhe(p)
        if linhas:
            prod[(emp, ano_k, mes_k)] = linhas
    return prod, vend


def montar(emp, prod, vend, antigo):
    novo = dict(antigo)
    m25 = {a: 0.0 for a in ABREV}
    m26 = {a: 0.0 for a in ABREV}
    pv = {}      # produto -> acumulados
    pos25 = {}   # produto -> {mes: positivacao}
    pos26 = {}
    tot_pos25 = {a: 0.0 for a in ABREV}
    tot_pos26 = {a: 0.0 for a in ABREV}

    for (e, ano2, mes), linhas in prod.items():
        if e != emp:
            continue
        alvo_m = m26 if ano2 == "26" else m25
        alvo_p = pos26 if ano2 == "26" else pos25
        alvo_t = tot_pos26 if ano2 == "26" else tot_pos25
        for nome, val, qtd, pos in linhas:
            alvo_m[mes] += val
            d = pv.setdefault(nome, {"val25": 0.0, "qtd25": 0.0,
                                     "val26": 0.0, "qtd26": 0.0})
            d["val" + ano2] += val
            d["qtd" + ano2] += qtd
            if pos:
                alvo_p.setdefault(nome, {})
                alvo_p[nome][mes] = alvo_p[nome].get(mes, 0.0) + pos
                alvo_t[mes] += pos

    # PRESERVACAO: mes que existe no dashboard mas nao tem arquivo mantem o
    # valor antigo. Sem isso, a BELLIZ perderia abril/2026 (o arquivo de abril
    # contem maio), apagando R$ 31.957,44 que hoje estao publicados.
    n25 = {a: round(v, 2) for a, v in m25.items() if v}
    n26 = {a: round(v, 2) for a, v in m26.items() if v}
    preservados = []
    for chave, novo_d in (("mensal_2025", n25), ("mensal_2026", n26)):
        for a, v in (antigo.get(chave) or {}).items():
            if a not in novo_d and v:
                novo_d[a] = v
                preservados.append("%s %s" % (chave[-4:], a))
    novo["mensal_2025"] = {a: n25[a] for a in ABREV if a in n25}
    novo["mensal_2026"] = {a: n26[a] for a in ABREV if a in n26}
    novo["_preservados"] = preservados

    novo["por_produto"] = sorted(
        [{"nome": n,
          "val26": round(d["val26"], 2), "qtd26": int(d["qtd26"]),
          "val25": round(d["val25"], 2), "qtd25": int(d["qtd25"]),
          "pos_2026": {k: int(v) for k, v in sorted(pos26.get(n, {}).items(),
                                                    key=lambda x: ABREV.index(x[0]))},
          "pos_2025": {k: int(v) for k, v in sorted(pos25.get(n, {}).items(),
                                                    key=lambda x: ABREV.index(x[0]))}}
         for n, d in pv.items()],
        key=lambda x: -x["val26"])

    # positivacoes totais por mes (pares item-cliente, NAO clientes unicos)
    novo["positivacoes_2025"] = {a: int(v) for a, v in tot_pos25.items() if v}
    novo["positivacoes_2026"] = {a: int(v) for a, v in tot_pos26.items() if v}

    v26 = vend.get((emp, "26"), {})
    v25 = vend.get((emp, "25"), {})
    novo["por_vendedor"] = sorted(
        [{"nome": n, "val26": round(v26.get(n, 0.0), 2), "val25": round(v25.get(n, 0.0), 2)}
         for n in set(v26) | set(v25)],
        key=lambda x: -x["val26"])
    return novo


def carregar():
    h = open(INDEX, encoding="utf-8").read()
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
    return h, i, j + 1, json.loads(h[i:j + 1])


def main():
    simular = "--simular" in sys.argv
    print("=" * 72)
    print("  SELL OUT DARTORA — recalculo%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 72)
    h, ini, fim, dados = carregar()
    da = dados["sellout_dartora"]
    prod, vend = coletar()

    for emp in D.EMPRESAS:
        antigo = da.get(emp, {})
        novo = montar(emp, prod, vend, antigo)
        a26 = sum(antigo.get("mensal_2026", {}).values())
        n26 = sum(novo["mensal_2026"].values())
        a25 = sum(antigo.get("mensal_2025", {}).values())
        n25 = sum(novo["mensal_2025"].values())
        print("\n%-11s 2026 %13s -> %13s   (%d meses)"
              % (emp, "{:,.2f}".format(a26), "{:,.2f}".format(n26),
                 len(novo["mensal_2026"])))
        print("            2025 %13s -> %13s   (%d meses)"
              % ("{:,.2f}".format(a25), "{:,.2f}".format(n25),
                 len(novo["mensal_2025"])))
        pos = novo.get("positivacoes_2026", {})
        print("            produtos %d | vendedores %d | positivacoes/mes 2026: %s"
              % (len(novo["por_produto"]), len(novo["por_vendedor"]),
                 ", ".join("%s=%d" % (k, v) for k, v in list(pos.items())[:7])))
        if novo.get("_preservados"):
            print("            PRESERVADOS (sem arquivo): %s"
                  % ", ".join(novo["_preservados"]))
        novo.pop("_preservados", None)
        da[emp] = novo

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_dartora_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    txt = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    open(INDEX, "w", encoding="utf-8").write(h[:ini] + txt + h[fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
