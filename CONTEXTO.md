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
