# CONTEXTO DO PROJETO — leia isto primeiro

**Para o Claude:** este arquivo existe para você retomar o trabalho num chat
novo sem precisar redescobrir nada. Leia-o inteiro antes de mexer em qualquer
coisa. Depois leia `COMO_FUNCIONA.md` (manual da operação) e, se precisar de
detalhe histórico, `ROTEIRO_AUTOMACAO.md`.

Última atualização: 11/08/2026.

---

## O que é

Dashboard comercial da **Cr Lima Comércio e Representações**, empresa de
representação que vende para redes de farmácia e supermercado no Sul do país.
O Cristiano é o dono e também atende os maiores clientes.

- **Pasta:** `/Users/cristianoalmeida/Desktop/Projeto Comercial IA/`
- **Site:** https://calmeida50.github.io/Dashboard-Comercial-Cr-Lima/
- **Repositório:** `git@github.com:Calmeida50/Dashboard-Comercial-Cr-Lima.git`
- **Arquitetura:** um `index.html` de ~4 MB com os dados embutidos em
  `DADOS_EMBEDDED` (e `DADOS_PANVEL` separado). Coletores em Python leem o
  Google Drive e reescrevem esses blocos.

---

## Como trabalhar aqui (importante)

1. **Sempre rodar `python3 validar_js.py` antes de publicar.** O JS está todo
   num arquivo só; um erro de sintaxe deixa o site EM BRANCO. Já aconteceu.
   O `publicar.sh` já chama isso, mas confira.

2. **Scripts longos: rodar em segundo plano com `nohup ... &` e depois
   `sleep` + `tail`.** A conexão do Desktop Commander cai em execuções que
   passam de ~4 minutos. Aconteceu várias vezes.

3. **Nunca gravar sem simular antes.** Quase todo coletor aceita `--simular`.

4. **Conferir DEPOIS de gravar, não só antes.** Em 09/08 uma gravação apagou
   42 meses congelados e eu só descobri porque conferi depois.

5. **Ler o arquivo real antes de supor o formato.** Cada cliente tem um layout
   diferente, e eles mudam de um mês para o outro sem aviso.

---

## Estado atual (11/08/2026)

Tudo publicado e funcionando. **10 categorias no ciclo automático:**

```
faturamento     -> atualizar_faturamento.py + atualizar_vendedores.py
                   + atualizar_comissoes.py      (nesta ordem!)
sellout_sj      -> atualizar_sellout.py          (São João)
sellout_dt      -> atualizar_dartora.py
sellout_nt      -> atualizar_nilo.py
sellout_imec    -> conferir_imec.py
sellout_aqua    -> atualizar_unidasul_aquafast.py
sellout_renner  -> atualizar_renner.py           (SEMANAL)
sellout_pv      -> atualizar_panvel.py + atualizar_panvel_lojas.py
estoque         -> atualizar_estoque.py          (São João)
estoque_pv      -> atualizar_estoque_panvel.py
```

Rotina às 18h pelo launchd (`rotina_diaria.sh`). Julho fechado em
**R$ 11.004.891,35**, batendo ao centavo entre faturamento, vendedores e
comissões.

---

## Regras de negócio (não são óbvias — vieram do Cristiano)

- **VAREJO = soma de todos os vendedores MENOS o Cristiano.** Não é pessoa, é
  total derivado. Cristiano atende os clientes ponderados; Edimar responde
  pelo varejo (supervisiona e também atende). Somar VAREJO junto com as
  pessoas conta em dobro.
- **O mesmo cliente muda de vendedor conforme a EMPRESA.** IMEC é do Cristiano
  na Ever Green e do Matheus na Kisabor. Nunca atribuir só pelo nome.
- **Prudence: BRAIR e DIMED têm DOIS vendedores** (Cristiano e Grazi), cada um
  com uma linha de produtos. Por isso o Cristiano preenche a coluna `Vendedor`
  no relatório da Prudence a partir de julho/2026. É a única empresa assim.
- **`Representante` NÃO é vendedor.** Na Belliz, Fiat Lux e Kisabor essa coluna
  traz a própria CR LIMA. Usá-la criaria um vendedor fantasma.
- **Comissão:** 5% Granado/Prudence/Belliz/Kisabor/Payot/Depimiel,
  3% Ever Green/Fiat Lux, 1,5% Aquafast, 0% Cless/Botânica.
  Rateio: 100% Cristiano e Edimar, 60% os demais.
- **DIMED = PANVEL** (mesmo cliente). **SGM = DARTORA.**
- **WMS e WMB entraram no Atacadão** (Edimar), desde jan/2025.
- **Renner:** 80 lojas oficiais para estoque e ruptura; as outras ~22
  receberam produto por engano — contam no faturamento, não na cobrança de
  abastecimento. Loja 88 nunca recebeu produto. 4 itens saem de loja física e
  ficam só no e-commerce (fora do cálculo de ruptura).

---

## Cortes de período (CRÍTICO)

`corte.py` centraliza. **Nada anterior a junho/2026 é reprocessado.**

Motivo: até maio o acompanhamento vinha da **Planilha 2026** (controle do
Cristiano em Excel), os números estão validados, e o Drive só tem 5 das 10
empresas nesse período — recalcular produziria valor MENOR que o real.

**Comissões têm corte próprio, um mês adiante:** recalculam só de **julho**,
porque junho já foi pago. Comissão paga não se recalcula.

Exceção: a **Ever Green** tem relatório desde jan/2025 e poderia ser
reconstruída, mas segue congelada junto com o resto por consistência.

---

## Armadilhas já encontradas (não repetir)

- **Valor fixo no código que era verdade quando foi escrito.** Apareceu umas
  seis vezes: `has2025 = emp === 'GRANADO'`, `Math.min(mes+1, 6)` no ranking
  de clientes, seletor de mês parando em junho, `_pvEmpList` fixo, rótulos
  "Jan a Jun". **Se algo não acompanha uma troca de seleção, procure por lista
  ou condição fixa.**
- **Inserir HTML procurando `</body>`:** existem DUAS ocorrências, e a primeira
  está dentro de uma string no JS. Usar `rfind`.
- **Coluna de PESO lida como valor:** 'Peso Líquido Kisabor' casava com
  "LIQUIDO" (prioridade máxima) e março da Kisabor virava R$ 12.502 em vez de
  R$ 97.634. VETO já cobre PESO, KG, CX FD, CAIXA, VOLUME, CUBAGEM.
- **Linhas de estatística do Excel** ('Sum', 'Average', 'TOTAL GERAL:') sendo
  lidas como cliente.
- **Cabeçalho fora da linha 0:** a Kisabor traz um bloco de filtros no topo;
  o cabeçalho real está na linha 9. `achar_cabecalho` procura até a linha 16.
- **Nome de arquivo sem a empresa:** `ESTOQUE SAO JOAO JULHO 26.xlsx` deixou a
  Payot parada um mês. O coletor agora descobre pela descrição dos produtos.
- **PDF não é lido.** Kisabor e Depimiel ficaram fora de junho até virarem
  Excel.
- **Drive recusa leitura** (`Resource deadlock avoided`) — havia sido tratado
  como sucesso e o dado sumia em silêncio. Agora é falha e tenta de novo.
- **Script DTV7** varre TODOS os botões da página e esconde os que têm nome de
  marca. Exceção por prefixo de id: `dt-v7-`, `imec-emp-`, `uni-emp-`, `pv-`.
  Botão novo com nome de marca precisa de prefixo listado ali.

---

## Pendências

1. **Renner: separar perfume de linha antiga** na evolução mensal. Em 2025 não
   havia perfume na Renner, então o comparativo mistura duas operações — valor
   sobe 352% e unidade cai 36% no mesmo mês. O Cristiano já aprovou separar.
2. **Percentuais distorcidos** em produtos que quase não venderam em 2025
   (ex: +51.636%). Tratar como "novo" em vez de mostrar o percentual.
3. **Comissões jan–mai:** a fórmula atual não reproduz o que foi pago
   (diferenças de até R$ 1,4 mi, variando de sinal). Como está tudo pago e
   congelado, não é urgente — mas a causa nunca foi entendida.
4. **Semana 28 da Renner** veio com 21 colunas em vez de 22 (faltou
   'Sales Value'). O leitor tolera, mas vale pedir de novo.
5. **Estoque da Dartora e Nilo Tozzo** não estão no ciclo (clientes enviam
   mensalmente, não semanalmente).

---

## Como o Cristiano trabalha

- Ele confere os números e **encontra inconsistências reais** — várias das
  correções mais importantes vieram de observações dele ("não pode ter dado
  tanta diferença em valor e em unidades ter ficado negativo").
- Prefere resolver na origem quando possível (marcar o vendedor no relatório
  em vez de criar exceção no código).
- Salva os arquivos no Drive ao longo do dia e espera a rotina pegar.
- Quando ele diz "de junho para trás", inclui junho. Confirmar sempre que a
  fronteira importar.

---

## Mês Corrente: pedidos, não faturamento (11/08/2026)

A tela **Mês Corrente** mostra os **pedidos captados** — o que as secretárias
digitam na planilha de pedidos diários no Drive. **Nunca** o faturamento.

Motivo (Cristiano): serve para acompanhar o que foi captado no mês, mesmo que
na hora de faturar o pedido não seja atendido 100%. São duas informações
diferentes e não devem ser misturadas.

**O bug que existia:** o código somava as duas fontes
(`realMesBase + LIVE_PEDIDOS.totalGeral`). Enquanto o mês não tinha
faturamento só apareciam os pedidos; quando o faturamento entrava, o valor
DOBRAVA. Julho apareceu com R$ 20,7 milhões contra R$ 11,0 milhões reais.

Fonte: `LIVE_PEDIDOS_MULTI[mesIdx]`, que tem todos os meses. Mês sem pedidos
digitados cai no faturamento, para não zerar histórico antigo.

Todas as **outras** telas seguem usando faturamento normalmente.

---

## Positivação no YTD por vendedor (12/08/2026)

Cada empresa, na abertura do YTD por vendedor, traz a linha **Positivação**:
quantos clientes da carteira compraram naquele mês e o percentual.

**Critério da carteira (confirmado pelo Cristiano):** clientes que compraram
em **2026 OU 2025**. Inclui os que estão parados este ano — que são justamente
os que precisam ser trabalhados. A alternativa (contar só quem comprou em
2026) daria um percentual mais alto e esconderia essa oportunidade.

Exemplo: CESAR / BELLIZ tem 53 clientes na carteira; 17 positivados em janeiro
= 32%. Contando só quem comprou em 2026 seriam 44 clientes e 38,6%.

Semáforo: verde ≥60%, laranja ≥35%, vermelho abaixo.
A coluna Total mostra quantos clientes distintos compraram no ano.

Vale também na exportação para Excel, onde os clientes saem agrupados
(recolhidos, com o +/- na lateral) reproduzindo o expandir da tela.

---

## O que foi feito em 12/08/2026

- **YTD por vendedor** ganhou abertura por EMPRESA com as mesmas 5 linhas da
  visão geral (Hist. 2025, Obj. 2026, Realizado, % Real/Obj., Cresc. vs 2025),
  mais a linha de **Positivação**. Clicando na empresa, expande os CLIENTES
  com realizado mês a mês, total 2026, total 2025 e variação em colunas
  próprias. Botão de **Excel** exporta tudo no mesmo layout, com os clientes
  agrupados (o Excel mostra o +/- na lateral).
- **Mês Corrente**: nova coluna **Tendência** (projeção de fechamento) e
  **% Tend.** (quanto isso representa do objetivo), logo após o Realizado.
  Cálculo por DIAS ÚTEIS: `realizado / dias úteis decorridos × dias úteis do
  mês`. Dias corridos distorceriam, porque pedido não entra no fim de semana.
  Mês fechado mostra "—". Como a tela lê os pedidos digitados, a tendência se
  atualiza todo dia.
- **Cobertura da São João** ganhou 3 colunas: Venda 2025, Venda 2026 e 26x25.
- **`gerar_base_clientes.py`**: gera `_saida/Base_Clientes_Canal.xlsx` com 543
  clientes (413 ativos em 2026, 130 que só compraram em 2025), vendedor,
  empresas, venda dos dois anos e coluna CANAL em branco com lista suspensa
  (alimentar / farma / indireto) + aba de resumo automática.
  **PENDENTE:** o Cristiano vai classificar o canal; depois disso dá para
  montar a análise por canal no dashboard.

### Aprendizados de método (12/08)

- **Sempre `python3 validar_js.py` antes de publicar.** Já está dentro do
  `publicar.sh`.
- **Verificar se a substituição realmente aconteceu.** Contei a definição de
  uma função como se fosse a chamada e publiquei código que nunca rodava.
  Conferir com `grep -c` esperando o número certo de ocorrências.
- **Cache do navegador engana.** Depois de publicar, esperar 1–2 min e usar
  Cmd+Shift+R. Se persistir, abrir com `?v=2` na URL.
- **`publicar.sh` diz "Nada a publicar"** quando o commit já foi feito antes
  dele — é normal, o `git push` seguinte é que publica.

---

## Pendências zeradas em 12/08/2026

1. **Renner: perfume separado da linha antiga.** O bloco `sellout_renner`
   agora grava três séries: `meses`, `meses_perfume` e `meses_linha_antiga`.
   A virada do mês é detectada sempre pela série completa — filtrando, alguma
   semana fica com MTD zero no recorte e a contagem desalinha.
   Conferido: as 3 séries com 8 meses e perfume + linha antiga = total.
   **FALTA:** mostrar as duas séries na TELA da Renner (hoje só o dado está
   gravado; a tela ainda exibe o total).

2. **Percentual distorcido.** `varPct(v26, v25, minBase)` devolve "novo" (roxo)
   quando a base de 2025 é menor que R$ 500. Aplicado na tabela de produtos da
   Panvel. **FALTA:** aplicar nas demais telas que mostram variação por
   produto (São João, Dartora, Nilo, IMEC).

3. **Canal do cliente** — depende do Cristiano preencher a coluna CANAL em
   `_saida/Base_Clientes_Canal.xlsx` (543 clientes). Depois disso dá para
   montar a análise por canal no dashboard.

### Atualização das pendências — fim do dia 12/08

1. **Renner: perfume × linha antiga — CONCLUÍDO.** Dado gravado em três séries
   E exibido na tela (aba Resumo tem 3 tabelas: Perfume, Linha antiga, Total).
2. **Percentual distorcido — CONCLUÍDO.** Base mínima de R$ 500 nos 4 pontos
   que calculam variação por produto; abaixo disso mostra "novo" em roxo.
3. **Canal do cliente — PENDENTE**, aguardando o Cristiano preencher a coluna
   CANAL em `_saida/Base_Clientes_Canal.xlsx`. Depois disso: montar a análise
   por canal (alimentar / farma / indireto) no dashboard.

---

## Sessão de 12/08/2026 — tarde

### Aba Cobertura da São João (Sell Out → São João → Cobertura)

Ganhou, nesta ordem: **Produto · Sell out 2025 · Sell out 2026 · 26x25 ·
Lojas com estoque (data) · Lojas no mês · Mês anterior · Δ mês · Mesmo mês
2025 · Δ ano**, mais linha de TOTAL. O Excel da aba saiu igual.

Não precisou de coletor: `val_2026`/`val_2025` já existiam por produto e por
mês para praticamente todos os SKUs. A variação usa o `varPct` com base mínima
de R$ 500 — abaixo disso mostra "novo" em roxo.

A coluna de estoque vem de `estoque_sao_joao[emp].produtos[].lojas` (lojas com
estoque > 0), casada pelo NOME do produto. Casou 100% nas seis empresas nas
linhas que aparecem na tela. Itens com **zero lojas com estoque** saem em
vermelho — ruptura total na rede.

### Bloco "Cobertura de Lojas — Top 5 SKUs" REMOVIDO

Ficava no fim da tela de Sell Out e perdeu a função para a aba Cobertura.
Saíram o card, o modal de lojas sem venda e ~206 linhas de JS
(`renderCoberturaSkus`, `selecionarCoberturaMes`, `abrirModalCobertura`,
`MESES_COB` e as do modal).

**Consequência importante:** `cobertura_mensal` não é mais usado em tela
nenhuma. A tarefa "recalcular a cobertura no `atualizar_sellout.py`", que era
a próxima da fila, DEIXOU DE EXISTIR. Se aparecer em anotação antiga, ignore.

### Data de atualização do estoque, por cliente

Antes os coletores gravavam só `periodo` = último dia do mês da pasta, e a tela
mostrava "31/07" mesmo para arquivo salvo em 05/08. Agora
`atualizar_estoque.py` e `atualizar_estoque_panvel.py` gravam **`atualizado_em`
com a data real do arquivo, por empresa**, mais o nome do arquivo.

Na tela, uma função só (`dataEstoque`) alimenta três pontos: badge do estoque
São João, badge da Panvel e o cabeçalho da coluna de estoque na Cobertura.
Cai no `periodo` como reserva se faltar a data. Empresa sem arquivo novo
conserva a data dela, não herda a de quem mandou.

Isso cobre ritmos diferentes: São João e Panvel semanais, outros mensais. O
`sincronizar.py` assina cada pasta por nome + tamanho + data de modificação,
então regravar o MESMO nome de arquivo já dispara o coletor.

Ressalva: a data vem do arquivo no Drive, não de dentro da planilha (o layout
de estoque não tem data). Se o Drive reescrever o arquivo numa
ressincronização, a data pode andar sem o dado ter mudado.

### Somatório no modal de produtos do Sell Out

Clicando na empresa no Consolidado (aba Acumulado), o modal agora fecha com uma
linha TOTAL: nº de SKUs, val 2026, qtd 2026, val 2025, qtd 2025 e variação.
Confere com os cards do topo — as seis empresas somam R$ 40.364.623,88.

### Receita Líquida e Financeiro entraram no ciclo — 11ª categoria

**Antes não tinham atualização automática nenhuma:** nem coletor, nem categoria
no `sincronizar.py`. Os três blocos eram carregados à mão e estavam parados em
junho desde 11/07.

Criado o **`atualizar_financeiro.py`**, que lê
`FINANCEIRO/CONTROLE DE CUSTO E CONTROLE DE RECEITAS 26.xlsx` e escreve
`receitas_empresa_mensal`, `financeiro` e `receita_liquida`.

Layout da planilha: aba `RECEITAS 2026` com matriz mês × empresa, coluna TOTAL
e um bloco RESUMO abaixo; aba `CONTROLE DE CUSTOS 2026` com blocos de 3 colunas
por mês (rótulo | VALOR | %), seis por faixa, em duas faixas (jan-jun, jul-dez)
— interessa a linha TOTAL.

Decisões do coletor:
- **PRESERVA as colunas de 2025** (`jur25`/`rec25`/`liq25`). A planilha é só de
  2026; recalcular zeraria o comparativo.
- **Trava de conferência:** reprocessa jan–mai e compara com o publicado; se
  divergir mais de R$ 0,01, aborta sem gravar. Rodou limpo.
- **Junho mudou:** a planilha tem duas fontes de receita que não fecham — soma
  das empresas R$ 370.791,55 contra RESUMO R$ 369.568,23 (dif R$ 1.223,32). O
  dashboard usava o RESUMO. Adotada a SOMA DAS EMPRESAS, que reconcilia com a
  abertura por empresa da tela. Líquido de junho: R$ 128.343,87 → R$ 129.567,19.
  O coletor avisa toda vez que as duas fontes discordarem.

Nota: a planilha de **pedidos diários** funciona por outro caminho — o
navegador busca o Google Sheets ao vivo via `gviz` (`MASTER_DATA_SHEET_ID`),
sem coletor e sem passar pela rotina das 18h. É a única tela assim.

### Aprendizado de método

`publicar.sh` versiona **só o index.html**. Mudança em `.py` precisa de commit
à mão depois — passou batido duas vezes nesta sessão.


## Sessão de 13/08/2026 — dia inteiro

Estado no fim do dia: tudo publicado e versionado. **13 categorias** no ciclo.

### Lady Diu — 12º cliente de Sell Out (só quantidade)

`atualizar_sellout_ladydiu.py` lê UMA planilha mestre em
`SELL OUT PRINCIPAIS CLIENTES/SELL OUT LADYDIU 2025 E 2026 /`, com abas 2026 e
2025, 9 produtos, meses nas colunas. Trava: a coluna TOTAL é conferida contra a
soma dos meses, produto a produto; divergiu, aborta.

**Único cliente sem valor** — só unidades. Fica FORA de todo totalizador em R$
(card de total, consolidado por empresa, ranking de lojas).

**Armadilha evitada:** comparar o ano inteiro de 2025 (12 meses) com 2026 (7)
mostrava queda de 50% que era só diferença de período. O campo
`tot25_periodo` restringe 2025 aos MESMOS meses que 2026 tem. `tot25` (ano
cheio) fica guardado para quando dezembro chegar.

Decisão: planilha mestre única em vez de arquivo por mês. São 9 números por
mês; manter os nomes de produto sob controle do Cristiano elimina o risco de o
cliente mandar "SILVERFLEX 380 AG" num mês e "Silverflex Cu 380 Ag" no outro.

### BUG GRAVE corrigido: `p.val26` órfão em 3 telas

`(p.val26 || 0)` dentro de laços cuja variável era `c`, `v` ou `r`. Lançava
ReferenceError e o `try/catch` engolia num `console.warn` — a seção sumia SEM
AVISO. Atingia **11 dos 12 vendedores** na abertura por empresa do YTD (só
disparava quando havia cliente sem venda em 2025). Também estava no Ranking por
Empresa, no Ranking por Vendedor e nos cartões da Renner.

O catch agora MOSTRA uma tarja vermelha com a mensagem. Sumir calado é pior do
que aparecer quebrado.

### Lacuna de mix no Ranking de Clientes

Seletor "Quem não compra:" + empresa. Dois blocos separados:
**PAROU** (comprava em 2025, zerou em 2026) e **NUNCA COMPROU** (ordenado pelo
tamanho do cliente). Respeita o filtro de vendedor. Excel com a lista completa.

Por que separado: dos 407 clientes ativos, **290 compram UMA só empresa** — uma
lista crua de "não compra X" traria 300 nomes inúteis. O bloco PAROU tem 42
casos no total, com nome e sobrenome. Maior achado: **Nilo Tozzo comprava
R$ 395.591 de Cless em 2025 e zerou**.

### avg3m: a média de 3 meses estava CONGELADA (São João e Panvel)

Mesma doença do `cobertura_mensal`: nenhum script calculava, os três que citavam
o campo apenas preservavam. Estava parada em abr–jun.

Agora `atualizar_sellout.py` (São João) e `atualizar_panvel.py` calculam a cada
rodada, com os **3 últimos meses FECHADOS**. O mês corrente fica de fora por
regra explícita — mês parcial derrubaria a média e a cobertura pareceria melhor
do que é.

Critério da Panvel definido pelo Cristiano: **loja + site somados**. O estoque
fica na loja e abastece também a venda do site; dividir por só uma parte
inflaria a cobertura.

Não foi possível reproduzir o valor antigo (10.310 para o Sab Enxofre) por conta
nenhuma — veio de um critério que não existe mais no projeto. O novo é
auditável: (9.749+10.204+10.436)/3 = 10.129,7.

### Distribuição por loja da Panvel: era VENDA com rótulo de ESTOQUE

O botão dizia "quantas lojas têm 0,1,2,3,4+ unidades **em estoque**", mas o dado
vinha do arquivo de VENDA por loja, em faixas de quantidade VENDIDA (0, 1-5,
6-20, 21-50, +50). A data "22/07/2026" estava escrita fixa no código.

Agora `atualizar_estoque_panvel.py` calcula `dist_estoque` de verdade, do
arquivo de estoque (`Qtd Est Loja` por filial). A diferença é grande: num item,
a tela dizia 8 lojas com 4+ unidades; são **604 de 655**.

### Parâmetros da Panvel — 13ª categoria

`atualizar_parametros_panvel.py` lê `SELL OUT PRINCIPAIS CLIENTES/PARAMETROS
PANVEL/`:
- `CLUSTER PANVEL <EMPRESA> ATUALIZADO.xlsx` → `lojas_liberadas` (filiais
  distintas por item). Granado 149 SKUs, Prudence 22, Cless 12.
- `MIX PANVEL COM FAMILIA E CATEGORIA.xlsx` → família e categoria na NOSSA
  nomenclatura. **O relatório de sell out traz família/categoria próprias, com
  outra nomenclatura — por decisão do Cristiano, valem sempre as da planilha.**

Mix SEM empresa no nome vale para todas (o arquivo perdeu o "GRANADO" no nome
em 13/08 e o coletor deixou de achá-lo).

O coletor AVISA quando o mesmo código aparece com família/categoria divergente.
Foram 11 casos, corrigidos pelo Cristiano no mesmo dia. Cada código aparece em
2 linhas na planilha: a correção precisa ser feita nas duas.

### Modal do mês da Panvel — colunas novas

Ordem final: **Família · Categoria · Código · Produto · Mix · Venda 2025 ·
Venda 2026 · Var. % · Qtd · Lojas liberadas · Lojas com estoque · Lojas que
venderam**. A variação em R$ saiu.

- **Mix ATIVO/INATIVO**: quem está no cluster é ativo. Inativo ainda aparece
  vendendo estoque residual — são <1% da venda, quase todos KITs (que podem ser
  falso inativo: talvez a Panvel controle kits fora do cluster).
- **Lojas com estoque em vermelho** quando abaixo de 90% das liberadas.
- **Lojas que venderam**: só o MÊS CORRENTE, por decisão do Cristiano. Vem do
  arquivo por loja mais recente (`lojas_mes`).

### Classificação de arquivo por CONTEÚDO, não por nome

Em 13/08 a Panvel passou a exportar DOIS arquivos por empresa:
```
SELL OUT PANVEL GRANADO AGOSTO 26 ( 12.08 ).xlsx          -> POR LOJA
SELL OUT PANVEL GRANADO PRODUTO AGOSTO 26 ( 12.08 ).xlsx  -> consolidado
```
O nome curto, que em julho era o consolidado, virou o por loja. Decidir pelo
nome erraria um dos meses. Regra: tem `Filial Loja` → por loja; tem
`Venda Efetiva Ano Anterior` → consolidado.

Cada um tem o que o outro não tem: o consolidado traz o **comparativo com
2025**; o por loja traz as **filiais**. Por isso os dois precisam ser salvos.

**Isso destravou o ranking de lojas**, parado desde junho: a conferência
comparava o arquivo por loja (só loja física) com o total publicado (incluindo
site). Com o arquivo certo, julho fecha em 0,00 nas três empresas.

### Mês parcial

`atualizar_panvel.py` marca `parcial: True` e `ate` no mês corrente. A data sai
do NOME do arquivo — "( 12.08 )" — e cai na data de gravação se não houver.
Selo âmbar "◑ PARCIAL até 12/08" na tabela, no gráfico e no título do modal.

O **percentual continua válido** em mês parcial: o relatório da Panvel traz o
mesmo período nos dois anos (01-12/08 contra 01-12/08). O que não pode é ler o
valor absoluto como mês fechado.

### Ritmo de gravação combinado com o Cristiano

| o quê | quando |
|---|---|
| Estoque Panvel e São João | semanal |
| Sell out Panvel (os DOIS arquivos) | semanal |
| Sell out São João | 1x por mês, no início do mês seguinte |

Por isso a São João nunca cai como "parcial" — o mês dela já fechou quando é
salvo.

### Bugs de bastidor corrigidos

1. **Empresas fantasma**: o novo padrão de nome com data "( 12.08 )" fez o
   coletor de estoque criar "CLESS ( 12.08 )" como empresa. Ele só limpava
   parênteses com números inteiros, tipo "(1)". Agora limpa qualquer conteúdo
   entre parênteses e datas soltas. As três fantasmas foram removidas do dado.
2. **`%` mal escapado derrubava o script no pior momento**: o print da trava de
   divergência em `atualizar_panvel_lojas.py` usava "0,1%" sem escapar,
   quebrando com ValueError justamente ao avisar de problema — e levando junto
   o coletor encadeado. Mesmo defeito do log de 09/08.
3. **Casamento por código**: o estoque procurava a média por NOME e a média era
   chaveada por CÓDIGO. A Cless ficava com média vazia. O código do item passou
   a ser lido do arquivo de origem em `conferir_panvel.py`.


## Sessão de 14/08/2026

### Categoria por item da São João — 14ª categoria do ciclo

`atualizar_parametros_sao_joao.py` lê `SELL OUT PRINCIPAIS CLIENTES/PARAMETRO
SAO JOAO/` e grava `PARAMS_SAO_JOAO`. O sell out da São João NÃO traz categoria
e NÃO tem código de item — o casamento é pelo **nome normalizado**.

**Dois layouts convivem, e o coletor aceita os dois:**

| arquivo | colunas | contém |
|---|---|---|
| `MIX BELLIZ SAO JOAO COM CATEGORIA.xlsx` | Categoria, Produto | só ativos (61) |
| `MIX GRANADO SAO JOAO COM CATEGORIA.xlsx` | Status, CATEGORIA, DESCRIÇAO | ativos e inativos (98) |

O layout da Granado é melhor: cobre 86 de 86 produtos do sell out. Na Belliz,
78 de 139 ficam sem categoria (são os inativos, com venda residual) — para
resolver, basta refazer a planilha dela no formato de três colunas.

**Onde aparece:** modal do Acumulado (clicando na empresa no Consolidado) e
modal Mensal (clicando no mês), sempre ANTES da descrição. Excel dos dois
acompanha.

**Item novo = uma linha na planilha.** Não precisa mexer em código.

### Mix ATIVO/INATIVO da São João agora sai da planilha

Havia DUPLICIDADE: a lista de ativos vivia escrita à mão no `index.html`
(`MIX_ATIVO_SAO_JOAO`) e também na planilha nova. `isSjAtivo()` passou a
preferir a planilha quando ela traz a coluna Status; sem Status, cai na lista
do código. O coletor confere as duas fontes a cada rodada e avisa se
divergirem — em 14/08 batiam exatamente (Granado 71, Belliz 61).

### Modal Mensal da São João

Saiu a variação em R$, entrou **variação % em quantidade** ao lado das
quantidades (mostra se o crescimento veio de volume ou de preço) e a coluna
**Lojas com estoque**, ao lado de Lojas com venda.

Vermelho quando há MENOS lojas com estoque do que lojas que venderam — sinal
clássico de ruptura. Ex.: Sab Enxofre Granado vendeu em 1.229 e tem estoque em
1.208.

Ressalva: o estoque é a FOTO mais recente, não o estoque daquele mês. A data
vai no subtítulo do modal.

### Modal do mês da Panvel — colunas finais

Acrescentadas **Estoque lojas (un)** e **Cobertura (dias)**.

    cobertura = estoque nas lojas / (qtd vendida / dias do periodo)

Os dias saem do dado: no mês parcial, da data no nome do arquivo ("( 12.08 )" →
12 dias); no mês fechado, os dias do mês. Ajusta sozinho a cada arquivo novo.
Vermelho abaixo de 15 dias, azul acima de 45.

**Essa cobertura DIVERGE da aba Estoque, e as duas estão certas:** a da aba usa
a média de 3 meses FECHADOS (ritmo normal); esta usa o giro do mês corrente
(ritmo de agora).

### BUG: Excel de comissões não baixava

`exportarComissaoVendedorModal()` usava `nome.toUpperCase()` onde a variável do
escopo é `vendedor`. ReferenceError → o clique no botão Excel não fazia NADA,
sem mensagem. Mesma família do `p.val26` de 13/08, e mesma origem: o comentário
`/* _fixCvModal */` na linha mostra que veio de um script de correção aplicado
por cima do arquivo (`fix_cv_modal.py` está na pasta do Drive).

Corrigido de quebra: o total de CV somava `c.cv` (zero quando o valor precisa
ser calculado), então a linha TOTAL vinha menor que a soma das linhas.

### Comissões passam a exibir CENTAVOS

O dado SEMPRE esteve certo — `comissoes_detalhe` grava com 2 casas. Era só a
exibição: `fmt()` usa `Math.round`. Trocado para `fmtFull()` em toda a tela de
Comissões (modal por cliente, resumo por vendedor, detalhe por empresa, cartões
e tabela de pagamento). 45 substituições.

**Comissão não pode arredondar** — arredondar muda o que se paga.

Corrigido junto: `fmtFull()` usava `Math.abs()` e engolia o sinal negativo. Um
saldo de −R$ 120,00 aparecia como R$ 120,00, com a cor vermelha como única
pista. Isso também afetava a tela Financeiro, que já usava a função.

### Padrão que se repete — vale como alerta

Três bugs em dois dias vieram do MESMO padrão: **script de correção aplicado
por cima do `index.html` deixando variável de outro escopo**. `p.val26` em três
telas (13/08) e `nome` no Excel de comissões (14/08). Todos silenciosos: o erro
ia para o console e a tela simplesmente não fazia nada.

Ao mexer em qualquer função, conferir se as variáveis citadas existem NAQUELE
escopo. E desconfiar de trechos marcados com comentários tipo `/* _fix... */`.
