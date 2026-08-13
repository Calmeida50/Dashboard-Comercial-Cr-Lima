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

        # ── VENDA MEDIA MENSAL: janela movel dos 3 ULTIMOS MESES FECHADOS ──
        # Ate 13/08/2026 esse campo estava CONGELADO em abr-jun: nenhum script
        # o calculava, todos apenas preservavam (mesmo caso do cobertura_mensal).
        # Criterio definido pelo Cristiano: LOJA + SITE somados. O estoque fica
        # na loja e abastece tambem a venda do site, entao dividir a cobertura
        # por so uma parte inflaria o numero.
        # A chave e o CODIGO do item, que e como o estoque e a distribuicao
        # casam. Cai para o nome quando o arquivo nao trouxer codigo.
        # O MES CORRENTE FICA DE FORA, mesmo com arquivo ja salvo: a analise
        # semanal grava agosto parcial, e um mes pela metade derrubaria a
        # media — a cobertura pareceria melhor do que e. A media so vira
        # quando o mes fecha.
        hoje = datetime.date.today()
        sig_corrente = SIGLA[C.MESES[hoje.month - 1]] if hoje.year == 2026 else None
        fechados = [m for m in monthly if m["mes"] != sig_corrente]
        ult3 = fechados[-3:]
        avg, avg_nome = {}, {}
        for m in ult3:
            for p_ in (m.get("produtos") or []):
                q = p_.get("qtd") or 0
                if p_.get("cod"):
                    avg[p_["cod"]] = avg.get(p_["cod"], 0) + q
                avg_nome[p_["nome"]] = avg_nome.get(p_["nome"], 0) + q
        n3 = len(ult3) or 1
        avg = {k: round(v / n3, 1) for k, v in avg.items()}
        avg_nome = {k: round(v / n3, 1) for k, v in avg_nome.items()}
        est_ant = P[emp].get("estoque") or {}
        est_ant["avg3m_map"] = avg
        est_ant["avg3m_nome"] = avg_nome
        est_ant["avg3m_meses"] = [m["mes"] for m in ult3]
        P[emp]["estoque"] = est_ant
        print("     venda media (%s): %d itens por codigo, %d por nome"
              % ("+".join(m["mes"] for m in ult3), len(avg), len(avg_nome)))

        # `produtos` = acumulado do ano por SKU, montado a partir dos meses.
        # Sem isso a empresa nova (CLESS) ficava com a lista VAZIA e a tela
        # acabava mostrando os produtos da empresa anterior.
        acc = {}
        for m in monthly:
            for p_ in (m.get("produtos") or []):
                a = acc.setdefault(p_["nome"], {"nome": p_["nome"], "val26": 0.0,
                                                "val25": 0.0, "qtd26": 0,
                                                "val26_loja": 0.0, "val26_cdig": 0.0})
                a["val26"] += p_.get("val", 0.0)
                a["val25"] += p_.get("val_aa", 0.0)
                a["qtd26"] += p_.get("qtd", 0)
                a["val26_loja"] += p_.get("val_loja", 0.0)
                a["val26_cdig"] += p_.get("val_cdig", 0.0)
        antigos = {x.get("nome"): x for x in (antigo.get("produtos") or [])}
        prods = []
        for nome, a in acc.items():
            item = {"nome": nome,
                    "val26": round(a["val26"], 2),
                    "val25": round(a["val25"], 2),
                    "qtd26": int(a["qtd26"]),
                    "val26_loja": round(a["val26_loja"], 2),
                    "val26_cdig": round(a["val26_cdig"], 2)}
            # preserva o que so o carregamento antigo tinha
            v = antigos.get(nome) or {}
            for k in ("cod", "marca", "qtd26_loja", "qtd26_cdig"):
                if k in v:
                    item[k] = v[k]
            prods.append(item)
        prods.sort(key=lambda x: -x["val26"])
        if prods:
            P[emp]["produtos"] = prods
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
