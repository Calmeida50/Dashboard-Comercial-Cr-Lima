#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corte.py — a regra de corte do projeto, num lugar so.

DECISAO DO CRISTIANO (09/08/2026):

    "Anterior a junho, vamos congelar as informacoes. Toda a automatizacao
     seguimos de junho em diante. Os numeros anteriores a junho nao mexemos
     mais, deixamos congelado."

Motivo: ate maio/2026 o acompanhamento era feito na **Planilha 2026**, e os
numeros do dashboard vieram de la, ja validados. So a partir de junho o
Cristiano passou a salvar TODOS os relatorios no Drive — antes disso o Drive
tem apenas 5 das 10 empresas, entao qualquer recalculo produziria numero
menor que o real.

Esta trava e de CODIGO, nao de combinado: nenhum coletor consegue escrever em
mes congelado, mesmo que alguem passe o mes na linha de comando.
"""

ANO_CORTE = 2026
MES_CORTE = 6              # junho
IDX_CORTE = MES_CORTE - 1  # indice 5 nos arrays de 12 posicoes

MESES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
         "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


def congelado(idx_mes, ano=ANO_CORTE):
    """True se o mes (indice 0-11) esta no periodo congelado"""
    if ano < ANO_CORTE:
        return True
    if ano > ANO_CORTE:
        return False
    return idx_mes < IDX_CORTE


def checar(idx_mes, ano=ANO_CORTE):
    """Levanta erro se alguem tentar gravar em mes congelado.
    Usar SEMPRE antes de escrever no index.html."""
    if congelado(idx_mes, ano):
        nome = MESES[idx_mes] if 0 <= idx_mes < 12 else str(idx_mes)
        raise PermissionError(
            "%s/%s esta CONGELADO (corte: %s/%s). "
            "O dado veio da Planilha 2026 e nao deve ser recalculado. "
            "Ver corte.py." % (nome, ano, MESES[IDX_CORTE], ANO_CORTE))


def preservar(lista_antiga, lista_nova, ano=ANO_CORTE):
    """devolve uma lista de 12 posicoes com os meses congelados vindos da
    ANTIGA e os liberados vindos da NOVA. E a forma segura de gravar."""
    out = list(lista_nova)
    for k in range(min(12, len(out))):
        if congelado(k, ano) and k < len(lista_antiga):
            out[k] = lista_antiga[k]
    return out


def meses_liberados(ano=ANO_CORTE):
    """indices que podem ser gravados"""
    return [k for k in range(12) if not congelado(k, ano)]
