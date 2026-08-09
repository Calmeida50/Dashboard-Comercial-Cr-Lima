#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_vendedores.py — reconstroi os blocos por CLIENTE e por VENDEDOR a
partir dos arquivos de faturamento do Drive.

Blocos afetados:
    clientes_detalhado[EMPRESA][VENDEDOR][] = {nome, cod, meses[12], meses25[12]}
    acomp_vendas[VENDEDOR][MES][EMPRESA]    = {hist, obj, real}
    vendedores[NOME]                        = {hist, obj, real}

ATRIBUICAO — tres camadas, da mais forte para a mais fraca:
    1. coluna do proprio arquivo ('Vendedor' na PRUDENCE, 'Representante' na
       BELLIZ/FIAT LUX/KISABOR) — vem do sistema do fabricante
    2. equivalencias.py (revisao manual do Cristiano)
    3. o que ja esta no clientes_detalhado (cadastro atual)

SO MEXE EM 2026. O historico de 2025 (`meses25`, `hist`) e PRESERVADO — foi
corrigido manualmente e nao deve ser reprocessado.

Uso:
    python3 atualizar_vendedores.py --simular
    python3 atualizar_vendedores.py
"""
import os, re, sys, json, glob, shutil, datetime, unicodedata
import pandas as pd
import coletar_faturamento as C
import equivalencias as E

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
MES_JS = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
          "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


def chave(nome):
    """normaliza para comparar nomes de cliente entre fontes"""
    s = unicodedata.normalize("NFKD", str(nome or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).upper().strip()
    s = re.sub(r"^\d+\s*[-–]\s*", "", s)
    s = re.sub(r"\s*[-–]\s*\d+\s*$", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(LTDA|SA|S A|ME|EPP|EIRELI|CIA|COMERCIO|COM|IND|INDUSTRIA|"
               r"DISTRIBUIDORA|DISTRIB|DE|DA|DO|E)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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


def cadastro_atual(D):
    """{empresa: {chave_cliente: (vendedor, nome_exibido, cod)}} vindo do que
    ja esta publicado — e a 3a camada de atribuicao"""
    cad = {}
    for emp, vends in (D.get("clientes_detalhado") or {}).items():
        m = {}
        for v, lista in vends.items():
            for c in lista:
                m[chave(c["nome"])] = (v, c["nome"], c.get("cod", ""))
        cad[emp] = m
    return cad


def buscar_cadastro(cad_emp, ch):
    """acha o cliente no cadastro tolerando nome truncado.

    O arquivo e o cadastro cortam o nome em pontos diferentes:
        arquivo  'UNIDASUL DISTRIB'
        cadastro 'UNIDASUL DISTRIB ALIMENTICIA S/A'
        arquivo  'PRONTO DOCE SOLUCAO EM DISTRIBUICAO DE ALIMENT'
        cadastro 'PRONTO DOCE SOLUCAO EM DISTRIB'
    Exigir igualdade exata deixava 42% do faturamento sem vendedor, embora o
    cliente ESTIVESSE cadastrado."""
    if not ch:
        return None
    reg = cad_emp.get(ch)
    if reg:
        return reg
    # um contem o outro (nome truncado dos dois lados)
    melhor, tam = None, 0
    for k, v in cad_emp.items():
        if not k or len(k) < 6:
            continue
        if k.startswith(ch) or ch.startswith(k) or k in ch or ch in k:
            # fica com o casamento de maior sobreposicao
            n = min(len(k), len(ch))
            if n > tam:
                melhor, tam = v, n
    if melhor:
        return melhor
    # ultimo recurso: similaridade alta
    from difflib import SequenceMatcher
    melhor, sc = None, 0.0
    for k, v in cad_emp.items():
        if not k or len(k) < 6:
            continue
        r = SequenceMatcher(None, ch, k).ratio()
        if r > sc:
            melhor, sc = v, r
    return melhor if sc >= 0.90 else None


def ler_notas(path, empresa):
    """devolve [(cliente, valor, vendedor_do_arquivo|None)] ja sem bonificacao
    e sem linha de total. Reaproveita a deteccao validada do coletor."""
    hdr = C.achar_cabecalho(path)
    if hdr is None:
        return []
    d = pd.read_excel(path, header=hdr)
    d = d.loc[:, [c for c in d.columns if not str(c).startswith("Unnamed")]]
    d = d.dropna(how="all")
    if d.empty:
        return []

    # coluna de valor: mesma regra do coletor
    cand = []
    for i, c in enumerate(d.columns):
        if str(d[c].dtype).startswith("datetime"):
            continue
        s = C.score_col(c)
        if s > 0:
            cand.append((s, i, c))
    if not cand:
        return []
    cand.sort(key=lambda t: (t[0], t[1]))
    col_val = cand[-1][2]

    # coluna de cliente: textual
    col_cli, melhor = None, -1
    for c in d.columns:
        n = C.norm(c)
        if "PRODUTO" in n or n.startswith("COD"):
            continue
        if not any(t in n for t in ("CLIENTE", "RAZAO", "CONTA", "NOME", "FILIAL")):
            continue
        am = d[c].dropna().astype(str).head(60)
        if am.empty:
            continue
        pct = sum(1 for x in am if re.search(r"[A-Za-z]{3}", x)) / len(am)
        if pct > 0.7 and pct > melhor:
            melhor, col_cli = pct, c
    if col_cli is None:
        return []

    # coluna de vendedor na origem (1a camada) — SO nas empresas em que ela
    # realmente traz o vendedor. Nas demais, 'Representante' e o codigo da
    # representacao (a propria Cr Lima) e contaminaria a atribuicao.
    col_vend = None
    if empresa in E.EMPRESAS_COM_VENDEDOR_NA_ORIGEM:
        col_vend = next((c for c in d.columns
                         if C.norm(c) in E.COLUNAS_VENDEDOR), None)

    # so vendas
    for c in d.columns:
        n = C.norm(c)
        if "OPERACAO" in n or "TIPO" in n:
            am = " ".join(C.norm(x) for x in d[c].dropna().astype(str).head(50))
            if "VEND" in am or "BONIF" in am:
                d = d[~d[c].astype(str).map(C.norm).str.contains("BONIF", na=False)]
                break

    out = []
    for _, r in d.iterrows():
        nome = str(r[col_cli]).strip()
        if not nome or C.norm(nome) in E.LIXO:
            continue
        val = C.to_num(r[col_val])
        if val == 0:
            continue
        vend = None
        if col_vend is not None and pd.notna(r[col_vend]):
            cand_v = str(r[col_vend]).strip().upper()
            # barreira: so aceita nome que seja de vendedor conhecido
            if cand_v in E.VENDEDORES_VALIDOS:
                vend = cand_v
        out.append((nome, val, vend))
    return out


def coletar(D, ate_mes=12):
    """{(empresa, vendedor, chave_cliente): {nome, cod, meses[12]}} + relatorio"""
    cad = cadastro_atual(D)
    acc, sem_vend = {}, {}
    for k in range(ate_mes):
        pasta = C.pasta_mes(MESES[k], 2026)
        if not pasta:
            continue
        for f in sorted(os.listdir(pasta)):
            if f.startswith(".") or f.startswith("~$"):
                continue
            p = os.path.join(pasta, f)
            if not os.path.isfile(p):
                continue
            emp = C.identificar_empresa(f)
            if not emp:
                continue
            empk = "BOTÂNICA" if emp == "BOTANICA" else emp
            for nome, val, vend_arq in ler_notas(p, empk):
                canon = E.canonico(nome)
                if canon is None:            # lixo
                    continue
                ch = chave(canon)
                # --- 3 camadas de atribuicao
                vend = None
                if vend_arq:                                   # 1. arquivo
                    vend = vend_arq
                if not vend:                                   # 2. equivalencias
                    vend = E.vendedor_de(empk, canon)
                reg = buscar_cadastro(cad.get(empk, {}), ch)
                if not vend and reg:                           # 3. cadastro
                    vend = reg[0]
                if not vend:
                    a = sem_vend.setdefault((empk, canon), 0.0)
                    sem_vend[(empk, canon)] = a + val
                    continue
                vend = vend.upper()
                exib = reg[1] if reg else canon
                cod = reg[2] if reg else ""
                d = acc.setdefault((empk, vend, ch),
                                   {"nome": exib, "cod": cod, "meses": [0.0] * 12})
                d["meses"][k] += val
    return acc, sem_vend


def cobertura(D, acc, ate_mes):
    """compara o total atribuido com o bloco `empresas` (fonte ja validada)"""
    emp_b = D["empresas"]
    linhas = []
    for empk in sorted({e for (e, _v, _c) in acc}):
        s = sum(sum(d["meses"][:ate_mes]) for (e, _v, _c), d in acc.items() if e == empk)
        t = sum((emp_b.get(empk, {}).get("real") or [0] * 12)[:ate_mes])
        linhas.append((empk, s, t, t - s, (t - s) / t * 100 if t else 0))
    return linhas


def main():
    simular = "--simular" in sys.argv
    _h, _i, _j, D = carregar()
    # ate qual mes ha faturamento fechado
    real = D["empresas"]["GERAL"]["real"]
    ate = max([k + 1 for k, v in enumerate(real) if v], default=0)
    print("=" * 76)
    print("  ATRIBUICAO POR VENDEDOR — jan a %s/2026%s"
          % (MESES[ate - 1].title(), "  [SIMULACAO]" if simular else ""))
    print("=" * 76)

    acc, sem_vend = coletar(D, ate)
    print("\nCOBERTURA (atribuido vs faturamento do bloco `empresas`)\n")
    print("%-11s %15s %15s %14s %7s" % ("EMPRESA", "ATRIBUIDO", "FATURAMENTO", "FALTA", "%"))
    tot_s = tot_t = 0
    for empk, s, t, falta, pct in cobertura(D, acc, ate):
        tot_s += s; tot_t += t
        marca = "" if abs(pct) < 0.5 else ("  <<" if abs(pct) >= 3 else "  <")
        print("%-11s %15s %15s %14s %6.1f%%%s"
              % (empk, "{:,.2f}".format(s), "{:,.2f}".format(t),
                 "{:,.2f}".format(falta), pct, marca))
    print("%-11s %15s %15s %14s %6.1f%%"
          % ("TOTAL", "{:,.2f}".format(tot_s), "{:,.2f}".format(tot_t),
             "{:,.2f}".format(tot_t - tot_s),
             (tot_t - tot_s) / tot_t * 100 if tot_t else 0))

    if sem_vend:
        print("\nAINDA SEM VENDEDOR (%d clientes, R$ %s):"
              % (len(sem_vend), "{:,.2f}".format(sum(sem_vend.values()))))
        for (e, n), v in sorted(sem_vend.items(), key=lambda x: -x[1])[:15]:
            print("   %-11s %-46s R$ %12s" % (e, n[:46], "{:,.2f}".format(v)))

    print("\n%d pares (empresa, vendedor, cliente)" % len(acc))
    vends = sorted({v for (_e, v, _c) in acc})
    print("vendedores encontrados: %s" % ", ".join(vends))
    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    print("\n[gravacao ainda nao implementada — rode com --simular]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
