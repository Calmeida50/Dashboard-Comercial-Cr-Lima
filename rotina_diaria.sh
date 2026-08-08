#!/bin/bash
# ============================================================
#  rotina_diaria.sh — varre o Drive, processa o que mudou e publica.
#
#  Roda as 18h todo dia (launchd). Se o Mac estava desligado no horario,
#  dispara ao ligar.
#
#  sincronizar.py compara uma impressao digital de cada pasta e so roda os
#  coletores das categorias que mudaram — por isso a execucao normal leva
#  segundos, e nao os ~10 minutos da leitura completa.
#
#  Publica AUTOMATICAMENTE (decisao do Cristiano, 08/08/2026: "precisa ser
#  automatico, isso diminui o retrabalho"). A protecao que resta e a trava de
#  conferencia dentro de cada coletor: se o parser deixar de reproduzir o
#  historico, ele aborta ANTES de gravar e a rotina nao publica nada.
# ============================================================
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
PASTA="/Users/cristianoalmeida/Desktop/Projeto Comercial IA"
LOG="$PASTA/_backups/rotina_diaria.log"
cd "$PASTA" || exit 1
mkdir -p _backups

carimbo() { date '+%Y-%m-%d %H:%M:%S'; }
notificar() {
  /usr/bin/osascript -e "display notification \"$2\" with title \"Dashboard Comercial\" subtitle \"$1\"" 2>/dev/null
}

{
echo ""
echo "=============================================="
echo "  ROTINA DIARIA — $(carimbo)"
echo "=============================================="

DRIVE="$HOME/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/Meu Drive/PROJETO COMERCIAL IA"
if [ ! -d "$DRIVE" ]; then
  echo "ERRO: pasta do Drive inacessivel. O Google Drive esta rodando?"
  notificar "Falhou" "Pasta do Google Drive inacessivel"
  exit 1
fi

SAIDA=$(/usr/bin/python3 sincronizar.py 2>&1)
echo "$SAIDA"

if echo "$SAIDA" | grep -q "ABORTOU"; then
  QUAL=$(echo "$SAIDA" | grep "ABORTOU" | head -1)
  notificar "Abortado" "$QUAL - nada foi publicado"
  echo "-> abortado pela trava de conferencia"
  exit 2
fi

# publica so se o dashboard realmente mudou
if [ -z "$(git status --porcelain index.html)" ]; then
  echo "-> index.html inalterado; nada a publicar"
  exit 0
fi

ATUALIZADOS=$(echo "$SAIDA" | grep -c "atualizado")
echo ""
echo "-> publicando ($ATUALIZADOS categoria(s) atualizada(s))..."
if bash publicar.sh "Atualizacao automatica - $(date '+%d/%m/%Y %H:%M')"; then
  RESUMO=$(echo "$SAIDA" | grep "  - " | sed 's/^  - //' | paste -sd '; ' -)
  notificar "Publicado" "$RESUMO"
  echo "-> publicado com sucesso"
else
  notificar "Erro ao publicar" "Dados gravados mas o envio falhou"
  echo "-> ERRO no publicar.sh"
  exit 1
fi

echo "fim: $(carimbo)"
} >> "$LOG" 2>&1
