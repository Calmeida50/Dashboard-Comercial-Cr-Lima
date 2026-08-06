#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conferir_dartora.py — le os arquivos de sell out da Dartora e compara com o
dashboard. NAO grava nada.

Diferencas em relacao a Sao Joao:
  - nome do arquivo NEM SEMPRE traz o ano -> o ano vem da PASTA (2025/ ou 2026/)
  - dois tipos de relatorio: regular (por produto) e "POR VENDEDOR"
  - o regular ja vem liquido (`Valor líq`), sem coluna bruta
  - traz `Qtd clientes`, que a Sao Joao nao tem
"""
import os, re, json, glob, unicodedata
import pandas as pd

DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA/SELL OUT PRINCIPAIS CLIENTES"
)
EMPRESAS = ["BELLIZ", "CLESS", "EVER GREEN", "GRANADO", "PRUDENCE"]
MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ABREV = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper().replace("_", " ")
    return re.sub(r"\s+", " ", s).strip()


def arquivos():
    """indexa todos os arquivos da Dartora por (empresa, mes, ano, tipo)"""
    idx = {}
    for p in glob.glob(os.path.join(DRIVE, "**", "*.*"), recursive=True):
        if not p.lower().endswith((".xlsx", ".xls", ".txt")):
            continue
        nome = norm(os.path.basename(p))
        if "DARTORA" not in nome or "VENDEDORES DO" in nome:
            continue
        tipo = "vendedor" if "POR VENDEDOR" in nome else "produto"
        emp = next((e for e in EMPRESAS if norm(e) in nome), None)
        mes = next((m for m in MESES if m in nome), None)
        if not emp or not mes:
            continue
        # ano: primeiro tenta a pasta, depois o sufixo do nome
        cam = norm(p)
        ano = None
        for a in ("2025", "2026"):
            if "/" + a + "/" in p or "/%s " % a[-2:] in cam:
                ano = a[-2:]
        if ano is None:
            m = re.search(r"\b(25|26)\b", nome)
            ano = m.group(1) if m else None
        if ano is None:
            continue
        idx.setdefault((emp, mes, ano, tipo), []).append(p)
    return idx


def ler_txt(path):
    """Relatorio de largura fixa, Latin-1, CRLF. Estrutura:
         Mês: 01/2026
         <descricao>   <cod item>   <quantidade>   <valor liq>
    O mes vem DENTRO do arquivo — nunca confiar no nome."""
    txt = open(path, encoding="latin-1", errors="replace").read()
    linhas = txt.splitlines()
    # descricao ... codigo(12345-6) ... quantidade ... valor [... qtd clientes]
    # Alguns meses tem a coluna extra "Qtd clientes" DEPOIS do valor, entao nao
    # ancorar no fim da linha: pegar os numeros que vem apos o codigo.
    re_item = re.compile(r"^\s+(.+?)\s{2,}(\d{4,}-\d)\s+(.*)$")
    re_mes = re.compile(r"M[eê]s:\s*(\d{2})/(\d{4})")
    total = 0.0
    meses = set()
    for l in linhas:
        m = re_mes.search(l)
        if m:
            meses.add((int(m.group(1)), int(m.group(2))))
            continue
        it = re_item.match(l)
        if it:
            nums = re.findall(r"-?[\d.]+,\d{2}|-?[\d.]+,\d{3}", it.group(3))
            if len(nums) >= 2:                    # [0]=quantidade  [1]=valor
                v = nums[1].replace(".", "").replace(",", ".")
                try:
                    total += float(v)
                except ValueError:
                    pass
    return total, meses


def mes_do_arquivo(path):
    """devolve (mes, ano) lido de DENTRO do arquivo, ou None"""
    if path.lower().endswith(".txt"):
        _, meses = ler_txt(path)
        return sorted(meses)[0] if meses else None
    try:
        hdr = _achar_hdr(path)
        if hdr is None:
            return None
        d = pd.read_excel(path, header=hdr)
        col = next((c for c in d.columns if norm(c).startswith("MES")), None)
        if col is None:
            return None
        s = pd.to_datetime(d[col], errors="coerce").dropna()
        if s.empty:
            return None
        return (int(s.iloc[0].month), int(s.iloc[0].year))
    except Exception:
        return None


def _achar_hdr(path):
    cru = pd.read_excel(path, header=None, nrows=15)
    for r in range(len(cru)):
        linha = [norm(x) for x in cru.iloc[r].tolist() if str(x) != "nan"]
        if any("VALOR" in x or "VLR" in x for x in linha) and len(linha) >= 3:
            return r
    return None


def ler_produto(path):
    """soma o valor liquido do relatorio regular (xlsx ou txt)"""
    if path.lower().endswith(".txt"):
        total, _ = ler_txt(path)
        return total, None
    hdr = _achar_hdr(path)
    if hdr is None:
        return None, "cabecalho nao encontrado"
    d = pd.read_excel(path, header=hdr)
    # linha de total: OS DOIS criterios, nao um ou outro —
    #  (a) alguma celula com "TOTAL" (as vezes na coluna Marca)
    #  (b) coluna de descricao vazia (o total nao tem nome de produto)
    eh_total = d.apply(lambda r: any(norm(x) in ("TOTAL", "TOTAL GERAL")
                                     for x in r.tolist()), axis=1)
    desc = next((c for c in d.columns if norm(c).startswith("DESC")), None)
    if desc is not None:
        eh_total = eh_total | d[desc].isna()
    d = d[~eh_total]
    col = next((c for c in d.columns if "VALOR" in norm(c) or "VLR" in norm(c)), None)
    if col is None:
        return None, "sem coluna de valor: %s" % list(d.columns)[:6]
    bruto = "BRUTO" in norm(col)
    v = pd.to_numeric(d[col], errors="coerce").fillna(0)
    return float(v.sum()), ("BRUTO" if bruto else None)


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
    return json.loads(h[i:j + 1])["sellout_dartora"]


def main():
    idx = arquivos()
    da = dashboard()
    # RECHAVEIA pelo mes lido DENTRO do arquivo — o nome ja mentiu (ABRIL 26
    # continha maio). Onde nao der para ler, mantem o do nome.
    novo, trocados = {}, []
    for (emp, mes, ano2, tipo), lista in idx.items():
        p = lista[0]
        real = mes_do_arquivo(p) if tipo == "produto" else None
        if real:
            m_real, a_real = real
            k_mes, k_ano = MESES[m_real - 1], str(a_real)[-2:]
            if (k_mes, k_ano) != (mes, ano2):
                trocados.append("%s: nome diz %s/%s, arquivo diz %s/%s"
                                % (os.path.basename(p)[:46], mes[:3], ano2,
                                   k_mes[:3], k_ano))
            novo.setdefault((emp, k_mes, k_ano, tipo), []).append(p)
        else:
            novo.setdefault((emp, mes, ano2, tipo), []).append(p)
    idx = novo
    if trocados:
        print("\nARQUIVOS COM MES DIFERENTE DO NOME (usando o de dentro):")
        for t in trocados:
            print("   !", t)

    print("=" * 76)
    print("  CONFERENCIA SELL OUT DARTORA — arquivos vs dashboard")
    print("=" * 76)
    ok = div = 0
    faltam_arq, faltam_dash, usam_bruto = [], [], []
    for ano2, chave in (("25", "mensal_2025"), ("26", "mensal_2026")):
        print("\n--- 20%s" % ano2)
        for emp in EMPRESAS:
            bloco = da.get(emp, {}).get(chave, {})
            for k, mes in enumerate(MESES):
                alvo = bloco.get(ABREV[k])
                arqs = idx.get((emp, mes, ano2, "produto"), [])
                if not arqs and alvo is None:
                    continue                      # nao existe nem la nem ca
                if not arqs:
                    faltam_arq.append("%s %s/%s (dash tem %.2f)" % (emp, ABREV[k], ano2, alvo))
                    continue
                val, flag = ler_produto(arqs[0])
                if val is None:
                    print("  %-11s %-4s ERRO %s" % (emp, ABREV[k], flag))
                    continue
                if flag == "BRUTO":
                    usam_bruto.append("%s %s/%s" % (emp, ABREV[k], ano2))
                if alvo is None:
                    faltam_dash.append("%s %s/%s (arquivo tem %.2f)" % (emp, ABREV[k], ano2, val))
                    continue
                dif = val - alvo
                if abs(dif) < 0.05:
                    ok += 1
                else:
                    div += 1
                    print("  %-11s %-4s arquivo %12s  dash %12s  dif %11s"
                          % (emp, ABREV[k], "{:,.2f}".format(val),
                             "{:,.2f}".format(alvo), "{:,.2f}".format(dif)))
    print("\n" + "=" * 76)
    print("conferem: %d   divergem: %d" % (ok, div))
    if usam_bruto:
        print("\nARQUIVOS COM COLUNA **BRUTA** (%d) — contamina a serie:" % len(usam_bruto))
        print("   " + ", ".join(usam_bruto[:18]))
    if faltam_arq:
        print("\nno dashboard mas SEM arquivo (%d):" % len(faltam_arq))
        for x in faltam_arq[:12]: print("   -", x)
    if faltam_dash:
        print("\ncom arquivo mas AUSENTE do dashboard (%d):" % len(faltam_dash))
        for x in faltam_dash[:12]: print("   -", x)


if __name__ == "__main__":
    main()
