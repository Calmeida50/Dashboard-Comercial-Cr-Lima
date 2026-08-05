#!/bin/bash
# ============================================================
#  Publicar o dashboard no GitHub Pages
#  Uso: bash publicar.sh  ["mensagem opcional"]
# ============================================================
set -u
PASTA="/Users/cristianoalmeida/Desktop/Projeto Comercial IA"
SITE="https://calmeida50.github.io/Dashboard-Comercial-Cr-Lima/"
cd "$PASTA" || { echo "Pasta nao encontrada: $PASTA"; exit 1; }

echo ""
echo "=============================================="
echo "   Publicar Dashboard Comercial"
echo "=============================================="
echo ""

# 1. Confere se ha algo para publicar
if [ -z "$(git status --porcelain index.html)" ]; then
  echo "Nada mudou no index.html. Nada a publicar."
  exit 0
fi

# 2. Traz o que estiver no remoto antes de enviar
echo "-> Buscando atualizacoes do remoto..."
git fetch -q origin
ATRAS=$(git rev-list --count HEAD..origin/main)
if [ "$ATRAS" -gt 0 ]; then
  echo ""
  echo "ATENCAO: o remoto tem $ATRAS commit(s) que voce nao tem."
  echo "Alguem publicou de outro lugar. Resolva antes de continuar:"
  echo "   git pull --rebase"
  exit 1
fi

# 3. Backup local antes de publicar
mkdir -p _backups
cp index.html "_backups/index.html.bak_$(date +%Y%m%d_%H%M)"
echo "-> Backup salvo em _backups/"

# 4. Commit e envio
MSG="${1:-Atualizacao dashboard - $(date '+%d/%m/%Y %H:%M')}"
git add index.html data/data.json 2>/dev/null
git commit -q -m "$MSG"

echo "-> Enviando para o GitHub..."
if git push -q origin main; then
  echo ""
  echo "=============================================="
  echo "  Publicado com sucesso."
  echo "  O GitHub Pages leva ~1 minuto para atualizar."
  echo "  $SITE"
  echo "  (na primeira visita use Cmd+Shift+R)"
  echo "=============================================="
else
  echo ""
  echo "Falhou o envio. O commit local foi feito."
  echo "Tente novamente com: git push origin main"
  exit 1
fi
echo ""
