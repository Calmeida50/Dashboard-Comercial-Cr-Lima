#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_sellout.py — le os arquivos de sell out da Sao Joao e compara com o
que esta no dashboard. NAO grava nada.

Regras (ver ROTEIRO_AUTOMACAO.md, etapa 2):
  1. descartar a linha de totalizacao (sem Desc_Filial)
  2. devolucoes sao EXCLUIDAS, nao subtraidas (ignorar Vl Liquido negativo)
  3. comparar nomes de arquivo sempre normalizados (NFD no macOS)
"""
import os, re, glob, json
import pandas as pd
import coletar_faturamento as C   # reaproveita norm()

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["BELLIZ", "CLESS", "EVER GREEN", "GRANADO", "PAYOT", "PRUDENCE"]
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO"]
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun"]


def achar(empresa, mes, ano2):
    """acha o arquivo; compara tudo normalizado por causa do NFD do macOS"""
    alvo_emp = C.norm(empresa)
    alvo_mes = C.norm(mes)
    achados = []
    for p in glob.glob(os.path.join(DRIVE, "**", "*.xlsx"), recursive=True):
        n = C.norm(os.path.basename(p))
        if "SAO JOAO" not in n:
            continue
        if alvo_emp not in n or alvo_mes not in n:
            continue
        # o ano vem como sufixo de 2 digitos no nome (ex: JUNHO 26)
        if not re.search(r"\b%s\b" % ano2, n):
            continue
        achados.append(p)
    return achados


def ler(path):
    """devolve (valor, quantidade) aplicando as regras 1, 2 e 3"""
    d = pd.read_excel(path)
    col_fil = next((c for c in d.columns if "FILIAL" in C.norm(c)), None)
    col_prod = next((c for c in d.columns if "PRODUTO" in C.norm(c)
                     and "COD" not in C.norm(c)), None)
    # regra 3: SEMPRE liquido. Alguns arquivos trazem Vl Bruto junto — ignorar.
    col_val = next((c for c in d.columns if "LIQUID" in C.norm(c)), None)
    col_qtd = next((c for c in d.columns if "GIRO" in C.norm(c)), None)
    if col_val is None:
        return None, None, "coluna de valor liquido nao encontrada"
    # regra 1: descartar totalizacoes — o total geral (sem filial) e os
    # subtotais por loja (com filial, sem produto, como no arquivo da BELLIZ)
    if col_fil is not None:
        d = d[d[col_fil].notna()]
    if col_prod is not None:
        d = d[d[col_prod].notna()]
    v = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    mask = v > 0                            # regra 2: devolucao nao entra
    q = pd.to_numeric(d[col_qtd], errors="coerce").fillna(0) if col_qtd is not None else None
    return float(v[mask].sum()), (float(q[mask].sum()) if q is not None else None), None


def dashboard():
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
    return json.loads(h[i:j + 1])["sellout_sao_joao"]


def main():
    sj = dashboard()
    print("=" * 78)
    print("  CONFERENCIA SELL OUT SAO JOAO — arquivos vs dashboard")
    print("=" * 78)
    ok = div = falta = 0
    linhas_div = []
    for ano2, chave in (("25", "mensal_2025"), ("26", "mensal_2026")):
        print("\n--- 20%s" % ano2)
        print("%-11s %-5s %16s %16s %12s" % ("EMPRESA", "MES", "ARQUIVO", "DASHBOARD", "DIF"))
        for emp in EMPRESAS:
            bloco = sj.get(emp, {}).get(chave, {})
            for k, mes in enumerate(MESES):
                alvo = bloco.get(ABREV[k])
                arqs = achar(emp, mes, ano2)
                if not arqs:
                    falta += 1
                    txt = "{:,.2f}".format(alvo) if alvo else "-"
                    print("%-11s %-5s %16s %16s   sem arquivo"
                          % (emp, ABREV[k], "-", txt))
                    continue
                val, qtd, erro = ler(arqs[0])
                if erro:
                    falta += 1
                    print("%-11s %-5s   ERRO: %s" % (emp, ABREV[k], erro))
                    continue
                if alvo is None:
                    print("%-11s %-5s %16s %16s   (sem no dash)"
                          % (emp, ABREV[k], "{:,.2f}".format(val), "-"))
                    continue
                dif = val - alvo
                if abs(dif) < 0.05:
                    ok += 1
                else:
                    div += 1
                    linhas_div.append((emp, ABREV[k], ano2, val, alvo, dif))
                    print("%-11s %-5s %16s %16s %12s  DIVERGE"
                          % (emp, ABREV[k], "{:,.2f}".format(val),
                             "{:,.2f}".format(alvo), "{:,.2f}".format(dif)))
    print("\n" + "=" * 78)
    print("conferem: %d   divergem: %d   sem arquivo: %d" % (ok, div, falta))
    if not linhas_div:
        print("Nenhuma divergencia. As regras reproduzem o historico.")


if __name__ == "__main__":
    main()
