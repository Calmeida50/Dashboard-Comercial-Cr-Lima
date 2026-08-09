#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
equivalencias.py — tabela de apelidos e atribuicao de clientes.

Construida a partir da revisao manual do Cristiano (09/08/2026) sobre a
planilha `pendencias_atribuicao_vendedor.xlsx`.

Resolve tres coisas:
  1. APELIDOS  — mesma empresa escrita de forma diferente entre o arquivo de
                 faturamento e o cadastro (ex: 'CIA. ZAFFARI' = 'COMPANHIA
                 ZAFFARI COM E IND')
  2. FUSOES    — clientes que devem ser SOMADOS num so (ex: WMS/WMB entraram
                 no Atacadao; O Vantajao e bandeira da Irmaos Andreazza)
  3. VENDEDOR  — quem atende, quando o cadastro nao sabia

PRIORIDADE DE ATRIBUICAO (da mais forte para a mais fraca):
  1. coluna do proprio arquivo ('Vendedor' na PRUDENCE, 'Representante' na
     BELLIZ / FIAT LUX / KISABOR) — vem do sistema do fabricante
  2. esta tabela
  3. o cadastro Base_Clientes_Vendedores.xlsx
"""

# --- 1. FUSOES: cliente do arquivo -> nome canonico no dashboard -------------
# Somar o faturamento sob o nome canonico. Um cliente pode ter varias grafias.
FUSOES = {
    # WMS/WMB foram compradas pelo Atacadao (regra vale desde jan/2025)
    "WMS SUPERMERCADOS DO BRASIL": "ATACADÃO S/A",
    "WMB SUPERMERCADOS DO BRASIL": "ATACADÃO S/A",
    "WMS SUPERMERCAODS DO BRASIL": "ATACADÃO S/A",      # erro de digitacao na origem
    # O Vantajao e bandeira da rede Irmaos Andreazza
    "O VANTAJAO": "IRMAOS ANDREAZZA LTDA",
    # Fort Atacadista e o mesmo grupo SDB
    "FORT ATACADISTA": "SDB COMERCIO DE ALIMENTOS LTDA",
    # SGM e Dartora sao o mesmo cliente — consolidar em DARTORA
    "SGM IND DE COM": "DARTORA",
    "SGM INDUSTRIA DE COSMETICOS": "DARTORA",
    # Crisan
    "CRISAN": "C&A COMERCIO DE ALIMENTOS LTDA",
}

# --- 2. APELIDOS: grafia do arquivo -> nome ja existente no cadastro ---------
APELIDOS = {
    "CIA. ZAFFARI COMERCIO E INDUSTRIA": "COMPANHIA ZAFFARI COM E IND",
    "COMPANHIA ZAFFARI COMERCIO E INDUSTRIA": "COMPANHIA ZAFFARI COM E IND",
    "SA0 JOAO FARMACIAS": "COMERCIO DE MEDICAMENTOS BRAIR LTDA",
    "SAO JOAO FARMACIAS": "COMERCIO DE MEDICAMENTOS BRAIR LTDA",
    "FARMACIAS SAO JOAO": "COMERCIO DE MEDICAMENTOS BRAIR LTDA",
    "SUPERM. GUANABARA": "SUPERMERCADO GUANABARA S A",
    "OSMAR NICOLINI COMER": "OSMAR NICOLINI SUPERMERCADOS LTDA",
    "LONDRES MACRO ATAC. PROD. ALIMENT.": "LONDRES MACRO ATACADO DE PRODUTOS ALIMENTICIOS LTDA",
    "SUPERMERCADOS LONDRES": "LONDRES MACRO ATACADO DE PRODUTOS ALIMENTICIOS LTDA",
    "IMPORTADORA & EXP.DE CEREAIS": "IMPORTADORA E EXPORTADORA DE CEREAIS S/A",
    "IMPORTADORA E EXPORTADORA DE CEREAIS SA": "IMPORTADORA E EXPORTADORA DE CEREAIS S/A",
    "IMEC RS": "IMPORTADORA E EXPORTADORA DE CEREAIS S/A",
    "IMEC": "IMPORTADORA E EXPORTADORA DE CEREAIS S/A",
    "COOPERATIVA AGRICOLA CAIRU": "COOP AGRICOLA CAIRU LTDA",
    "COOPERATIVA AGRICOLA": "COOP AGRICOLA CAIRU LTDA",
    "ORG FARMACEUTICAS CONFIANCA": "ORGANIZACOES FARMACEUTICAS CONFIANCA EIRELI",
    "FARMACIA CONFIANCA": "ORGANIZACOES FARMACEUTICAS CONFIANCA EIRELI",
    "COOP.TRIT.SEPEENSE": "COOP TRITICOLA SEPEENSE LTDA",
    "GUARAPARI COM DE GENEROS ALIMENT": "GUARAPARI COMERCIO DE GENEROS ALIMENTICIOS LTDA",
    "HOSPITAL BENEFICENTE SAO JOAO BOSCO": "HOSPITAL SÃO JOÃO BOSCO",
    "FARMACIA INHACOR M.V.C COMERCIAL DE MEDI": "FARM INHACOR M.V.C COM DE MEDICAM LTDA",
    "SIND. TRABALHADORES RURAL DE LAJEADO": "SINDICATO DOS TRABALH RURAIS DE LAJEADO",
    "UNIMED COOPERATIVA DE SERVICOS DE SAUDE DOS VALES DO TAQUARI":
        "UNIMED COOP SERV SAUDE VALES TAQUARI E RIO PARDO LTDA",
    "UNIMED SERRA GAUCHARS COOPERATIVA DE ASSISTENCIA A SAUDE": "UNIMED SERRA GAUCHA",
    "UNIMED SERRA GAUCHA/RS C. DE A. A SAUDE": "UNIMED SERRA GAUCHA",
    "FARMACIA ERECHIM": "PAULO ROBERTO FORNARI E CIA LTDA",
    "SUPERMERCADO COTRIPA": "COTRIPAL AGROPECUARIA COOPERATIVA",
    "SUPERMERCADOCOTRISAL": "COTRISAL AGROINDUSTRIAL COOPERATIVA",
    "SUPERMERCADO COTRISAL": "COTRISAL AGROINDUSTRIAL COOPERATIVA",
    "COSMETICOS SANTAMARIENSE": "COPROBEL",
    "CENTRAL GAUCHA DE COSMETICOS": "COPROBEL",
    "COMERCIO DE COSMETICOS CAXIENSE": "COMERCIO DE COSMETICOS CAXIENSE LTDA",
    "CRISSIELE DE CASTRO OLIVEIRA": "IMAGINE STORE MODA E PERFUMARIA LTDA",
    "MADREPEROLA ACESSORIOS E MAQUIAGENS": "RAFAELA FURINI",
    "20.808.832 JULIARA FERREIRA DA SILVA": "JULIARA FERREIRA DA SILVA 01507069014",
    "COSMETICOS ANA LIDIA": "ANA LIDIA",
}


# --- 3. VENDEDOR por (empresa, cliente) -------------------------------------
# O vendedor pode MUDAR conforme a empresa: o mesmo cliente e atendido por
# pessoas diferentes em marcas diferentes. Por isso a chave e o par.
VENDEDOR = {
    ("EVER GREEN", "IMPORTADORA E EXPORTADORA DE CEREAIS S/A"): "CRISTIANO",
    ("KISABOR",    "IMPORTADORA E EXPORTADORA DE CEREAIS S/A"): "MATHEUS",
    ("FIAT LUX",   "IMPORTADORA E EXPORTADORA DE CEREAIS S/A"): "MATHEUS",
    ("EVER GREEN", "SDB COMERCIO DE ALIMENTOS LTDA"): "EDIMAR",
    ("EVER GREEN", "COMERCIO DE MEDICAMENTOS BRAIR LTDA"): "CRISTIANO",
    ("EVER GREEN", "PAULO ROBERTO FORNARI E CIA LTDA"): "MATHEUS",
    ("EVER GREEN", "ORGANIZACOES FARMACEUTICAS CONFIANCA EIRELI"): "MATHEUS",
    ("EVER GREEN", "COTRIPAL AGROPECUARIA COOPERATIVA"): "MATHEUS",
    ("EVER GREEN", "COTRISAL AGROINDUSTRIAL COOPERATIVA"): "MATHEUS",
    ("FIAT LUX",   "COMPANHIA ZAFFARI COM E IND"): "HEIDI",
    ("FIAT LUX",   "LONDRES MACRO ATACADO DE PRODUTOS ALIMENTICIOS LTDA"): "JEFERSON",
    ("FIAT LUX",   "COMERCIAL LARC LTDA"): "HEIDI",
    ("GRANADO",    "LONDRES MACRO ATACADO DE PRODUTOS ALIMENTICIOS LTDA"): "JEFERSON",
    ("GRANADO",    "COPROBEL"): "HEIDI",
    ("GRANADO",    "COMERCIO DE COSMETICOS CAXIENSE LTDA"): "SUELI",
    ("GRANADO",    "SUPERVIZA SUPERMERCADOS LTDA"): "CESAR",
    ("GRANADO",    "IMPERIAL SUPERMERCADOS LTDA"): "CESAR",
    ("GRANADO",    "SUPER MADI COMERCIAL DE ALIMENTOS LTDA"): "HEIDI",
    ("GRANADO",    "KUCHAK COMERCIAL DE ALIMENTOS LTDA"): "HEIDI",
    ("GRANADO",    "COSMETICOS CARAZINHO LTDA"): "SILVIA",
    ("GRANADO",    "JULIANA SCHERER"): "SILVIA",
    ("GRANADO",    "M.B COMERCIO DE COSMETICOS LTDA"): "THIELIN",
    ("GRANADO",    "KI - BELEZA COMERCIO DE COSMETICOS LTDA"): "THIELIN",
    ("CLESS",      "COPROBEL"): "HEIDI",
    ("CLESS",      "COMERCIO DE COSMETICOS CAXIENSE LTDA"): "SUELI",
    ("CLESS",      "COSMETICOS CARAZINHO LTDA"): "SILVIA",
    ("CLESS",      "DINES DISTRIBUIDORA DE COSMETICOS LTDA"): "SUELI",
    ("CLESS",      "JAVIL COMERCIO DE COSMETICOS LTDA"): "SUELI",
    ("PRUDENCE",   "LADYDIU MEDICAMENTOS ESPECIAIS LTDA"): "GRAZI",
    ("PAYOT",      "THE BEAUTY COMERCIO E IMPORTACAO LTDA"): "THIELIN",
    ("PAYOT",      "DHONATAN KOSLOWSKI TEJADA"): "THIELIN",
    ("PAYOT",      "IMAGINE STORE MODA E PERFUMARIA LTDA"): "THIELIN",
    ("PAYOT",      "RAFAELA FURINI"): "MATHEUS",
    ("PAYOT",      "2A FARMACEUTICA LTDA"): "MATHEUS",
    ("PAYOT",      "DONA DA BELEZA LTDA"): "SUELI",
    ("PAYOT",      "CENTRAL BELA LTDA"): "SUELI",
    ("PAYOT",      "MT COM VAREJISTA DE MERCADORIAS LTDA"): "EDIMAR",
    ("PAYOT",      "LUMIER COSMETICOS LTDA"): "AHMANDA",
    ("PAYOT",      "MITHRASS COSMETICOS E SERVICOS LTDA"): "AHMANDA",
    ("BELLIZ",     "UNIMED SERRA GAUCHA"): "SUELI",
    ("BELLIZ",     "DROGARIA GLICOFARMA LTDA"): "SUELI",
    ("BELLIZ",     "HAODAY BRASIL LTDA"): "SUELI",
    ("BELLIZ",     "LL COMERCIO DE MEDICAMENTOS LTDA"): "SILVIA",
    ("BELLIZ",     "ANA LIDIA"): "CESAR",
    ("GRANADO",    "UNIMED SERRA GAUCHA"): "SUELI",
    ("KISABOR",    "C&A COMERCIO DE ALIMENTOS LTDA"): "SUELI",
}

# vendedor do cliente independente da empresa (fusoes com regra unica)
VENDEDOR_GERAL = {
    "ATACADÃO S/A": "EDIMAR",          # WMS/WMB -> Atacadao, desde jan/2025
    "IRMAOS ANDREAZZA LTDA": "ÂNGELA",  # O Vantajao
}

# --- 4. LIXO: rotulos que NAO sao cliente -----------------------------------
# A KISABOR fecha a planilha com estatistica do Excel. 'VAREJO' e agrupamento.
LIXO = {"SUM", "AVERAGE", "TOTAL", "COUNT", "SUBTOTAL", "MEDIA", "VAREJO",
        "SOMA", "MAX", "MIN", "CONTAGEM", "NAN"}

# --- 5. Colunas que ja trazem o vendedor na origem --------------------------
# Tem prioridade sobre tudo: vem do sistema do fabricante.
# PRUDENCE: 'Vendedor' — usada em julho/2026 para separar BRAIR e DIMED entre
# CRISTIANO e GRAZI (cada um atende uma linha de produtos nesses 2 clientes).
COLUNAS_VENDEDOR = ["VENDEDOR", "REPRESENTANTE"]


def canonico(nome):
    """aplica FUSOES e APELIDOS; devolve o nome final do cliente"""
    import re, unicodedata
    s = unicodedata.normalize("NFKD", str(nome or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).upper().strip()
    s = re.sub(r"^\d+\s*[-–]\s*", "", s)
    s = re.sub(r"\s*[-–]\s*\d+\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in LIXO:
        return None
    for chave, destino in FUSOES.items():
        if chave in s:
            return destino
    for chave, destino in APELIDOS.items():
        k = unicodedata.normalize("NFKD", chave)
        k = "".join(c for c in k if not unicodedata.combining(c)).upper()
        if k in s or s in k:
            return destino
    return s


def vendedor_de(empresa, cliente_canonico):
    """devolve o vendedor conhecido, ou None"""
    v = VENDEDOR.get((empresa, cliente_canonico))
    if v:
        return v
    return VENDEDOR_GERAL.get(cliente_canonico)
