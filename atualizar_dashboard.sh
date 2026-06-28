#!/bin/bash
# ============================================================
#  Atualizar Dashboard + Enviar para GitHub
#  Uso: bash atualizar_dashboard.sh
# ============================================================

PASTA="/Users/cristianoalmeida/Desktop/PROJETO COMERCIAL IA"
PLANILHA="$PASTA/PLANILHA COMERCIAL 2026.xlsx"
cd "$PASTA" || { echo "❌ Pasta não encontrada"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Atualizar Dashboard Comercial São João"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verificar se a planilha existe
if [ ! -f "$PLANILHA" ]; then
    echo "❌ Planilha não encontrada em:"
    echo "   $PLANILHA"
    exit 1
fi

echo "📊 Processando planilha..."
python3 importar_dados.py --planilha "PLANILHA COMERCIAL 2026.xlsx"

if [ $? -ne 0 ]; then
    echo "❌ Erro ao processar planilha"
    exit 1
fi

echo ""
echo "🚀 Enviando para GitHub..."
git add index.html data/data.json
git commit -m "Atualização dashboard — $(date '+%d/%m/%Y %H:%M')"
git push

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Dashboard atualizado e enviado para o GitHub!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo ""
    echo "⚠️  Dados atualizados localmente mas falhou o envio."
    echo "   Rode: git push  (para tentar novamente)"
fi
echo ""
