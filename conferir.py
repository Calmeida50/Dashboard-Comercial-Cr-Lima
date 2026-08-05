#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conferir.py — roda o coletor num mes fechado e compara com o dashboard."""
import re, json, sys, os
import coletar_faturamento as C

IDX = {m: i for i, m in enumerate(C.MESES)}

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
    return json.loads(h[i:j+1])

def main():
    mes = (sys.argv[1] if len(sys.argv) > 1 else "JUNHO").upper()
    ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    k = IDX[C.norm(mes)]
    emp = dashboard().get("empresas", {})
    _, res, probs = C.coletar(mes, ano)

    print("=" * 74)
    print("  CONFERENCIA %s/%s — coletor vs dashboard" % (mes, ano))
    print("=" * 74)
    print("%-12s %16s %16s %14s" % ("EMPRESA", "COLETOR", "DASHBOARD", "DIFERENCA"))
    print("-" * 74)
    ok = falha = 0
    for e in sorted(set(list(res.keys()) + [x for x in emp if x != "GERAL"])):
        chave = "BOTÂNICA" if e == "BOTANICA" else e
        alvo = emp.get(chave, {}).get("real", [0]*12)
        alvo = alvo[k] if len(alvo) > k else 0.0
        got = res[e]["vendas"] if e in res else None
        if got is None:
            print("%-12s %16s %16s   %s" % (e, "sem arquivo", "{:,.2f}".format(alvo), "-"))
            continue
        dif = got - alvo
        marca = "OK" if abs(dif) < 0.05 else "DIVERGE"
        if abs(dif) < 0.05: ok += 1
        else: falha += 1
        print("%-12s %16s %16s %14s  %s" % (
            e, "{:,.2f}".format(got), "{:,.2f}".format(alvo), "{:,.2f}".format(dif), marca))
    print("-" * 74)
    print("conferem: %d   divergem: %d" % (ok, falha))
    if probs:
        print("\nobservacoes:")
        for p in probs: print("  - %s" % p)

if __name__ == "__main__":
    main()
