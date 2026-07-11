#!/bin/bash
# Instala as dependências necessárias para o script de atualização
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Instalar dependências — Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Instalando pandas e openpyxl..."
pip3 install pandas openpyxl --quiet
if [ $? -eq 0 ]; then
    echo "✅ Dependências instaladas com sucesso!"
else
    echo "⚠️  Tenta com: pip install pandas openpyxl"
fi
echo ""
