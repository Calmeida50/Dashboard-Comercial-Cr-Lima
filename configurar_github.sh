#!/bin/bash
# ============================================================
#  Configuração inicial do repositório GitHub
#  Dashboard Comercial São João
#  Execute UMA VEZ para vincular ao GitHub
# ============================================================

PASTA="/Users/cristianoalmeida/Desktop/PROJETO COMERCIAL IA"
cd "$PASTA" || { echo "❌ Pasta não encontrada"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Configuração GitHub — Dashboard Comercial"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verificar se já está configurado
if [ -d ".git" ]; then
    echo "✅ Repositório git já inicializado."
    echo "   Fazendo push da versão atual..."
    git add index.html importar_dados.py
    git commit -m "Atualização dashboard" 2>/dev/null || echo "   (sem alterações novas)"
    git push
    echo ""
    echo "✅ Pronto! Código enviado para o GitHub."
    exit 0
fi

# ─── Coletar informações ───────────────────────────────────
echo "Antes de começar, acesse https://github.com/new e crie"
echo "um repositório PRIVADO chamado: dashboard-comercial"
echo ""
read -p "Seu usuário do GitHub: " USUARIO
echo ""

# Verificar se GitHub CLI está disponível
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI encontrado — autenticação simplificada"
    echo ""
    gh auth status 2>/dev/null || gh auth login

    # Inicializar git
    git init
    git add index.html importar_dados.py configurar_github.sh atualizar_dashboard.sh 2>/dev/null
    git add data/data.json 2>/dev/null
    git commit -m "Dashboard Comercial São João — versão inicial"
    git branch -M main

    git remote add origin "https://github.com/$USUARIO/dashboard-comercial.git"
    git push -u origin main

else
    echo "📌 Você precisa de um Token de Acesso Pessoal do GitHub."
    echo ""
    echo "   1. Acesse: https://github.com/settings/tokens/new"
    echo "   2. Em 'Note' escreva: dashboard-comercial"
    echo "   3. Em 'Expiration' escolha: No expiration"
    echo "   4. Em 'Scopes' marque: ✅ repo"
    echo "   5. Clique 'Generate token' e COPIE o token"
    echo ""
    read -p "Cole o token aqui: " TOKEN
    echo ""

    # Inicializar git
    git init
    git add index.html importar_dados.py configurar_github.sh atualizar_dashboard.sh 2>/dev/null
    git add data/data.json 2>/dev/null
    git commit -m "Dashboard Comercial São João — versão inicial"
    git branch -M main

    REMOTE="https://$USUARIO:$TOKEN@github.com/$USUARIO/dashboard-comercial.git"
    git remote add origin "$REMOTE"
    git push -u origin main

    # Salvar config para próximos pushes (sem expor o token no script)
    git config credential.helper store
    echo "https://$USUARIO:$TOKEN@github.com" >> ~/.git-credentials
    echo "✅ Credenciais salvas — próximos pushes serão automáticos"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Repositório configurado com sucesso!"
echo "   https://github.com/$USUARIO/dashboard-comercial"
echo ""
echo "   Para atualizar o dashboard no futuro:"
echo "   bash atualizar_dashboard.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
