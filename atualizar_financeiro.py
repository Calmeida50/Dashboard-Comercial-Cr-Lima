# -*- coding: utf-8 -*-
"""
atualizar_financeiro.py — alimenta as telas RECEITA LIQUIDA e FINANCEIRO a
partir de `FINANCEIRO/CONTROLE DE CUSTO E CONTROLE DE RECEITAS 26.xlsx` no Drive.

Ate 12/08/2026 esses dois blocos eram carregados A MAO e estavam parados em
junho. Agora entram no ciclo automatico das 18h, como o resto.

BLOCOS QUE ESCREVE (dentro de DADOS_EMBEDDED):
    receitas_empresa_mensal  {"Janeiro": {"GRANADO": 143455.3, ...}, ...}
    financeiro               [{mes, receita, despesa, pct_despesa, liquido}, ...]
    receita_liquida          [{mes, jur25, jur26, jur_delta, rec25, rec26,
                               rec_delta, liq25, liq26, liq_delta, ativo26}, ...]

PRESERVA: as colunas de 2025 (jur25/rec25/liq25). Elas nao estao nesta planilha,
que e so de 2026 — recalcular zeraria o comparativo.

LAYOUT DA PLANILHA (lido do arquivo real, 12/08/2026):
  aba 'RECEITAS 2026'
      linha de cabecalho com as empresas; abaixo, uma linha por mes e uma
      coluna TOTAL. Mais abaixo um bloco RESUMO com o total de cada mes.
  aba 'CONTROLE DE CUSTOS 2026'
      blocos de 3 colunas por mes (rotulo | VALOR | %), seis por faixa, em
      duas faixas (jan-jun e jul-dez). O que interessa e a linha TOTAL.

ATENCAO — as duas fontes de receita do mes podem divergir: a soma das empresas
e o bloco RESUMO. Em junho/2026 a diferenca era de R$ 1.223,32. Vale a SOMA DAS
EMPRESAS, que e a que reconcilia com a abertura por empresa mostrada na tela.
A divergencia e sempre avisada.

TRAVA: meses anteriores ao corte (jan-mai) sao reconferidos contra o que ja
esta publicado. Se divergir mais de R$ 0,01, ABORTA sem gravar.

Uso:
    python3 atualizar_financeiro.py --simular
    python3 atualizar_financeiro.py
"""
import os, sys, json, glob, shutil, datetime
import pandas as pd

PROJ = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
PASTA = os.path.join(DRIVE, "FINANCEIRO")

MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
CAP = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MAI = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
       "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
# meses congelados: vieram da Planilha 2026 e ja foram validados
IDX_CORTE = 5   # jan..mai (indices 0-4) sao conferidos, nao alterados


def norm(s):
    """maiuscula, sem acento, sem espaco sobrando"""
    import unicodedata
    s = str(s or "").strip().upper()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def num(v):
    try:
        f = float(v)
        return 0.0 if pd.isna(f) else round(f, 2)
    except (TypeError, ValueError):
        return 0.0


def achar_planilha():
    """a planilha do financeiro; se houver mais de uma, a mais recente"""
    if not os.path.isdir(PASTA):
        return None
    cand = [p for p in glob.glob(os.path.join(PASTA, "*.xls*"))
            if not os.path.basename(p).startswith("~$")
            and ("CUSTO" in norm(p) or "RECEITA" in norm(p))]
    if not cand:
        return None
    return sorted(cand, key=os.path.getmtime, reverse=True)[0]


def ler_receitas(path):
    """devolve (por_empresa, total_por_mes, resumo_por_mes), indexados 0..11"""
    d = pd.read_excel(path, sheet_name="RECEITAS 2026", header=None)
    # cabecalho: a linha que traz os nomes das empresas
    lin_cab = None
    for r in range(len(d)):
        vals = [norm(x) for x in d.iloc[r].tolist()]
        if "GRANADO" in vals:
            lin_cab = r
            break
    if lin_cab is None:
        return None, None, None
    cols_emp = {}
    for c in range(1, d.shape[1]):
        nome = str(d.iat[lin_cab, c]).strip()
        if nome and nome.lower() != "nan" and norm(nome) != "TOTAL":
            cols_emp[c] = nome
    col_total = next((c for c in range(1, d.shape[1])
                      if norm(d.iat[lin_cab, c]) == "TOTAL"), None)

    por_emp = {}
    total = {}
    # linhas de mes logo abaixo do cabecalho, ate aparecer TOTAL/PARTICIPACAO
    for r in range(lin_cab + 1, len(d)):
        rot = norm(d.iat[r, 0])
        if rot in ("TOTAL", "PARTICIPACAO"):
            break
        if rot not in MESES:
            continue
        i = MESES.index(rot)
        linha = {}
        for c, nome in cols_emp.items():
            linha[nome] = num(d.iat[r, c])
        por_emp[i] = linha
        total[i] = round(sum(linha.values()), 2)

    # bloco RESUMO, mais abaixo: uma linha por mes com o total
    resumo = {}
    depois = False
    for r in range(len(d)):
        if "RESUMO" in norm(d.iat[r, 0]):
            depois = True
            continue
        if not depois:
            continue
        rot = norm(d.iat[r, 0])
        if rot in MESES:
            resumo[MESES.index(rot)] = num(d.iat[r, 1])
    return por_emp, total, resumo


def ler_custos(path):
    """TOTAL de custo por mes. Os meses ficam em blocos de 3 colunas, em duas
    faixas; procuramos a celula com o nome do mes e, abaixo dela, a linha TOTAL
    na mesma coluna — o valor esta na coluna seguinte."""
    d = pd.read_excel(path, sheet_name="CONTROLE DE CUSTOS 2026", header=None)
    out = {}
    for r in range(len(d)):
        for c in range(d.shape[1]):
            if norm(d.iat[r, c]) not in MESES:
                continue
            i = MESES.index(norm(d.iat[r, c]))
            # a linha TOTAL do bloco, procurando para baixo
            for r2 in range(r + 1, min(r + 40, len(d))):
                if norm(d.iat[r2, c]) == "TOTAL":
                    if c + 1 < d.shape[1]:
                        out[i] = num(d.iat[r2, c + 1])
                    break
                # outro mes na mesma coluna: bloco acabou
                if r2 > r and norm(d.iat[r2, c]) in MESES:
                    break
    return out


def carregar_index():
    src = open(os.path.join(PROJ, "index.html"), encoding="utf-8").read()
    marca = "const DADOS_EMBEDDED ="
    i = src.index(marca)
    j = src.index("{", i)
    obj, fim = json.JSONDecoder().raw_decode(src[j:])
    return src, j, j + fim, obj


def pctd(a, b):
    """variacao percentual de b para a, arredondada como no bloco atual"""
    return round((a / b - 1) * 100, 2) if b else 0.0


def main():
    simular = "--simular" in sys.argv
    path = achar_planilha()
    if not path:
        print("planilha do financeiro nao encontrada em %s" % PASTA)
        return 1

    print("=" * 74)
    print("  FINANCEIRO / RECEITA LIQUIDA%s" % ("  [SIMULACAO]" if simular else ""))
    print("=" * 74)
    print("arquivo: %s" % os.path.basename(path))
    print("gravado: %s\n"
          % datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat())

    por_emp, tot_emp, resumo = ler_receitas(path)
    if por_emp is None:
        print("ABORTOU: nao achei o cabecalho das empresas na aba RECEITAS 2026")
        return 1
    custos = ler_custos(path)

    src, ini, fim, D = carregar_index()
    rl_antigo = {r["mes"]: r for r in D.get("receita_liquida", [])}

    # divergencia entre as duas fontes de receita
    for i in sorted(tot_emp):
        r = resumo.get(i)
        if r is not None and abs(r - tot_emp[i]) > 0.01 and (r or tot_emp[i]):
            print("  ! %s: soma das empresas %.2f x RESUMO %.2f (dif %.2f)"
                  % (CAP[i], tot_emp[i], r, tot_emp[i] - r))
    print("")

    financeiro, receita_liq, receitas_emp = [], [], {}
    divergencias = []
    for i in range(12):
        rec = tot_emp.get(i, 0.0)
        desp = custos.get(i, 0.0)
        liq = round(rec - desp, 2)
        ativo = bool(rec or desp)

        # TRAVA: mes congelado nao pode mudar
        ant = rl_antigo.get(CAP[i])
        if i < IDX_CORTE and ant:
            for campo, novo_v, velho_v in (("receita", rec, ant["rec26"]),
                                           ("custo", desp, ant["jur26"])):
                if abs(novo_v - velho_v) > 0.01:
                    divergencias.append("%s %s: publicado %.2f, planilha %.2f"
                                        % (CAP[i], campo, velho_v, novo_v))

        financeiro.append({"mes": MAI[i], "receita": rec, "despesa": desp,
                           "pct_despesa": round(desp / rec * 100, 2) if rec else 0.0,
                           "liquido": liq})
        # colunas de 2025 vem do bloco atual — nao estao nesta planilha
        j25 = (ant or {}).get("jur25", 0.0)
        r25 = (ant or {}).get("rec25", 0.0)
        l25 = (ant or {}).get("liq25", 0.0)
        receita_liq.append({
            "mes": CAP[i], "jur25": j25, "jur26": desp, "jur_delta": pctd(desp, j25),
            "rec25": r25, "rec26": rec, "rec_delta": pctd(rec, r25),
            "liq25": l25, "liq26": liq, "liq_delta": pctd(liq, l25),
            "ativo26": ativo})
        if ativo and por_emp.get(i):
            receitas_emp[CAP[i]] = por_emp[i]

        if ativo:
            print("  %-10s receita %12s | custo %12s | liquido %12s | %5.1f%%"
                  % (CAP[i], "{:,.2f}".format(rec), "{:,.2f}".format(desp),
                     "{:,.2f}".format(liq), (desp / rec * 100) if rec else 0))

    if divergencias:
        print("\nABORTOU — mes congelado divergiu do publicado:")
        for x in divergencias:
            print("  ! %s" % x)
        print("nada foi gravado.")
        return 2

    if simular:
        print("\nSIMULACAO — nada foi gravado.")
        return 0

    D["financeiro"] = financeiro
    D["receita_liquida"] = receita_liq
    D["receitas_empresa_mensal"] = receitas_emp

    os.makedirs(os.path.join(PROJ, "_backups"), exist_ok=True)
    bkp = os.path.join(PROJ, "_backups", "index.html.bak_financeiro_%s"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(os.path.join(PROJ, "index.html"), bkp)
    novo = src[:ini] + json.dumps(D, ensure_ascii=False, separators=(",", ":")) \
           + src[fim:]
    open(os.path.join(PROJ, "index.html"), "w", encoding="utf-8").write(novo)
    print("\ngravado. backup em _backups/%s" % os.path.basename(bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
