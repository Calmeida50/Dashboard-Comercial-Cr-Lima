#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sincronizar.py — varre as pastas do Drive, detecta arquivos novos ou alterados
e roda apenas os coletores afetados.

Por que nao rodar tudo sempre: a leitura completa passa de 300 arquivos e leva
varios minutos. Comparando uma "impressao digital" (nome + tamanho + data) de
cada pasta, so processamos o que realmente mudou.

Categorias e seus coletores:
    faturamento  -> atualizar_faturamento.py   (mes anterior + mes corrente)
    sellout_sj   -> atualizar_sellout.py
    sellout_dt   -> atualizar_dartora.py
    sellout_nt   -> atualizar_nilo.py
    sellout_imec -> conferir_imec.py
    sellout_aqua -> atualizar_unidasul_aquafast.py
    estoque      -> atualizar_estoque.py

Estado guardado em _backups/estado_arquivos.json
"""
import os, re, sys, json, glob, subprocess, datetime, hashlib
import corte   # regra de corte: nada anterior a junho/2026 e reprocessado

PROJ = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
ESTADO = os.path.join(PROJ, "_backups", "estado_arquivos.json")

CATEGORIAS = {
    "faturamento":  (["FATURAMENTO DAS EMPRESAS*"], ["atualizar_faturamento.py"]),
    "sellout_sj":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_sellout.py"]),
    "sellout_dt":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_dartora.py"]),
    "sellout_nt":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_nilo.py"]),
    "sellout_imec": (["SELL OUT PRINCIPAIS CLIENTES"], ["conferir_imec.py"]),
    "sellout_aqua": (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_unidasul_aquafast.py"]),
    "sellout_pv":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_panvel.py",
                                                        "atualizar_panvel_lojas.py"]),
    "estoque":      (["ESTOQUE DOS PRINCIPAIS CLIENTES"], ["atualizar_estoque.py"]),
    "estoque_pv":   (["ESTOQUE DOS PRINCIPAIS CLIENTES"], ["atualizar_estoque_panvel.py"]),
}
# filtro por nome de arquivo, para cada categoria so olhar o que lhe interessa
FILTRO = {
    "sellout_sj":   "SAO JOAO",
    "sellout_dt":   "DARTORA",
    "sellout_nt":   "NILO",
    "sellout_imec": "IMEC",
    "sellout_aqua": "AQUAFAST",
    "sellout_pv":   "PANVEL",
    "estoque":      "SAO JOAO",
    "estoque_pv":   "PANVEL",
}


def _mes_congelado_no_caminho(p):
    """True se o arquivo esta numa pasta de mes anterior ao corte.
    Mexer num arquivo de marco nao pode disparar reprocessamento — aquele
    periodo veio da Planilha 2026 e esta congelado."""
    alto = p.upper()
    if "/2025/" in alto:
        return True
    for k in range(corte.IDX_CORTE):
        nome = corte.MESES[k]
        variantes = (nome, nome.replace("MARCO", "MARÇO"))
        for v in variantes:
            if "/%s/" % v in alto or "/%s " % v in alto:
                return True
    return False


def impressao(pastas, filtro=None):
    """assinatura da pasta: nome, tamanho e data de cada arquivo relevante"""
    itens = []
    for pasta in pastas:
        for base in glob.glob(os.path.join(DRIVE, pasta)):
            for p in glob.glob(os.path.join(base, "**", "*.*"), recursive=True):
                nome = os.path.basename(p)
                if nome.startswith(".") or nome.startswith("~$"):
                    continue
                if not p.lower().endswith((".xlsx", ".xls", ".xlsm", ".txt")):
                    continue
                if filtro and filtro not in nome.upper():
                    continue
                if _mes_congelado_no_caminho(p):
                    continue
                try:
                    st = os.stat(p)
                    itens.append("%s|%d|%d" % (nome, st.st_size, int(st.st_mtime)))
                except OSError:
                    pass
    itens.sort()
    return hashlib.sha256("\n".join(itens).encode()).hexdigest(), len(itens)


def carregar_estado():
    try:
        return json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        return {}


def salvar_estado(e):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump(e, open(ESTADO, "w", encoding="utf-8"), indent=2)


def rodar(script):
    """executa um coletor; devolve (codigo, saida)"""
    r = subprocess.run(["/usr/bin/python3", os.path.join(PROJ, script)],
                       cwd=PROJ, capture_output=True, text=True, timeout=1800)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    forcar = "--forcar" in sys.argv
    so_ver = "--verificar" in sys.argv
    estado = carregar_estado()
    novo_estado = dict(estado)
    mudaram, relatorio = [], []

    print("=" * 70)
    print("  SINCRONIZAR — %s" % datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("=" * 70)

    if not os.path.isdir(DRIVE):
        print("ERRO: pasta do Drive inacessivel. O Google Drive esta rodando?")
        return 1

    for cat, (pastas, scripts) in CATEGORIAS.items():
        h, n = impressao(pastas, FILTRO.get(cat))
        antes = estado.get(cat, {}).get("hash")
        if h == antes and not forcar:
            print("  %-13s %3d arquivos · sem mudanca" % (cat, n))
            continue
        print("  %-13s %3d arquivos · MUDOU" % (cat, n))
        mudaram.append((cat, scripts, h, n))

    if not mudaram:
        print("\nNada mudou no Drive. Nada a fazer.")
        return 0
    if so_ver:
        print("\n--verificar: nao executei nada.")
        return 0

    for cat, scripts, h, n in mudaram:
        for s in scripts:
            print("\n>>> %s (%s)" % (s, cat))
            cod, saida = rodar(s)
            ultimas = [l for l in saida.strip().splitlines() if l.strip()][-6:]
            for l in ultimas:
                print("    " + l[:120])
            if cod == 2:
                relatorio.append("%s ABORTOU (divergencia no historico)" % cat)
                print("    !! abortado pela trava — estado NAO atualizado")
                break
            # codigo 1 = "nada a processar" (ex: mes corrente ainda sem arquivo).
            # Nao e falha: o estado pode avancar normalmente.
            if cod not in (0, 1):
                relatorio.append("%s falhou (codigo %d)" % (cat, cod))
                break
        else:
            novo_estado[cat] = {"hash": h, "arquivos": n,
                                "em": datetime.datetime.now().isoformat(timespec="seconds")}
            relatorio.append("%s atualizado (%d arquivos)" % (cat, n))

    salvar_estado(novo_estado)
    print("\n" + "\n".join("  - " + r for r in relatorio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
