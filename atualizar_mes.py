#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   ATUALIZAR DASHBOARD COMERCIAL — Script Mensal              ║
║   Uso: python3 atualizar_mes.py                              ║
║                                                              ║
║   1. Coloca os ficheiros de faturamento na pasta NOVOS_DADOS/║
║      Ex: FATURAMENTO_AQUAFAST_JULHO_26.xlsx                  ║
║   2. Corre este script                                       ║
║   3. O dashboard é atualizado e publicado automaticamente    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re, sys, shutil, subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime

# ============================================================
#  CONFIGURAÇÃO
# ============================================================
PASTA_PROJETO   = Path("/Users/cristianoalmeida/Desktop/PROJETO COMERCIAL IA")
INDEX_HTML      = PASTA_PROJETO / "index.html"
PASTA_NOVOS     = PASTA_PROJETO / "NOVOS_DADOS"      # coloca aqui os xlsx novos
PASTA_ARQUIVO   = PASTA_PROJETO / "FATURAMENTO DAS EMPRESAS"  # arquivo após processar
AUTO_PUSH       = True   # False = não publica no GitHub automaticamente

# ============================================================
#  MAPEAMENTO DE MESES
# ============================================================
MESES_IDX = {
    'JANEIRO':0, 'FEVEREIRO':1, 'MARÇO':2, 'MARCO':2,
    'ABRIL':3, 'MAIO':4, 'JUNHO':5, 'JULHO':6,
    'AGOSTO':7, 'SETEMBRO':8, 'OUTUBRO':9,
    'NOVEMBRO':10, 'DEZEMBRO':11,
    # abreviações
    'JAN':0,'FEV':1,'MAR':2,'ABR':3,'MAI':4,'JUN':5,
    'JUL':6,'AGO':7,'SET':8,'OUT':9,'NOV':10,'DEZ':11,
}

MESES_NOME = [
    'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'
]

# Empresas reconhecidas (tal como aparecem nos dados do dashboard)
EMPRESAS_MAP = {
    'AQUAFAST':    'AQUAFAST',
    'GRANADO':     'GRANADO',
    'CLESS':       'CLESS',
    'EVERGREEN':   'EVER GREEN',
    'EVER GREEN':  'EVER GREEN',
    'EVER_GREEN':  'EVER GREEN',
    'PRUDENCE':    'PRUDENCE',
    'BELLIZ':      'BELLIZ',
    'FIATLUX':     'FIAT LUX',
    'FIAT LUX':    'FIAT LUX',
    'FIAT_LUX':    'FIAT LUX',
    'PAYOT':       'PAYOT',
    'DEPIMIEL':    'DEPIMIEL',
    'BOTANICA':    'BOTÂNICA',
    'BOTÂNICA':    'BOTÂNICA',
    'KISABOR':     'KISABOR',
}

# ============================================================
#  FUNÇÕES AUXILIARES
# ============================================================

def sep():
    print("━" * 52)

def normalizar(s):
    if not s or str(s).strip().upper() in ('NAN', 'NONE', ''):
        return ''
    return re.sub(r'\s+', ' ', str(s).strip().upper())

def detectar_empresa_mes(nome_arquivo):
    """Detecta empresa e mês a partir do nome do ficheiro."""
    nome = Path(nome_arquivo).stem.upper()
    # Substituir acentos comuns
    nome = nome.replace('Ç','C').replace('Ã','A').replace('Â','A').replace('É','E')
    partes = re.split(r'[_\s\-]+', nome)

    empresa = None
    mes_idx = None

    # Detectar mês
    for p in partes:
        if p in MESES_IDX:
            mes_idx = MESES_IDX[p]
            break

    # Detectar empresa — procura por palavras-chave
    nome_sem_sep = nome.replace('_',' ')
    for chave, valor in EMPRESAS_MAP.items():
        if chave in nome_sem_sep or chave in partes:
            empresa = valor
            break

    return empresa, mes_idx

def ler_faturamento(filepath):
    """
    Lê ficheiro xlsx de faturamento.
    Devolve ({nome_normalizado: total}, {nome_normalizado: [nf1, nf2, ...]}).
    Suporta cabeçalho na linha 1 ou linha 2 (auto-detecção).
    Valores negativos = devoluções (reduzem o total automaticamente).
    """
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"  ❌ Erro ao ler o ficheiro: {e}")
        return None, None

    # Auto-detectar cabeçalho deslocado (ex: GRANADO — linha 1 contém os nomes das colunas)
    n_unnamed = sum(1 for c in df.columns if str(c).startswith('Unnamed:'))
    if n_unnamed > len(df.columns) // 2:
        try:
            df = pd.read_excel(filepath, header=1)
            print(f"  ℹ️  Cabeçalho deslocado detectado — relido com header=1")
        except Exception as e:
            print(f"  ❌ Erro ao reprocessar cabeçalho: {e}")
            return None, None

    cols_upper = {re.sub(r'\s+','_', c.strip().upper()): c for c in df.columns}

    # Coluna de cliente
    cliente_col = None
    for cand in ['CLIENTE','RAZAO_SOCIAL','RAZÃO_SOCIAL','NOME_CLIENTE','NOME']:
        if cand in cols_upper:
            cliente_col = cols_upper[cand]
            break
    if not cliente_col:
        print(f"  ❌ Coluna de CLIENTE não encontrada.")
        print(f"     Colunas disponíveis: {list(df.columns)}")
        return None, None

    # Coluna de valor (RECEITA > BRUTO_COM_IMP > VALOR)
    valor_col = None
    for cand in ['RECEITA','BRUTO_COM_IMP','VALOR_LIQUIDO','VALOR','TOTAL']:
        if cand in cols_upper:
            valor_col = cols_upper[cand]
            break
    if not valor_col:
        print(f"  ❌ Coluna de VALOR não encontrada.")
        print(f"     Colunas disponíveis: {list(df.columns)}")
        return None, None

    # Coluna de NF (opcional) — suporta vários nomes de coluna
    nf_col = None
    for cand in ['NF','NUMERO_SERIE','NÚMERO_SÉRIE','NUMERO_NF','NOTA_FISCAL','NUMERO_NOTA','NUM_NF','SERIE']:
        if cand in cols_upper:
            nf_col = cols_upper[cand]
            break

    nf_info = f" | NF: '{nf_col}'" if nf_col else " | NF: não encontrada"
    print(f"  → Cliente: '{cliente_col}' | Valor: '{valor_col}'{nf_info}")

    def limpar_nome(s):
        """Remove sufixo de código numérico: 'EMPRESA SA-123456' → 'EMPRESA SA'"""
        return re.sub(r'-\d{4,}$', '', str(s)).strip()

    totais = {}
    nfs    = {}  # {nome_normalizado: [nf1, nf2, ...]}
    for _, row in df.iterrows():
        nome = normalizar(limpar_nome(row[cliente_col]))
        if not nome or nome in ('TOTAL','SUBTOTAL','NAN',''):
            continue
        try:
            val = float(row[valor_col]) if pd.notna(row[valor_col]) else 0.0
        except (ValueError, TypeError):
            continue
        totais[nome] = totais.get(nome, 0.0) + val

        if nf_col and pd.notna(row.get(nf_col, None)):
            nf_val = str(row[nf_col]).strip()
            if nf_val and nf_val.upper() not in ('NAN', 'NONE', ''):
                nfs.setdefault(nome, []).append(nf_val)

    return totais, nfs

def carregar_dados_html(html):
    """Extrai JSON de DADOS_EMBEDDED do HTML."""
    inicio = html.find('const DADOS_EMBEDDED = ')
    if inicio == -1:
        raise ValueError("DADOS_EMBEDDED não encontrado no index.html")
    inicio += len('const DADOS_EMBEDDED = ')
    fim = html.find(';\n', inicio)
    return json.loads(html[inicio:fim]), inicio, fim

def salvar_dados_html(html, dados, inicio, fim):
    """Substitui DADOS_EMBEDDED no HTML."""
    novo_json = json.dumps(dados, ensure_ascii=False, separators=(',',':'))
    return html[:inicio] + novo_json + html[fim:]

def atualizar_teto_meses(html, max_mes_idx):
    """Atualiza Math.min(currentM + 1, N) para o novo teto de meses com dados."""
    novo_teto = max_mes_idx + 1
    # Cobre currentM e currentMonthIdx
    html = re.sub(
        r'Math\.min\(currentM \+ 1,\s*\d+\)',
        f'Math.min(currentM + 1, {novo_teto})',
        html
    )
    html = re.sub(
        r'Math\.min\(currentMonthIdx \+ 1,\s*\d+\)',
        f'Math.min(currentMonthIdx + 1, {novo_teto})',
        html
    )
    return html

def construir_lookup(cd_empresa):
    """
    Constrói dicionário {nome_normalizado: (vendedor, indice)} para matching rápido.
    """
    lookup = {}
    for vend, lista in cd_empresa.items():
        for i, cliente in enumerate(lista):
            chave = normalizar(cliente.get('nome', ''))
            if chave:
                lookup[chave] = (vend, i)
    return lookup

# ============================================================
#  SCRIPT PRINCIPAL
# ============================================================

def main():
    print()
    sep()
    print("  Atualizar Dashboard Comercial — São João")
    sep()
    print()

    # Criar pastas se não existirem
    PASTA_NOVOS.mkdir(exist_ok=True)
    PASTA_ARQUIVO.mkdir(exist_ok=True)

    # Verificar ficheiros novos
    ficheiros = sorted(
        list(PASTA_NOVOS.glob("*.xlsx")) +
        list(PASTA_NOVOS.glob("*.XLSX")) +
        list(PASTA_NOVOS.glob("*.xls"))
    )

    if not ficheiros:
        print(f"📂 Pasta NOVOS_DADOS/ está vazia.")
        print()
        print("   Para atualizar o dashboard:")
        print(f"   1. Abre a pasta:  {PASTA_NOVOS}")
        print("   2. Cola os ficheiros de faturamento do mês")
        print("   3. Nomeie como:  FATURAMENTO_EMPRESA_MES_26.xlsx")
        print("      Ex: FATURAMENTO_AQUAFAST_JULHO_26.xlsx")
        print("   4. Corre este script novamente")
        print()
        return

    print(f"📂 {len(ficheiros)} ficheiro(s) em NOVOS_DADOS/:")
    for f in ficheiros:
        print(f"   • {f.name}")
    print()

    # Carregar index.html
    if not INDEX_HTML.exists():
        print(f"❌ index.html não encontrado em:\n   {INDEX_HTML}")
        return

    html = INDEX_HTML.read_text(encoding='utf-8')
    dados, pos_inicio, pos_fim = carregar_dados_html(html)
    cd = dados.get('clientes_detalhado', {})

    # Determinar teto atual de meses
    max_mes_com_dados = 5  # mínimo = Junho

    atualizacoes = []
    resumo_erros = []

    for filepath in ficheiros:
        print(f"📊 {filepath.name}")
        empresa, mes_idx = detectar_empresa_mes(filepath.name)

        if empresa is None:
            print(f"  ⚠️  Empresa não reconhecida no nome do ficheiro.")
            print(f"     Renomeia para incluir: AQUAFAST, GRANADO, CLESS, PRUDENCE,")
            print(f"     BELLIZ, EVERGREEN, FIAT LUX, PAYOT, DEPIMIEL, BOTANICA")
            resumo_erros.append(f"{filepath.name} — empresa não reconhecida")
            continue

        if mes_idx is None:
            print(f"  ⚠️  Mês não reconhecido no nome do ficheiro.")
            print(f"     Inclui o mês em português: JULHO, AGOSTO, SETEMBRO...")
            resumo_erros.append(f"{filepath.name} — mês não reconhecido")
            continue

        print(f"  Empresa: {empresa}  |  Mês: {MESES_NOME[mes_idx]}")

        # Encontrar empresa nos dados
        chave_empresa = None
        for k in cd:
            if normalizar(k) == normalizar(empresa):
                chave_empresa = k
                break

        if chave_empresa is None:
            print(f"  ⚠️  '{empresa}' não encontrada nos dados do dashboard.")
            print(f"     Empresas disponíveis: {', '.join(cd.keys())}")
            resumo_erros.append(f"{filepath.name} — empresa '{empresa}' não está nos dados")
            continue

        # Ler faturamento
        fat, nfs_fat = ler_faturamento(filepath)
        if fat is None:
            resumo_erros.append(f"{filepath.name} — erro ao ler")
            continue

        total_arquivo = sum(fat.values())
        print(f"  Total faturamento: R$ {total_arquivo:,.2f}  ({len(fat)} clientes no arquivo)")

        # Fazer matching com clientes_detalhado
        lookup = construir_lookup(cd[chave_empresa])
        matches = 0
        nao_encontrados = []

        for nome_fat, valor in fat.items():
            if nome_fat in lookup:
                vend, idx = lookup[nome_fat]
                # Garantir array com 12 posições
                meses = cd[chave_empresa][vend][idx].setdefault('meses', [0]*12)
                while len(meses) < 12:
                    meses.append(0)
                meses[mes_idx] = round(valor, 2)
                matches += 1
            else:
                nao_encontrados.append((nome_fat, valor))

        # Atualizar NF em comissoes_detalhe (quando o ficheiro tem coluna de NF)
        if nfs_fat:
            mes_key = MESES_NOME[mes_idx].upper()
            com_det = dados.get('comissoes_detalhe', {})
            nf_updates = 0
            for vend_entries in com_det.values():
                if mes_key not in vend_entries:
                    continue
                emp_entries = vend_entries[mes_key].get(chave_empresa, [])
                for entry in emp_entries:
                    nome_entry = normalizar(re.sub(r'-\d{4,}$', '', entry.get('nome', '')).strip())
                    if nome_entry in nfs_fat and (not entry.get('nf') or entry['nf'] == '—'):
                        entry['nf'] = '/'.join(nfs_fat[nome_entry])
                        nf_updates += 1
            if nf_updates:
                print(f"  🔢 {nf_updates} NF(s) atualizada(s) em comissoes_detalhe")

        print(f"  ✅ {matches} cliente(s) atualizados")

        if nao_encontrados:
            nao_encontrados.sort(key=lambda x: -abs(x[1]))
            print(f"  ⚠️  {len(nao_encontrados)} cliente(s) sem correspondência (top 5):")
            for nome, val in nao_encontrados[:5]:
                print(f"     • {nome[:50]}: R$ {val:,.2f}")
            if len(nao_encontrados) > 5:
                print(f"     ... e mais {len(nao_encontrados)-5}")

        max_mes_com_dados = max(max_mes_com_dados, mes_idx)
        atualizacoes.append(f"{empresa}/{MESES_NOME[mes_idx]}")

        # Mover ficheiro para arquivo
        destino = PASTA_ARQUIVO / filepath.name
        if destino.exists():
            destino = PASTA_ARQUIVO / f"{filepath.stem}_atualizado_{datetime.now().strftime('%d%m%Y')}{filepath.suffix}"
        shutil.move(str(filepath), str(destino))
        print(f"  📁 Arquivado em FATURAMENTO DAS EMPRESAS/")
        print()

    if not atualizacoes:
        print("Nenhuma atualização realizada. Verifica os erros acima.")
        if resumo_erros:
            print("\nErros:")
            for e in resumo_erros:
                print(f"  • {e}")
        return

    # Atualizar HTML com novos dados e novo teto
    html_atualizado = salvar_dados_html(html, dados, pos_inicio, pos_fim)
    html_atualizado = atualizar_teto_meses(html_atualizado, max_mes_com_dados)
    INDEX_HTML.write_text(html_atualizado, encoding='utf-8')

    print(f"✅ index.html atualizado: {', '.join(atualizacoes)}")
    print(f"   Teto de meses: {max_mes_com_dados + 1} ({MESES_NOME[max_mes_com_dados]})")
    print()

    # Git push
    if AUTO_PUSH:
        os.chdir(PASTA_PROJETO)
        msg = f"Atualização {', '.join(atualizacoes)} — {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        subprocess.run(['git', 'add', 'index.html'], capture_output=True)
        r = subprocess.run(['git', 'commit', '-m', msg], capture_output=True, text=True)
        if 'nothing to commit' in r.stdout:
            print("ℹ️  Sem alterações para publicar (dados idênticos).")
        else:
            r2 = subprocess.run(['git', 'push'], capture_output=True, text=True)
            if r2.returncode == 0:
                print("🚀 Publicado no GitHub! Aguarda 1-2 min e atualiza o browser.")
            else:
                print("⚠️  Erro no push. Tenta manualmente: git push")
                print(r2.stderr)
    else:
        print("ℹ️  AUTO_PUSH=False — publica manualmente com: git push")

    print()
    sep()
    print("  Concluído!")
    if resumo_erros:
        print()
        print("  ⚠️  Ficheiros com erros (não processados):")
        for e in resumo_erros:
            print(f"     • {e}")
    sep()
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo utilizador.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback; traceback.print_exc()
