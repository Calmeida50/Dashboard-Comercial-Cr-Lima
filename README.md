# Dashboard Comercial — Cr Lima

Site publicado: https://calmeida50.github.io/Dashboard-Comercial-Cr-Lima/
Atalho na Area de Trabalho: `Dashboard Comercial.html` (redireciona para o site)

Esta pasta e a UNICA copia oficial do projeto.

---

## As duas velocidades do dashboard

O dashboard tem duas fontes de dados independentes, que NAO se conversam.

### Diario — automatico, sem publicar

A tela **Mes Corrente** le a planilha Google **MASTER DATA** (pasta
`PROJETO COMERCIAL IA` no Drive) direto do navegador, e recarrega sozinha
a cada 2 minutos enquanto a tela estiver aberta.

Quem lancar pedido na MASTER DATA ve o reflexo no site em ate 2 minutos.
Nao e preciso rodar script nem publicar nada.

### Mensal — manual, exige publicar

Todas as outras telas (Visao Geral, YTD, Clientes, Ranking, One Page,
Receita Liquida, Financeiro, Comissoes, Sell Out) leem a constante
`DADOS_EMBEDDED`, um JSON de ~600 KB gravado dentro do proprio `index.html`.

Enquanto nao publicar, a mudanca so existe na sua maquina.

---

## Rotina mensal (passo a passo)

1. Baixe do Drive os `FATURAMENTO_<EMPRESA>_<MES>_26.xlsx` do mes fechado
2. Coloque os arquivos em `NOVOS_DADOS/`
3. Rode:

       python3 atualizar_mes.py

   Ele le os xlsx, casa os nomes de cliente pelos aliases, soma por
   empresa/vendedor, reescreve o `DADOS_EMBEDDED` no `index.html` e move
   os arquivos processados para `FATURAMENTO DAS EMPRESAS/`.

4. Confira no navegador abrindo o `index.html` local
5. Publique:

       bash publicar.sh "Faturamento julho 2026"

---

## Publicacao

O `publicar.sh` e o UNICO caminho de publicacao. Ele:

- verifica se o `index.html` mudou (se nao mudou, nao faz nada)
- busca o remoto antes de enviar e AVISA se alguem publicou de outro lugar,
  em vez de gerar conflito
- salva um backup em `_backups/` antes de enviar
- faz commit e push

O GitHub Pages leva cerca de 1 minuto para reconstruir. Na primeira visita
use Cmd+Shift+R para furar o cache.

Autenticacao e por SSH (chave `~/.ssh/id_ed25519_github`). Nao ha token
gravado em lugar nenhum — se algum dia voltar a pedir senha, o problema e
a chave, nao o token.

---

## Estrutura da pasta

    index.html      o dashboard inteiro (HTML + CSS + JS + dados embutidos)
    atualizar_mes.py  processa os xlsx do mes e reescreve os dados no index.html
    publicar.sh     unico caminho de publicacao
    NOVOS_DADOS/    entrada: coloque aqui os xlsx do mes a processar
    FATURAMENTO DAS EMPRESAS/  arquivo dos xlsx ja processados
    RELATORIOS DE COMISSAO/    relatorios de comissao por ano/mes
    FINANCEIRO/     despesa juridica e receitas por empresa
    _backups/       versoes antigas do index.html e a rota legada
    _ARQUIVADO_*/   clones antigos do repositorio, mantidos por seguranca

---

## Armadilhas conhecidas

**Pastas com espaco no fim do nome.** Ja aconteceu de existir
`FATURAMENTO DAS EMPRESAS` e `FATURAMENTO DAS EMPRESAS ` (com espaco final)
ao mesmo tempo. Sao pastas distintas para o sistema e identicas a olho nu no
Finder. Se salvar na errada, o script nao encontra o arquivo e NAO da erro —
o mes simplesmente some. Ao criar pasta, confira o nome.

**Copias do projeto em outros lugares.** Ja existiram copias em
`~/Dashboard-Comercial-Cr-Lima/` e dentro desta propria pasta, cada uma com
historico git proprio, publicando no mesmo repositorio. Isso custou uma noite
de diagnostico. Estao arquivadas como `_ARQUIVADO_*`. Nao crie novas: edite
sempre aqui.

**A copia no Google Drive nao e backup atual.** O Drive tem um `index.html`
e um `.git` antigos, subidos manualmente. O Drive para Desktop NAO esta
instalado, entao nada ali sincroniza sozinho. Trate o Drive como arquivo de
dados de origem (os xlsx), nao como backup do codigo.

**Rota legada.** O caminho antigo (`atualizar_dashboard.sh`,
`importar_dados.py`, `PLANILHA COMERCIAL 2026.xlsx`) foi aposentado quando a
captura migrou para as subpastas do Drive. Esta em
`_backups/rota_legada_planilha_comercial/`. A planilha parou em 27/06/2026 —
se rodar aquele caminho, o dashboard volta no tempo.

**`data/data.json` esta orfao.** O `index.html` nao le esse arquivo. Parou
em 28/06/2026. Mantido apenas por precaucao.
