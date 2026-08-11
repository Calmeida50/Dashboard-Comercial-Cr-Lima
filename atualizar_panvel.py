#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_panvel.py — grava o SELL OUT da Panvel em DADOS_PANVEL.

Faltava: a Panvel so tinha conferidor (conferir_panvel.py, 4/4 sem
divergencia), sem gravador — por isso ficou parada em 6 meses enquanto os
outros clientes ja tinham julho.

Regras (ver conferir_panvel.py):
  - separa LOJA de C.Dig pela coluna `Origem Venda`
  - o valor vem como TEXTO ("'30.038,03'") em quase todos os meses
  - ignora os arquivos "POR LOJA" (outra familia, alimenta o ranking)
  - DIMED = PANVEL

Uso:
    python3 atualizar_panvel.py --simular
    python3 atualizar_panvel.py
"""
import os, re, sys, json, glob, shutil, datetime
import conferir_panvel as C

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
SIGLA = {"JANEIRO":"Jan","FEVEREIRO":"Fev","MARCO":"Mar","ABRIL":"Abr",
         "MAIO":"Mai","JUNHO":"Jun","JULHO":"Jul","AGOSTO":"Ago",
         "SETEMBRO":"Set","OUTUBRO":"Out","NOVEMBRO":"Nov","DEZEMBRO":"Dez"}


def bloco_panvel():
    s = open(INDEX, encoding="utf-8").read()
    i = s.find("const DADOS_PANVEL = ") + len("const DADOS_PANVEL = ")
    d = 0; j = i; ins = False; esc = False
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
    return s, i, j + 1, json.loads(s[i:j + 1])


def main():
    simular = "--simular" in sys.argv
    s, ini, fim, P = bloco_panvel()
    idx = C.arquivos()                 # {(empresa, mes): caminho}, sem "POR LOJA"

    empresas = sorted({e for (e, _m) in idx})
    print("=" * 70)
    print("  SELL OUT PANVEL%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 70)
    ok = div = 0
    novas = []

    for emp in empresas:
        antigo = P.get(emp, {})
        ant_m = {m.get("mes"): m for m in (antigo.get("monthly") or [])}
        monthly, tl, td = [], 0.0, 0.0
        for mes in C.MESES:
            p = idx.get((emp, mes))
            if not p:
                continue
            loja, dig, erro, loja_aa, dig_aa, prods = C.ler(p, detalhe=True)
            if erro:
                print("  ! %s %s: %s" % (emp, mes[:3], erro))
                continue
            sig = SIGLA[mes]
            tl += loja; td += dig
            # ATENCAO aos nomes reais dos campos: val26_loja / val26_cdig.
            # O ano anterior vem AGORA DO ARQUIVO (coluna 'Venda Efetiva Ano
            # Anterior'). Antes so era preservado o que ja existia no bloco —
            # por isso a PRUDENCE aparecia sem 2025 em todos os meses.
            a = ant_m.get(sig, {})
            antes = (a.get("val26_loja", 0) or 0) + (a.get("val26_cdig", 0) or 0)
            if a:
                if abs((loja + dig) - antes) > 0.05:
                    div += 1
                    print("  ! %s %s ja publicado divergiu: %.2f -> %.2f"
                          % (emp, sig, antes, loja + dig))
                else:
                    ok += 1
            else:
                print("  + %s %s = %s (loja %s | site %s)"
                      % (emp, sig, "{:,.2f}".format(loja + dig),
                         "{:,.2f}".format(loja), "{:,.2f}".format(dig)))
            item = {"mes": sig,
                    "val26_loja": round(loja, 2), "val26_cdig": round(dig, 2),
                    "val25_loja": round(loja_aa, 2), "val25_cdig": round(dig_aa, 2),
                    # produtos do mes: permite clicar no mes e ver o detalhe
                    "produtos": prods or []}
            monthly.append(item)

        if not monthly:
            continue
        if emp not in P:
            P[emp] = {"empresa": emp}
            novas.append(emp)
        P[emp]["monthly"] = monthly
        P[emp]["ytd_loja"] = round(tl, 2)
        P[emp]["ytd_cdig"] = round(td, 2)
        P[emp]["ytd_total"] = round(tl + td, 2)
        P[emp]["pct_loja"] = round(tl / (tl + td) * 100, 1) if (tl + td) else 0
        P[emp]["pct_cdig"] = round(td / (tl + td) * 100, 1) if (tl + td) else 0
        marca = "   << EMPRESA NOVA" if emp in novas else ""
        print("\n%-10s %d meses | loja %13s | site %12s | total %13s%s"
              % (emp, len(monthly), "{:,.2f}".format(tl),
                 "{:,.2f}".format(td), "{:,.2f}".format(tl + td), marca))

    print("\nmeses ja publicados: %d conferem, %d divergem" % (ok, div))
    if div:
        print("ABORTADO — divergencia em mes ja publicado.")
        return 2
    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_panvel_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    txt = json.dumps(P, ensure_ascii=False, separators=(",", ":"))
    open(INDEX, "w", encoding="utf-8").write(s[:ini] + txt + s[fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
