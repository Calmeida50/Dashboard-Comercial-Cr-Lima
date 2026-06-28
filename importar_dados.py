#!/usr/bin/env python3
"""
Script de importação de dados para o Dashboard Comercial São João
=================================================================
Uso:
  python importar_dados.py --planilha "PLANILHA COMERCIAL 2026.xlsx"
  python importar_dados.py --relatorio "GRANADO MAIO 26.xlsx"
  python importar_dados.py --pasta "RELATORIOS/"
  python importar_dados.py --planilha "planilha.xlsx" --push  (envia para GitHub)
"""

import argparse
import json
import os
import re
import sys
import subprocess
from pathlib import Path

try:
    import pandas as pd
    import openpyxl
except ImportError:
    print("Instalando dependências...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "--quiet"])
    import pandas as pd

# ============================================================
#  CONFIGURAÇÕES
# ============================================================
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "data.json"

MESES = ['JANEIRO','FEVEREIRO','MARÇO','ABRIL','MAIO','JUNHO',
         'JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']

EMPRESA_KEYWORDS = {
    'GRANADO':    ['granado'],
    'PRUDENCE':   ['prudence'],
    'BELLIZ':     ['belliz'],
    'CLESS':      ['cless'],
    'KISABOR':    ['kisabor'],
    'EVER GREEN': ['ever green', 'evergreen', 'ever_green'],
    'FIAT LUX':   ['fiat lux', 'fiatlux', 'fiat_lux'],
    'AQUAFAST':   ['aquafast'],
    'PAYOT':      ['payot'],
    'DEPIMIEL':   ['depimiel'],
    'BOTÂNICA':   ['botanica', 'botânica'],
}

MES_KEYWORDS = {
    'JANEIRO': ['janeiro', 'jan'],
    'FEVEREIRO': ['fevereiro', 'fev'],
    'MARÇO': ['março', 'marco', 'mar'],
    'ABRIL': ['abril', 'abr'],
    'MAIO': ['maio', 'mai'],
    'JUNHO': ['junho', 'jun'],
    'JULHO': ['julho', 'jul'],
    'AGOSTO': ['agosto', 'ago'],
    'SETEMBRO': ['setembro', 'set'],
    'OUTUBRO': ['outubro', 'out'],
    'NOVEMBRO': ['novembro', 'nov'],
    'DEZEMBRO': ['dezembro', 'dez'],
}

# ============================================================
#  UTILITÁRIOS
# ============================================================
def normalizar(texto):
    """Remove acentos e converte para minúsculas."""
    import unicodedata
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def detectar_empresa(nome_arquivo):
    nome = normalizar(nome_arquivo)
    for empresa, palavras in EMPRESA_KEYWORDS.items():
        if any(normalizar(p) in nome for p in palavras):
            return empresa
    return None

def detectar_mes(nome_arquivo):
    nome = normalizar(nome_arquivo)
    for mes, palavras in MES_KEYWORDS.items():
        if any(normalizar(p) in nome for p in palavras):
            return mes
    return None

def carregar_dados():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'meses': ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                  'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'],
        'empresas': {},
        'vendedores': {},
        'financeiro': [],
        'comissoes_empresa': {},
        'comissoes_vendedor': {},
        'atualizado_em': ''
    }

def salvar_dados(dados):
    DATA_DIR.mkdir(exist_ok=True)
    from datetime import date
    dados['atualizado_em'] = date.today().isoformat()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"✅ Dados salvos em {DATA_FILE}")

# ============================================================
#  PROCESSAR PLANILHA GERENCIAL PRINCIPAL
# ============================================================
def processar_planilha(caminho):
    """Extrai todos os dados da Planilha Comercial 2026.xlsx"""
    print(f"\n📊 Processando planilha principal: {caminho}")
    dados = carregar_dados()

    xl = pd.ExcelFile(caminho)
    print(f"   Abas encontradas: {xl.sheet_names}")

    # --- YTD POR EMPRESA ---
    if 'YTD POR EMPRESA' in xl.sheet_names:
        print("   → Extraindo YTD por Empresa...")
        df = pd.read_excel(caminho, sheet_name='YTD POR EMPRESA', header=None)

        blocos = {
            'GERAL':      3,  'GRANADO':    10, 'PAYOT':      16,
            'PRUDENCE':   22, 'BELLIZ':     28, 'CLESS':      34,
            'KISABOR':    40, 'DEPIMIEL':   46, 'BOTÂNICA':   52,
            'FIAT LUX':   59, 'EVER GREEN': 65, 'AQUAFAST':   71,
        }

        for empresa, linha_header in blocos.items():
            if linha_header >= len(df):
                continue
            resultado = {'hist': [0]*12, 'obj': [0]*12, 'real': [0]*12}
            for offset in range(1, 6):
                if linha_header + offset >= len(df):
                    break
                row = df.iloc[linha_header + offset].tolist()
                label = str(row[0]).strip().upper() if pd.notna(row[0]) else ''
                vals = []
                for col_i in range(1, 13):
                    v = row[col_i] if col_i < len(row) and pd.notna(row[col_i]) and isinstance(row[col_i], (int, float)) else 0
                    vals.append(round(float(v), 2))
                if 'HIST' in label and 'GAP' not in label and '%' not in label:
                    resultado['hist'] = vals
                elif 'OBJ' in label and 'GAP' not in label and '%' not in label:
                    resultado['obj'] = vals
                elif 'REALIZADO' in label and 'GAP' not in label and '%' not in label:
                    resultado['real'] = vals
            dados['empresas'][empresa] = resultado
            total_real = sum(v for v in resultado['real'] if v > 0)
            if total_real > 0:
                print(f"      {empresa}: R$ {total_real:,.0f}")

    # --- YTD POR VENDEDOR ---
    if 'YTD POR VENDEDOR' in xl.sheet_names:
        print("   → Extraindo YTD por Vendedor...")
        df = pd.read_excel(caminho, sheet_name='YTD POR VENDEDOR', header=None)
        nomes = ['CRISTIANO','GRAZI','JEFERSON','MATHEUS','HEIDI','EDIMAR',
                 'SUELI','ÂNGELA','CESAR','SILVIA','B2B']
        vendedor_atual = None
        for i in range(len(df)):
            row = df.iloc[i].tolist()
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ''
            col1 = str(row[1]).strip() if pd.notna(row[1]) and len(row) > 1 else ''
            if col0 in nomes:
                vendedor_atual = col0
                if vendedor_atual not in dados['vendedores']:
                    dados['vendedores'][vendedor_atual] = {}
            if vendedor_atual:
                total = float(row[-1]) if pd.notna(row[-1]) and isinstance(row[-1], (int, float)) and row[-1] != 0 else 0
                if 'HIST' in col1.upper() and 'TOTAL' in col1.upper() and 'GAP' not in col1.upper():
                    dados['vendedores'][vendedor_atual]['hist'] = total
                elif 'OBJ' in col1.upper() and 'TOTAL' in col1.upper() and 'GAP' not in col1.upper():
                    dados['vendedores'][vendedor_atual]['obj'] = total
                elif 'REAL' in col1.upper() and 'TOTAL' in col1.upper() and 'GAP' not in col1.upper():
                    dados['vendedores'][vendedor_atual]['real'] = total
        for nome, d in dados['vendedores'].items():
            if d.get('real', 0) > 0:
                print(f"      {nome}: REAL R$ {d['real']:,.0f}")

    # --- RESUMO FINANCEIRO ---
    if 'RESUMO FINANCEIRO' in xl.sheet_names:
        print("   → Extraindo Resumo Financeiro...")
        df = pd.read_excel(caminho, sheet_name='RESUMO FINANCEIRO', header=None)
        financeiro = []
        for i in range(4, 16):
            row = df.iloc[i].tolist()
            if pd.notna(row[0]) and str(row[0]).strip():
                mes = str(row[0]).strip()
                receita = float(row[1]) if pd.notna(row[1]) and isinstance(row[1], (int, float)) else 0
                despesa = float(row[2]) if pd.notna(row[2]) and isinstance(row[2], (int, float)) else 0
                pct = float(row[3]) if pd.notna(row[3]) and isinstance(row[3], (int, float)) else 0
                liquido = float(row[4]) if len(row) > 4 and pd.notna(row[4]) and isinstance(row[4], (int, float)) else receita - despesa
                financeiro.append({
                    'mes': mes,
                    'receita': round(max(receita, 0), 2),
                    'despesa': round(max(despesa, 0), 2),
                    'pct_despesa': round(abs(pct), 2),
                    'liquido': round(liquido, 2)
                })
        dados['financeiro'] = financeiro

    # --- COMISSÕES ---
    if 'COMISSÕES' in xl.sheet_names:
        print("   → Extraindo Comissões...")
        df = pd.read_excel(caminho, sheet_name='COMISSÕES', header=None)
        com_vend = {}
        for i in range(5, len(df)):
            row = df.iloc[i].tolist()
            empresa = str(row[0]).strip() if pd.notna(row[0]) else ''
            vendedor = str(row[1]).strip() if pd.notna(row[1]) and len(row) > 1 else ''
            if not empresa or empresa == '0' or not vendedor or vendedor == '0':
                continue
            if vendedor not in com_vend:
                com_vend[vendedor] = {m: 0 for m in MESES}
            for mes_i, mes in enumerate(MESES):
                base_col = 3 + mes_i * 3
                com_v = float(row[base_col+2]) if base_col+2 < len(row) and pd.notna(row[base_col+2]) and isinstance(row[base_col+2], (int, float)) else 0
                com_vend[vendedor][mes] = round(com_vend[vendedor][mes] + com_v, 2)
        dados['comissoes_vendedor'] = {v: d for v, d in com_vend.items() if any(d.values())}

    salvar_dados(dados)
    print("\n✅ Planilha processada com sucesso!")
    return dados

# ============================================================
#  PROCESSAR RELATÓRIO DE EMPRESA
# ============================================================
def processar_relatorio(caminho, empresa=None, mes=None, atualizar=False):
    """Processa um relatório Excel de uma indústria."""
    caminho = Path(caminho)
    print(f"\n📄 Processando relatório: {caminho.name}")

    empresa = empresa or detectar_empresa(caminho.name)
    mes = mes or detectar_mes(caminho.name)

    if not empresa:
        print("   ⚠️  Empresa não identificada. Use --empresa GRANADO (por exemplo)")
        return None
    if not mes:
        print("   ⚠️  Mês não identificado. Use --mes JANEIRO (por exemplo)")
        return None

    print(f"   🏭 Empresa: {empresa}")
    print(f"   📅 Mês: {mes}")

    ext = caminho.suffix.lower()
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(caminho)
    elif ext == '.csv':
        df = pd.read_csv(caminho, sep=';', encoding='latin-1')
    else:
        print("   ❌ Formato não suportado. Use .xlsx, .xls ou .csv")
        return None

    print(f"   📊 {len(df)} linhas de dados")
    print(f"   📋 Colunas: {list(df.columns)}")

    # Detectar coluna de valor líquido
    col_val = None
    for col in df.columns:
        if 'líquido' in str(col).lower() or 'liquido' in str(col).lower() or 'liquid' in str(col).lower():
            col_val = col
            break
    if col_val is None:
        for col in df.columns:
            if 'valor' in str(col).lower() or 'total' in str(col).lower() or 'faturad' in str(col).lower():
                col_val = col
                break

    if col_val:
        total = df[col_val].sum()
        print(f"   💰 Total {col_val}: R$ {total:,.2f}")
    else:
        print("   ⚠️  Coluna de valor não encontrada automaticamente")
        total = 0

    if atualizar and total > 0:
        dados = carregar_dados()
        mes_idx = MESES.index(mes)
        if empresa not in dados['empresas']:
            dados['empresas'][empresa] = {'hist': [0]*12, 'obj': [0]*12, 'real': [0]*12}
        atual = dados['empresas'][empresa].get('real', [0]*12)[mes_idx]
        print(f"\n   Valor atual: R$ {atual:,.2f}")
        print(f"   Novo valor:  R$ {total:,.2f}")
        resp = input("   Confirmar atualização? (s/N): ").strip().lower()
        if resp == 's':
            dados['empresas'][empresa]['real'][mes_idx] = round(total, 2)
            salvar_dados(dados)
            print(f"   ✅ {empresa} / {mes} atualizado para R$ {total:,.2f}")
        else:
            print("   ↩️  Atualização cancelada")

    return total

# ============================================================
//  PROCESSAR PASTA DE RELATÓRIOS
// ============================================================
def processar_pasta(pasta, atualizar=False):
    """Processa todos os arquivos Excel de uma pasta."""
    pasta = Path(pasta)
    arquivos = list(pasta.glob('*.xlsx')) + list(pasta.glob('*.xls')) + list(pasta.glob('*.csv'))
    print(f"\n📁 Pasta: {pasta}")
    print(f"   {len(arquivos)} arquivos encontrados")
    for arq in sorted(arquivos):
        processar_relatorio(arq, atualizar=atualizar)

# ============================================================
#  PUSH PARA GITHUB
# ============================================================
def push_github(mensagem=None):
    from datetime import date
    if mensagem is None:
        mensagem = f"Atualização dashboard — {date.today().strftime('%d/%m/%Y')}"
    print("\n🚀 Enviando para GitHub...")
    try:
        subprocess.run(['git', 'add', 'index.html', 'data/data.json'], check=True)
        result = subprocess.run(['git', 'commit', '-m', mensagem], capture_output=True, text=True)
        if result.returncode != 0 and 'nothing to commit' in result.stdout + result.stderr:
            print("   (sem alterações novas para enviar)")
            return
        subprocess.run(['git', 'push'], check=True)
        print("✅ Dashboard enviado para GitHub com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no git: {e}")
        print("   Execute 'bash configurar_github.sh' para configurar o repositório.")

# ============================================================
#  MAIN
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dashboard Comercial — Importador de Dados')
    parser.add_argument('--planilha', help='Caminho da Planilha Comercial 2026.xlsx')
    parser.add_argument('--relatorio', help='Caminho de um relatório de empresa')
    parser.add_argument('--pasta', help='Pasta com vários relatórios')
    parser.add_argument('--empresa', help='Nome da empresa (ex: GRANADO)')
    parser.add_argument('--mes', help='Mês (ex: MAIO)')
    parser.add_argument('--atualizar', action='store_true', help='Aplicar alterações no JSON (pede confirmação)')
    parser.add_argument('--push', action='store_true', help='Enviar para GitHub após processar')
    parser.add_argument('--sem-push', action='store_true', help='Processar sem enviar para GitHub')
    args = parser.parse_args()

    if not any([args.planilha, args.relatorio, args.pasta]):
        parser.print_help()
        print("\n📌 Exemplos:")
        print("  python importar_dados.py --planilha 'PLANILHA COMERCIAL 2026.xlsx'")
        print("  python importar_dados.py --planilha 'planilha.xlsx' --sem-push")
        print("  python importar_dados.py --relatorio 'GRANADO MAIO 26.xlsx' --atualizar")
        print("  python importar_dados.py --pasta 'RELATORIOS/JUNHO/' --atualizar")
        sys.exit(0)

    if args.planilha:
        processar_planilha(args.planilha)
        # Push automático ao processar planilha principal (use --sem-push para desativar)
        if not args.sem_push:
            push_github()

    if args.relatorio:
        processar_relatorio(args.relatorio, empresa=args.empresa, mes=args.mes, atualizar=args.atualizar)
        if args.push:
            push_github()

    if args.pasta:
        processar_pasta(args.pasta, atualizar=args.atualizar)
        if args.push:
            push_github()
