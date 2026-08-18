# -*- coding: utf-8 -*-
"""
drive_io.py — leitura de Excel do Google Drive com NOVA TENTATIVA.

O Drive recusa a leitura enquanto esta sincronizando o arquivo:
    OSError: [Errno 11] Resource deadlock avoided

Isso ja custou caro no projeto:
  10/08  a rotina marcou a categoria como "atualizada" mesmo tendo falhado, e
         o dado ficou faltando em silencio ate alguem perceber.
  15/08  estoque da Panvel nao entrou; so foi notado na segunda-feira.
  17/08  de novo o estoque da Panvel — o Cristiano teve que perguntar.

O `coletar_faturamento.py` ja resolvia isso sozinho desde o inicio; este
modulo leva a mesma protecao para todos os coletores.

Uso:
    from drive_io import ler_excel
    d = ler_excel(caminho, sheet_name="Planilha1")
"""
import time
import pandas as pd

TENTATIVAS = 5
PAUSA_BASE = 1.5          # segundos; cresce a cada tentativa


def _e_bloqueio(e):
    t = str(e).lower()
    return ("deadlock" in t or "errno 11" in t
            or "resource temporarily unavailable" in t
            or "errno 35" in t)


def ler_excel(path, **kw):
    """pd.read_excel que espera o Drive terminar de sincronizar.

    Erros que NAO sao de sincronismo (arquivo corrompido, aba inexistente)
    sobem na hora — nova tentativa nao ajudaria e so atrasaria o log."""
    ultimo = None
    for i in range(TENTATIVAS):
        try:
            return pd.read_excel(path, **kw)
        except OSError as e:
            ultimo = e
            if not _e_bloqueio(e):
                raise
            time.sleep(PAUSA_BASE * (i + 1))
    raise ultimo


def abrir_excel(path):
    """pd.ExcelFile com a mesma protecao"""
    ultimo = None
    for i in range(TENTATIVAS):
        try:
            return pd.ExcelFile(path)
        except OSError as e:
            ultimo = e
            if not _e_bloqueio(e):
                raise
            time.sleep(PAUSA_BASE * (i + 1))
    raise ultimo
