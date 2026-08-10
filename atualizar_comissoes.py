#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_comissoes.py — recalcula os blocos de comissao a partir do
`clientes_detalhado` (que ja foi reconstruido dos arquivos do Drive).

Blocos:
    comissoes_resumo[VEND][MES]   = {fat, com, cv}
    comissoes_vendedor[VEND][MES] = cv         (comissao do vendedor)
    comissoes_empresa[EMP][MES]   = faturamento da empresa
    comissoes_detalhe[VEND][MES][EMP] = [{nome, fat, com, cv, status, ...}]

REGRAS (confirmadas pelo Cristiano em 04/08/2026):

  percentual por EMPRESA:
    GRANADO, PRUDENCE, BELLIZ, KISABOR, PAYOT, DEPIMIEL = 5,0%
    EVER GREEN, FIAT LUX = 3,0%
    AQUAFAST = 1,5%
    CLESS, BOTANICA = sem comissao

  rateio do VENDEDOR sobre a comissao da empresa:
    CRISTIANO e EDIMAR = 100%
    todos os demais     = 60%

SO MEXE DE JUNHO EM DIANTE (corte.py). Jan-mai fica como esta.
O campo `status`/`com_pago` do detalhe e PRESERVADO quando ja existia — e
controle de pagamento, nao se recalcula.
"""
import os, re, sys, json, shutil, datetime
import corte

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

PCT_EMPRESA = {
    "GRANADO": 0.05, "PRUDENCE": 0.05, "BELLIZ": 0.05, "KISABOR": 0.05,
    "PAYOT": 0.05, "DEPIMIEL": 0.05,
    "EVER GREEN": 0.03, "FIAT LUX": 0.03,
    "AQUAFAST": 0.015,
    "CLESS": 0.0, "BOTÂNICA": 0.0, "BOTANICA": 0.0,
}
FATOR_100 = {"CRISTIANO", "EDIMAR"}


def fator_vendedor(nome):
    return 1.0 if (nome or "").upper() in FATOR_100 else 0.60


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
    h, ini, fim, D = carregar()
    cd = D.get("clientes_detalhado") or {}
    ate = 0
    for x in (D.get("empresas", {}).get("GERAL", {}).get("real") or []):
        ate += 1 if x else 0
    ate = max(ate, corte.IDX_CORTE + 1)

    print("=" * 72)
    print("  COMISSOES — recalculo de %s ate %s%s"
          % (MESES[corte.IDX_CORTE][:3], MESES[ate - 1][:3],
             "  [SIMULACAO]" if simular else ""))
    print("=" * 72)

    resumo = D.setdefault("comissoes_resumo", {})
    porvend = D.setdefault("comissoes_vendedor", {})
    poremp = D.setdefault("comissoes_empresa", {})
    detalhe = D.setdefault("comissoes_detalhe", {})

    # detalhe antigo: preserva status de pagamento por (vend, mes, emp, cliente)
    pagos = {}
    for v, meses in (detalhe or {}).items():
        for mk, emps in (meses or {}).items():
            for e, lst in (emps or {}).items():
                for it in (lst or []):
                    pagos[(v, mk, e, it.get("nome", ""))] = (
                        it.get("status", "ABERTO"),
                        it.get("com_pago", 0),
                        it.get("mes_pago", ""))

    mudou = []
    for k in range(corte.IDX_CORTE, ate):
        mk = MESES[k]
        # zera o mes nos blocos que vamos reescrever
        acum_v = {}
        acum_e = {}
        det_mes = {}
        for emp, vends in cd.items():
            pct = PCT_EMPRESA.get(emp.upper())
            if pct is None:
                print("   ! sem percentual definido para %s — tratado como 0" % emp)
                pct = 0.0
            for vend, lista in vends.items():
                for c in lista:
                    fat = (c.get("meses") or [0.0] * 12)[k]
                    if not fat:
                        continue
                    com = fat * pct
                    cv = com * fator_vendedor(vend)
                    a = acum_v.setdefault(vend, {"fat": 0.0, "com": 0.0, "cv": 0.0})
                    a["fat"] += fat; a["com"] += com; a["cv"] += cv
                    acum_e[emp] = acum_e.get(emp, 0.0) + fat
                    st, cp, mp = pagos.get((vend, mk, emp, c.get("nome", "")),
                                           ("ABERTO", 0, ""))
                    det_mes.setdefault(vend, {}).setdefault(emp, []).append({
                        "nome": c.get("nome", ""),
                        "fat": round(fat, 2),
                        "com": round(com, 2),
                        "cv": round(cv, 2),
                        "status": st, "com_pago": cp, "mes_pago": mp,
                    })

        for vend, a in acum_v.items():
            antes = (resumo.get(vend, {}) or {}).get(mk, {}) or {}
            resumo.setdefault(vend, {})[mk] = {
                "fat": round(a["fat"], 2),
                "com": round(a["com"], 2),
                "cv": round(a["cv"], 2)}
            porvend.setdefault(vend, {})[mk] = round(a["cv"], 2)
            if abs((antes.get("fat") or 0) - a["fat"]) > 0.05:
                mudou.append("%s %s: fat %s -> %s"
                             % (vend, mk[:3],
                                "{:,.2f}".format(antes.get("fat") or 0),
                                "{:,.2f}".format(a["fat"])))
        for emp, v in acum_e.items():
            poremp.setdefault(emp, {})[mk] = round(v, 2)
        for vend, emps in det_mes.items():
            detalhe.setdefault(vend, {})[mk] = emps

        tot_fat = sum(a["fat"] for a in acum_v.values())
        tot_com = sum(a["com"] for a in acum_v.values())
        tot_cv = sum(a["cv"] for a in acum_v.values())
        print("  %-10s fat %14s | com %12s | cv %12s"
              % (mk[:3], "{:,.2f}".format(tot_fat),
                 "{:,.2f}".format(tot_com), "{:,.2f}".format(tot_cv)))

    if mudou:
        print("\n  mudancas (%d):" % len(mudou))
        for x in mudou[:12]:
            print("    - %s" % x)

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_comissoes_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    txt = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    open(INDEX, "w", encoding="utf-8").write(h[:ini] + txt + h[fim:])
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
