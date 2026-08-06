#!/bin/bash
# ============================================================
#  rotina_diaria.sh — coleta o faturamento do mes corrente,
#  grava no dashboard e publica. Roda sozinho as 18h.
#
#  Encadeia:  atualizar_faturamento.py  ->  publicar.sh
#  Aborta sem gravar se a trava de conferencia falhar.
# ============================================================
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
PASTA="/Users/cristianoalmeida/Desktop/Projeto Comercial IA"
LOG="$PASTA/_backups/rotina_diaria.log"
cd "$PASTA" || exit 1
mkdir -p _backups

carimbo() { date '+%Y-%m-%d %H:%M:%S'; }
notificar() {
  # $1 = titulo, $2 = mensagem
  /usr/bin/osascript -e "display notification \"$2\" with title \"Dashboard Comercial\" subtitle \"$1\"" 2>/dev/null
}

{
echo ""
echo "=============================================="
echo "  ROTINA DIARIA — $(carimbo)"
echo "=============================================="

# --- 1. o Drive esta acessivel?
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/Meu Drive/PROJETO COMERCIAL IA"
if [ ! -d "$DRIVE" ]; then
  echo "ERRO: pasta do Drive nao encontrada. O Google Drive esta rodando?"
  notificar "Falhou" "Pasta do Google Drive inacessivel"
  exit 1
fi

# --- 2. coleta e grava (a trava de conferencia mora aqui dentro)
# Processa DOIS meses: o anterior e o corrente.
# Motivo: na primeira semana do mes o Cristiano salva os relatorios do mes que
# fechou. Rodar so o mes corrente deixaria a rotina em branco justamente na
# semana em que os dados chegam. Reprocessar e idempotente.
MES_ATUAL=$(date '+%m'); ANO_ATUAL=$(date '+%Y')
if [ "$MES_ATUAL" = "01" ]; then
  MES_ANT=12; ANO_ANT=$((ANO_ATUAL - 1))
else
  MES_ANT=$((10#$MES_ATUAL - 1)); ANO_ANT=$ANO_ATUAL
fi
NOMES=(JANEIRO FEVEREIRO MARCO ABRIL MAIO JUNHO JULHO AGOSTO SETEMBRO OUTUBRO NOVEMBRO DEZEMBRO)
N_ANT=${NOMES[$((MES_ANT - 1))]}
N_ATU=${NOMES[$((10#$MES_ATUAL - 1))]}

SAIDA=""
CODIGO=0
for PAR in "$N_ANT $ANO_ANT" "$N_ATU $ANO_ATUAL"; do
  set -- $PAR
  echo ""
  echo "--- processando $1/$2"
  S=$(/usr/bin/python3 atualizar_faturamento.py "$1" "$2" 2>&1)
  C=$?
  echo "$S"
  SAIDA="$SAIDA$S"$'\n'
  [ $C -eq 2 ] && CODIGO=2
done

if [ $CODIGO -eq 2 ]; then
  echo "-> ABORTADO pela trava de conferencia. Nada foi gravado."
  notificar "Abortado" "O coletor divergiu do historico. Nada foi gravado."
  exit 2
fi
if [ $CODIGO -ne 0 ]; then
  echo "-> nada a fazer hoje"
  exit 0
fi

# --- 3. mudou alguma coisa?
if [ -z "$(git status --porcelain index.html)" ]; then
  echo "-> index.html inalterado; nada a publicar"
  exit 0
fi

# --- 4. publica
echo ""
echo "-> publicando..."
if bash publicar.sh "Faturamento automatico - $(date '+%d/%m/%Y')"; then
  # resumo para a notificacao: empresas gravadas e faltantes
  GRAVADAS=$(echo "$SAIDA" | grep -cE "^      [A-Z].*->")
  FALTAM=$(echo "$SAIDA" | sed -n 's/.*sem arquivo: //p' | head -1)
  TOTAL=$(echo "$SAIDA" | grep "GERAL" | sed 's/.*-> *//')
  MSG="Julho: $TOTAL"
  [ -n "$FALTAM" ] && MSG="$MSG | faltam: $FALTAM"
  notificar "Publicado" "$MSG"
  echo "-> publicado com sucesso"
else
  notificar "Erro ao publicar" "Dados gravados mas o envio falhou"
  echo "-> ERRO no publicar.sh"
  exit 1
fi

echo "fim: $(carimbo)"
} >> "$LOG" 2>&1
