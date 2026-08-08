#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_nilo.py — grava o sell out da Nilo Tozzo no index.html.

Regras (conferidas 36/36 em conferir_nilo.py):
  - coluna de valor alterna entre 'Fat' e 'Total' conforme o mes
  - NAO confundir com 'Vl Tabela', 'Dif Total' nem 'Bnf'
  - a linha de totalizacao vem no TOPO, marcada na coluna 'Cod'
  - traz positivacao nativa na coluna 'Pos'
  - mes ja publicado que divergir ABORTA a gravacao
"""
import os, re, sys, json, shutil, datetime
import pandas as pd
import conferir_nilo as N


def main():
    simular = "--simular" in sys.argv
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
    nt = D.get("sellout_nilo_tozzo", {})
    idx = N.arquivos()

    print("=" * 68)
    print("  SELL OUT NILO TOZZO%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 68)
    ok = div = 0
    mudou = False
    for emp in N.EMPRESAS:
        bloco = nt.setdefault(emp, {})
        for ano2, chave in (("25", "mensal_2025"), ("26", "mensal_2026")):
            serie = bloco.setdefault(chave, {})
            pos = bloco.setdefault("positivacao_" + ("2025" if ano2 == "25" else "2026"), {})
            for k, mes in enumerate(N.MESES):
                p = idx.get((emp, mes, ano2))
                if not p:
                    continue
                fat, pv, erro = N.ler(p[0] if isinstance(p, list) else p)
                if erro:
                    print("  ! %s %s/%s: %s" % (emp, N.ABREV[k], ano2, erro))
                    continue
                ab = N.ABREV[k]
                antes = serie.get(ab)
                if antes is not None and abs(fat - antes) > 0.05:
                    div += 1
                    print("  ! %s %s/%s ja publicado divergiu: %.2f -> %.2f"
                          % (emp, ab, ano2, antes, fat))
                    continue
                if antes is None:
                    print("  + %s %s/%s = %s (pos %d)"
                          % (emp, ab, ano2, "{:,.2f}".format(fat), pv))
                    mudou = True
                else:
                    ok += 1
                serie[ab] = round(fat, 2)
                if pv:
                    pos[ab] = int(pv)

    print("\nja publicados: %d conferem, %d divergem" % (ok, div))
    if div:
        print("ABORTADO — divergencia em mes ja publicado.")
        return 2
    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    if not mudou:
        print("Nada novo.")
        return 0

    D["sellout_nilo_tozzo"] = nt
    os.makedirs("_backups", exist_ok=True)
    bkp = "_backups/index.html.bak_nilo_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("index.html", bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open("index.html", "w", encoding="utf-8").write(h[:i] + txt + h[j + 1:])
    print("\ngravado. backup em %s" % bkp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
