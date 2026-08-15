# COMO O DASHBOARD SE ATUALIZA — manual da operação

Atualizado em 11/08/2026.

Este documento responde a uma pergunta só: **o que acontece quando eu salvo
uma planilha nova no Drive?**

---

## 1. A resposta curta

Você salva o arquivo na pasta certa do Drive. Às 18h (ou quando o Mac liga, se
estava desligado) a rotina detecta a mudança, processa **apenas o que mudou**,
confere contra o histórico e publica.

Se algum número divergir do que já estava publicado, ela **para antes de
gravar** e não publica nada.

---

## 2. Onde salvar cada coisa

Tudo dentro de `Meu Drive/PROJETO COMERCIAL IA/`:

| O que | Pasta | Nome do arquivo |
|---|---|---|
| Faturamento | `FATURAMENTO DAS EMPRESAS/2026/<MÊS>/` | `FATURAMENTO <EMPRESA> <MÊS> 26.xlsx` |
| Sell out São João | `SELL OUT PRINCIPAIS CLIENTES/2026/<MÊS> 26/` | `SELL OUT SAO JOAO <EMPRESA> <MÊS> 26.xlsx` |
| Sell out Panvel | idem | `SELL OUT PANVEL <EMPRESA> <MÊS> 26.xlsx` |
| Sell out Dartora | idem | contém `DARTORA` no nome |
| Sell out Nilo Tozzo | idem | contém `NILO` |
| Sell out IMEC | idem | contém `IMEC` |
| Sell out Aquafast | idem | contém `AQUAFAST` |
| **Renner (semanal)** | pasta própria da Renner | `Semana <N> 2026.xlsx` |
| Estoque São João | `ESTOQUE DOS PRINCIPAIS CLIENTES/2026/<MÊS>/` | `ESTOQUE SAO JOAO <EMPRESA> <MÊS> 26.xlsx` |
| Estoque Panvel | idem | contém `PANVEL` |
| **Sell out Lady Diu** | `SELL OUT PRINCIPAIS CLIENTES/SELL OUT LADYDIU 2025 E 2026/` | planilha mestre única, com `LADY` e `DIU` no nome |
| **Parâmetros Panvel** | `SELL OUT PRINCIPAIS CLIENTES/PARAMETROS PANVEL/` | `CLUSTER PANVEL <EMPRESA> ATUALIZADO.xlsx` e `MIX PANVEL COM FAMILIA E CATEGORIA.xlsx` |
| **Parâmetros São João** | `SELL OUT PRINCIPAIS CLIENTES/PARAMETRO SAO JOAO/` | `MIX <EMPRESA> SAO JOAO COM CATEGORIA.xlsx` e a relação de lojas (`CNPJ - CLASSIFICAÇÃO LOJAS...`) |
| **Mix mínimo Granado** | `RELATORIO GRANADO/` | a dinâmica `CR LIMA COM E REPRESENTACOES.xlsx` + os dois `MIX MINIMO CANAL ...` + `CLIENTES SEM CANAL - GRANADO.xlsx` |
| **Financeiro / Receita Líquida** | `FINANCEIRO/` | `CONTROLE DE CUSTO E CONTROLE DE RECEITAS 26.xlsx` |

## Com que frequência salvar cada coisa

| o quê | quando | observação |
|---|---|---|
| Estoque Panvel e São João | **semanal** | a data que aparece na tela é a do arquivo, por empresa |
| Sell out Panvel | **semanal**, os DOIS arquivos | ver abaixo |
| Sell out São João | **1x por mês**, no início do mês seguinte | por isso nunca aparece como parcial |
| Financeiro | diário, conforme preenche | |
| Lady Diu | mensal, preenchendo a coluna do mês na planilha mestre | 9 números |
| Parâmetros Panvel | quando a Panvel mandar cluster novo (~2x/ano) | |
| Parâmetros São João | quando cadastrar item novo | uma linha na planilha, sem mexer em código |
| Dinâmica da Granado | quando quiser atualizar o mix mínimo | salve SEMPRE na mesma planilha, com tudo em "(Tudo)" |

**A Panvel precisa de DOIS arquivos por empresa, toda semana**, porque cada um
tem o que o outro não tem:

- o **por produto** traz o comparativo com 2025 (mesmo período nos dois anos)
- o **por loja** traz as filiais, que alimentam "lojas que venderam" e o
  ranking de lojas

Pode nomear como quiser: o coletor identifica pelo conteúdo, não pelo nome.
Se escrever a data no nome — `( 12.08 )` —, ela vira a data de corte do mês
parcial que aparece na tela.

**Mês corrente aparece com selo ◑ PARCIAL.** O percentual continua confiável
(o relatório compara o mesmo período nos dois anos); o que não vale é ler o
valor absoluto como mês fechado. Esse mês NÃO entra na média de 3 meses.

## A tela Mix Mínimo

Mostra o que falta cadastrar do mix mínimo da Granado nos clientes ativos dos
canais **farma** e **alimentar**.

Filtros: canal, **vendedor**, busca e "só quem tem item faltando". O filtro de
vendedor vale para a tela inteira e para o Excel — é o material da reunião
individual, e o nome dele entra no nome do arquivo.

Clicando num **cliente**, abre o que falta, agrupado por linha do mix.
Clicando num **item**, abre quem falta vender e o vendedor responsável.

Duas regras: só entram clientes **com compra em 2026**, e item que o cliente
compra fora do mix mínimo **não** aparece como problema.

**A dinâmica precisa ter Cliente e EAN como campos**, e ser salva com os
filtros em "(Tudo)" — o coletor lê o resultado, então enxerga só o que estiver
expandido na hora de salvar.


## A tela Apresentação

Duas faces da mesma análise:

- **Dashboard** — para você analisar. Tem cliente, empresa, período, navegação
  por linha › categoria › grupo, oportunidade e risco de ruptura.
- **Modo slide** (botão verde ▶ Apresentar) — tela cheia para a reunião.
  Navega com seta, espaço ou os botões; ESC sai.

**Duas regras importantes, combinadas em 15/08/2026:**

Dentro do modo slide **não existe troca de cliente** — se você está
apresentando para a São João, não pode haver um botão "Panvel" na tela. Para
trocar, saia da apresentação.

A tela nunca escreve "os itens que fazem 90% do faturamento", e sim **"Top SKUs
em faturamento"**. Dizer o percentual daria ao cliente o argumento de delistar
os demais.

O botão **⬇ Excel** exporta oportunidade e risco de ruptura em duas abas,
respeitando o recorte aberto — é o material para enviar ao cliente depois da
reunião.

**Atualiza sozinha.** A apresentação não guarda dado: tudo é calculado dos
mesmos blocos que os coletores gravam. Estoque novo no Drive, mês novo de sell
out ou mix novo já aparecem na próxima rodada das 18h.



**O nome importa.** É por ele que o sistema descobre a empresa e o mês.
Se faltar a empresa no nome, o coletor tenta descobrir pela descrição dos
produtos — mas isso é rede de segurança, não o caminho normal.

---

## 3. O que atualiza o quê

Quando o **FATURAMENTO** muda, rodam três scripts em sequência:

1. `atualizar_faturamento.py` — o total por empresa (Visão Geral, YTD)
2. `atualizar_vendedores.py` — clientes, vendedores, ranking de clientes
3. `atualizar_comissoes.py` — comissões

**A ordem importa:** a comissão é calculada sobre o que o passo 2 atribuiu.

As demais categorias são independentes: cada sell out e cada estoque tem seu
próprio coletor.

O **FINANCEIRO** roda o `atualizar_financeiro.py`, que alimenta as duas telas
de uma vez: Receita Líquida e Financeiro. É a mesma planilha para as duas.
Como você a preenche diariamente, ela é reprocessada no ciclo do mesmo dia.
Duas coisas a saber:

- As colunas de **2025 são preservadas** — a planilha é só de 2026.
- Se a soma das empresas não bater com o bloco RESUMO da própria planilha, o
  log avisa. Vale o total pela **soma das empresas**, que é o que reconcilia
  com a abertura por empresa da tela.

**Estoque: a data que aparece na tela** é a data em que o arquivo foi salvo no
Drive, por empresa — não o fim do mês. Cliente semanal e cliente mensal
convivem sem ajuste: cada um mostra a sua data. Regravar o arquivo com o mesmo
nome já conta como mudança e dispara o coletor.

---

## 4. As travas que impedem número errado no ar

### Trava de conferência
Todo coletor reprocessa um mês **já publicado e validado** antes de gravar.
Se o resultado não bater com o que está no ar, ele **aborta** e não grava nada.
Foi essa trava que impediu várias gravações erradas ao longo do projeto.

### Trava de corte (`corte.py`)
**Nada anterior a junho/2026 é reprocessado.** Até maio o acompanhamento vinha
da Planilha 2026, os números estão validados e o Drive nem tem todas as
empresas nesse período — recalcular produziria valor menor que o real.

Comissões têm corte próprio, **um mês adiante**: recalculam só de julho, porque
junho já foi pago.

### Trava de sintaxe (`validar_js.py`)
O `publicar.sh` recusa publicar se o JavaScript tiver erro. Como o código está
todo num arquivo só, um erro de sintaxe deixaria o site **em branco**.

### Falha de leitura do Drive
Se o Drive recusar a leitura (`Resource deadlock avoided`), a rotina trata como
**falha**, não avança o estado e tenta de novo no próximo ciclo. Antes ela
marcava como processado e o dado sumia em silêncio.

---

## 5. Quando a rotina roda

Agendada pelo launchd às **18h todo dia**. Se o Mac estiver desligado nesse
horário, ela roda assim que ligar.

Para rodar na hora, sem esperar:

```bash
cd "/Users/cristianoalmeida/Desktop/Projeto Comercial IA"
bash rotina_diaria.sh
```

Para só olhar o que mudou, sem processar nada:

```bash
python3 sincronizar.py --verificar
```

Para ver o que aconteceu no último ciclo:

```bash
tail -40 _backups/rotina_diaria.log
```

---

## 6. Quando algo não atualizar — o que checar, nesta ordem

1. **O arquivo está na pasta certa do mês certo?**
   Pasta de julho com arquivo de agosto não é encontrado.

2. **O nome tem a empresa e o mês?**
   `ESTOQUE SAO JOAO JULHO 26.xlsx` (sem a empresa) já causou a Payot ficar
   um mês parada.

3. **O arquivo é Excel, não PDF?**
   PDF não é lido. A Kisabor e a Depimiel ficaram fora de junho por isso.

4. **A rotina rodou?** `tail -40 _backups/rotina_diaria.log`

5. **Abortou por divergência?** O log diz qual empresa e qual mês.
   Isso é proteção funcionando, não defeito — investigar o arquivo.

6. **O deploy do GitHub passou?** Se o build falhar, o push acontece mas o
   site não atualiza. Chega e-mail de falha.

---

## 7. O que NÃO é automático

- **Comissões de janeiro a junho** — já pagas, congeladas de propósito.
- **Qualquer mês anterior a junho/2026** — congelado.
- **Empresa nova** que apareça no faturamento entra sozinha; mas se ela tiver
  regra própria (percentual de comissão, apelido de cliente), precisa ser
  registrada em `equivalencias.py`.
- **Cliente novo sem vendedor** aparece como não atribuído até ser cadastrado.

---

## 8. Regras de negócio que estão no código

Estas foram levantadas ao longo do projeto e não são óbvias:

- **VAREJO = soma de todos os vendedores MENOS o Cristiano.** Não é uma pessoa,
  é um total derivado. O Cristiano atende os clientes ponderados; o Edimar
  responde pelo varejo.
- **O mesmo cliente muda de vendedor conforme a empresa.** IMEC é do Cristiano
  na Ever Green e do Matheus na Kisabor.
- **Prudence: Brair e Dimed têm DOIS vendedores** (Cristiano e Grazi), cada um
  com uma linha de produtos. Por isso a coluna `Vendedor` é preenchida à mão
  no relatório — é a única fonte confiável nesse caso.
- **`Representante` NÃO é vendedor.** Nos relatórios da Belliz, Fiat Lux e
  Kisabor essa coluna traz a própria Cr Lima.
- **WMS e WMB entraram no Atacadão** (Edimar), desde janeiro/2025.
- **Comissão por empresa:** 5% (Granado, Prudence, Belliz, Kisabor, Payot,
  Depimiel), 3% (Ever Green, Fiat Lux), 1,5% (Aquafast), 0% (Cless, Botânica).
  Rateio: 100% para Cristiano e Edimar, 60% para os demais.
- **Renner:** 80 lojas oficiais para estoque e ruptura; as demais contam no
  faturamento mas não na cobrança de abastecimento. Os 4 itens que saem de
  loja física ficam fora do cálculo de ruptura.
