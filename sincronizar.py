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
    financeiro   -> atualizar_financeiro.py  (Receita Liquida + Financeiro)

Estado guardado em _backups/estado_arquivos.json
"""
import time
import os, re, sys, json, glob, subprocess, datetime, hashlib
import corte   # regra de corte: nada anterior a junho/2026 e reprocessado

PROJ = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/"
    "Meu Drive/PROJETO COMERCIAL IA"
)
ESTADO = os.path.join(PROJ, "_backups", "estado_arquivos.json")

CATEGORIAS = {
    # O faturamento dispara TRES scripts em sequencia, nesta ordem:
    #   1. atualizar_faturamento.py  -> bloco `empresas` (total por empresa)
    #   2. atualizar_vendedores.py   -> clientes_detalhado, acomp_vendas,
    #                                   vendedores (as telas por vendedor e o
    #                                   ranking de clientes leem daqui)
    #   3. atualizar_comissoes.py    -> comissoes_* (depende do passo 2)
    # A ordem importa: a comissao e calculada sobre o que o passo 2 atribuiu.
    "faturamento":  (["FATURAMENTO DAS EMPRESAS*"], ["atualizar_faturamento.py",
                                                     "atualizar_vendedores.py",
                                                     "atualizar_comissoes.py"]),
    "sellout_sj":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_sellout.py"]),
    "sellout_dt":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_dartora.py"]),
    "sellout_nt":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_nilo.py"]),
    "sellout_imec": (["SELL OUT PRINCIPAIS CLIENTES"], ["conferir_imec.py"]),
    "sellout_aqua": (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_unidasul_aquafast.py"]),
    # Renner: unico cliente com relatorio SEMANAL, em pasta propria
    "sellout_renner": (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_renner.py"]),
    "sellout_pv":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_panvel.py",
                                                        "atualizar_panvel_lojas.py"]),
    "estoque":      (["ESTOQUE DOS PRINCIPAIS CLIENTES"], ["atualizar_estoque.py"]),
    "estoque_pv":   (["ESTOQUE DOS PRINCIPAIS CLIENTES"], ["atualizar_estoque_panvel.py"]),
    # Lady Diu: planilha mestre unica (2025 e 2026), so quantidade. O
    # relatorio mensal do cliente pode ficar guardado na pasta do mes como
    # comprovante — o coletor le apenas a planilha mestre.
    "sellout_ld":   (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_sellout_ladydiu.py"]),
    # Parametros da Panvel (cluster de lojas liberadas + familia/categoria).
    # Mudam ~2x por ano; ficam em PARAMETROS PANVEL/, fora das pastas de mes.
    "params_pv":    (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_parametros_panvel.py"]),
    # Categoria por item da Sao Joao. O sell out dela nao traz categoria; a
    # planilha tem so os ATIVOS, entao inativo fica sem categoria (esperado).
    "params_sj":    (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_parametros_sao_joao.py"]),
    # Mix minimo Granado: dinamica exportada pelo Cristiano + os dois mixes
    # minimos + o de-para de clientes. Sempre na MESMA planilha, entao basta a
    # data de modificacao mudar para reprocessar.
    "mix_minimo":   (["RELATORIO GRANADO"], ["atualizar_mix_minimo.py"]),
    # Belliz: ranking por canal (regional) + faturamento por produto e cliente
    "mix_belliz":   (["RELATORIOS BELLIZ"], ["atualizar_mix_belliz.py"]),
    # Sell in: usa as MESMAS pastas da Granado e da Belliz
    "sellin":       (["RELATORIO GRANADO", "RELATORIOS BELLIZ"],
                     ["atualizar_sellin.py"]),
    # Fort Atacadista (Ever Green): dois arquivos, um por ano, na pasta propria
    "sellout_fort": (["SELL OUT PRINCIPAIS CLIENTES"], ["atualizar_fort.py"]),
    # Financeiro: uma planilha so, preenchida diariamente pelo Cristiano, que
    # alimenta as telas Receita Liquida e Financeiro. Ate 12/08/2026 esses dois
    # blocos eram carregados a mao e estavam parados em junho.
    "financeiro":   (["FINANCEIRO"], ["atualizar_financeiro.py"]),
}
# filtro por nome de arquivo, para cada categoria so olhar o que lhe interessa
FILTRO = {
    "sellout_sj":   "SAO JOAO",
    "sellout_dt":   "DARTORA",
    "sellout_nt":   "NILO",
    "sellout_renner": "SEMANA",
    "sellout_imec": "IMEC",
    "sellout_aqua": "AQUAFAST",
    "sellout_pv":   "PANVEL",
    "sellout_ld":   "LADY",
    "params_pv":    "CLUSTER|MIX PANVEL",
    "params_sj":    "SAO JOAO COM CATEGORIA",
    "sellout_fort": "FORT ATACADISTA",
    "mix_belliz":   "BELLIZ",
    "sellin":       "SELL IN",
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
                # o filtro aceita alternativas separadas por "|": basta UMA
                # casar. Usado pelos parametros da Panvel, que sao dois
                # arquivos de nomes diferentes (CLUSTER... e MIX PANVEL...).
                if filtro and not any(f in nome.upper() for f in filtro.split("|")):
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

    pendentes = []      # categorias adiadas por Drive ocupado

    for cat, scripts, h, n in mudaram:
        for s in scripts:
            print("\n>>> %s (%s)" % (s, cat))
            cod, saida = rodar(s)
            ultimas = [l for l in saida.strip().splitlines() if l.strip()][-6:]
            for l in ultimas:
                print("    " + l[:120])
            # O Drive as vezes recusa a leitura enquanto sincroniza:
            #   OSError: [Errno 11] Resource deadlock avoided
            # Em 10/08 isso aconteceu e a rotina marcou como "atualizado",
            # gravando a impressao digital — entao ela NUNCA tentaria de novo
            # e o dado ficava faltando em silencio. Agora isso e falha.
            falha_leitura = any(t in saida for t in (
                "Resource deadlock avoided", "Errno 11",
                "cannot be determined", "No such file or directory"))
            if falha_leitura:
                # SEGUNDA CHANCE na mesma rodada. Cada coletor ja tenta de
                # novo internamente (drive_io), mas quando o Drive esta
                # sincronizando uma pasta inteira — a da Panvel tem 11
                # arquivos — a janela e maior que a espera do coletor.
                # Sem isso o dado ficava velho ate o dia seguinte, em
                # silencio: aconteceu em 10, 15 e 17/08/2026.
                print("    !! Drive recusou a leitura; aguardando 90s para tentar de novo")
                time.sleep(90)
                cod, saida = rodar(s)
                for l in [l for l in saida.strip().splitlines() if l.strip()][-6:]:
                    print("    " + l[:120])
                falha_leitura = any(t in saida for t in (
                    "Resource deadlock avoided", "Errno 11",
                    "cannot be determined", "No such file or directory"))
                if falha_leitura:
                    # TERCEIRA CHANCE, no FIM da rodada. O padrao observado em
                    # 17, 18 e 19/08/2026: falha as 18h e funciona de manha —
                    # ou seja, o Drive esta ocupado justamente na hora em que a
                    # rotina roda, e a janela passa de 2 minutos. Em vez de
                    # esperar parado, a categoria vai para o fim da fila: as
                    # outras rodam (leva alguns minutos) e ela e tentada de
                    # novo depois, com o Drive ja mais calmo.
                    pendentes.append((cat, s, h, n))
                    relatorio.append("%s adiado — Drive ocupado, sera tentado "
                                     "no fim da rodada" % cat)
                    print("    !! adiado para o fim da rodada")
                    break
                print("    -> deu certo na segunda tentativa")
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

    # ── categorias adiadas: nova tentativa agora que o resto ja rodou ──────
    if pendentes:
        print("\n" + "=" * 70)
        print("  RETOMANDO %d categoria(s) adiada(s) por Drive ocupado" % len(pendentes))
        print("=" * 70)
        time.sleep(60)
        for cat, s_, h, n in pendentes:
            print("\n>>> %s (%s) — tentativa final" % (s_, cat))
            cod, saida = rodar(s_)
            for l in [l for l in saida.strip().splitlines() if l.strip()][-6:]:
                print("    " + l[:120])
            falhou = any(t in saida for t in (
                "Resource deadlock avoided", "Errno 11",
                "cannot be determined", "No such file or directory"))
            # a mensagem no relatorio troca a de "adiado"
            relatorio[:] = [r for r in relatorio if not r.startswith(cat + " adiado")]
            if falhou or cod not in (0, 1):
                relatorio.append("%s FALHOU ao ler o Drive — sera tentado amanha" % cat)
                print("    !! falhou tambem na tentativa final")
            else:
                novo_estado[cat] = {"hash": h, "arquivos": n,
                                    "em": datetime.datetime.now().isoformat(timespec="seconds")}
                relatorio.append("%s atualizado na tentativa final (%d arquivos)" % (cat, n))
                print("    -> deu certo na tentativa final")

    salvar_estado(novo_estado)
    print("\n" + "\n".join("  - " + r for r in relatorio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
