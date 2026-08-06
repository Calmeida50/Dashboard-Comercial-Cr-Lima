#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_faturamento.py — grava no index.html o faturamento do mes corrente
lido do Drive.

Atualiza APENAS o bloco `empresas` (real[mes] por empresa + GERAL).
Nao toca em comissoes_empresa: aquele bloco e conferencia da Ever Green,
nao faturamento. Ver ROTEIRO_AUTOMACAO.md.

Trava de seguranca: antes de gravar, reprocessa um mes ja fechado e compara
com o que esta no dashboard. Se divergir, aborta sem escrever — significa que
o parser deixou de reproduzir o historico.

Uso:
    python3 atualizar_faturamento.py                 # mes corrente
    python3 atualizar_faturamento.py JULHO 2026
    python3 atualizar_faturamento.py --simular       # so mostra, nao grava
"""
import os, re, sys, json, shutil, datetime
import coletar_faturamento as C

PROJ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PROJ, "index.html")
MES_CONFERENCIA = ("JUNHO", 2026)     # mes fechado usado como prova
TOLERANCIA = 0.05                      # centavos de arredondamento

# nome no coletor -> chave no DADOS_EMBEDDED
CHAVE = {"BOTANICA": "BOTÂNICA"}


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


def gravar(h, ini, fim, dados):
    novo = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    return h[:ini] + novo + h[fim:]


def conferir(dados):
    """reprocessa um mes fechado; devolve lista de divergencias"""
    mes, ano = MES_CONFERENCIA
    k = C.MESES.index(C.norm(mes))
    _, res, _ = C.coletar(mes, ano)
    if not res:
        return ["mes de conferencia %s/%s nao pode ser lido" % (mes, ano)]
    ruins = []
    for emp, r in res.items():
        chave = CHAVE.get(emp, emp)
        real = dados["empresas"].get(chave, {}).get("real", [])
        alvo = real[k] if len(real) > k else None
        if alvo is None:
            ruins.append("%s: ausente no dashboard" % emp)
            continue
        dif = r["vendas"] - alvo
        if abs(dif) > TOLERANCIA:
            ruins.append("%s: coletor %.2f vs dashboard %.2f (dif %.2f)"
                         % (emp, r["vendas"], alvo, dif))
    return ruins


def aplicar(dados, res, k):
    """escreve real[k] das empresas coletadas e recalcula o GERAL"""
    mudancas = []
    for emp, r in sorted(res.items()):
        chave = CHAVE.get(emp, emp)
        bloco = dados["empresas"].get(chave)
        if bloco is None:
            mudancas.append((emp, None, None, "empresa ausente do dashboard"))
            continue
        real = bloco.setdefault("real", [0.0] * 12)
        while len(real) < 12:
            real.append(0.0)
        antes = real[k]
        depois = round(r["vendas"], 2)
        if abs(antes - depois) > 0.004:
            real[k] = depois
            mudancas.append((emp, antes, depois, None))

    # GERAL = soma das empresas (validado contra junho/2026)
    total = 0.0
    for e, b in dados["empresas"].items():
        if e == "GERAL":
            continue
        r = b.get("real", [])
        if len(r) > k:
            total += r[k]
    g = dados["empresas"].setdefault("GERAL", {}).setdefault("real", [0.0] * 12)
    while len(g) < 12:
        g.append(0.0)
    antes_g = g[k]
    g[k] = round(total, 2)
    return mudancas, antes_g, g[k]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    simular = "--simular" in sys.argv
    if len(args) >= 2:
        mes, ano = args[0].upper(), int(args[1])
    else:
        hoje = datetime.date.today()
        mes, ano = C.MESES[hoje.month - 1], hoje.year
    k = C.MESES.index(C.norm(mes))

    print("=" * 70)
    print("  ATUALIZAR FATURAMENTO — %s/%s%s" % (mes, ano, "  [SIMULACAO]" if simular else ""))
    print("=" * 70)

    h, ini, fim, dados = carregar()

    # --- trava: o parser ainda reproduz o historico?
    print("\n[1/3] conferindo contra %s/%s..." % MES_CONFERENCIA)
    ruins = conferir(dados)
    if ruins:
        print("      ABORTADO — o coletor divergiu do historico:")
        for r in ruins:
            print("        ! %s" % r)
        print("\n      Nada foi gravado. Investigar antes de rodar de novo.")
        return 2
    print("      ok, historico reproduzido sem divergencia")

    # --- coleta do mes alvo
    print("\n[2/3] lendo %s/%s no Drive..." % (mes, ano))
    pasta, res, probs = C.coletar(mes, ano)
    if not res:
        print("      nenhum arquivo lido. Nada a fazer.")
        for p in probs:
            print("        - %s" % p)
        return 1
    print("      %d empresa(s) lida(s)" % len(res))

    # --- aplica
    print("\n[3/3] aplicando...")
    mudancas, antes_g, depois_g = aplicar(dados, res, k)
    if not mudancas:
        print("      nenhum valor mudou; dashboard ja estava atualizado")
    for emp, antes, depois, erro in mudancas:
        if erro:
            print("      ! %s: %s" % (emp, erro))
        else:
            print("      %-12s %14s -> %14s" % (emp, "{:,.2f}".format(antes),
                                                "{:,.2f}".format(depois)))
    print("      %-12s %14s -> %14s" % ("GERAL", "{:,.2f}".format(antes_g),
                                        "{:,.2f}".format(depois_g)))

    if probs:
        print("\n      observacoes:")
        for p in probs:
            print("        - %s" % p)

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0
    if not mudancas:
        return 0

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups",
                       "index.html.bak_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(INDEX, bkp)
    open(INDEX, "w", encoding="utf-8").write(gravar(h, ini, fim, dados))
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
