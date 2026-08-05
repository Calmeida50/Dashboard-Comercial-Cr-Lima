# Roteiro — automacao da coleta (em construcao)

Anotado em 04/08/2026. Contexto passado pelo Cristiano para retomar depois.

## Principio geral

Os relatorios chegam **diferentes de cada empresa** — umas mandam xlsx, outras pdf,
e o layout varia. Isso NAO vai ser padronizado: a rotina precisa aceitar os
arquivos exatamente como as empresas enviam. Padronizar na origem geraria erro
de transcricao e trabalho manual; a inteligencia fica no parser, nao no usuario.

Layouts ja mapeados (faturamento, julho/2026):

| Empresa    | Coluna de valor            | Particularidade                          |
|------------|----------------------------|------------------------------------------|
| GRANADO    | VALOR TOTAL LIQUIDO REAL 2 | numerico; devolucoes vem negativas       |
| PRUDENCE   | Valor                      | texto "R$ 1.623,02"; coluna **Operacao** |
| BELLIZ     | Valor Venda                | traz representante e regional            |
| EVER GREEN | Valor Total da Nota        | data, NF, cliente, valor                 |

ATENCAO PRUDENCE: a coluna `Operacao` separa **Vendas** de **Bonificacao**.
Bonificacao nao e venda. O dashboard tem bloco proprio `prudence_bonificacao`.
Verificar se o atualizar_mes.py ja separa antes de automatizar.

## Comissoes — dois cenarios distintos

### Cenario 1 — comissao a receber (calculada)

Tela "Comissoes". Calcula o % de comissao de cada empresa para cada vendedor.

- Fonte do faturamento: pasta `FATURAMENTO DAS EMPRESAS`
- O % de comissao de cada empresa **ja esta definido**
- Comissao gerada = faturamento x % da empresa
- **Regra de rateio**: exceto CRISTIANO e EDIMAR, todos os demais vendedores
  recebem **60% da comissao gerada**

### Cenario 2 — comissao recebida (conferencia Ever Green)

Controle do que a Ever Green efetivamente paga, contra o que foi faturado.

- Faturamento lancado: janeiro/2025 a julho/2025
- Pasta `RELATORIOS DE COMISSAO`: os relatorios do que eles estao pagando
- **Cruzamento pelo numero da Nota Fiscal**: compara o que faturou com o que
  esta sendo pago, NF a NF

RISCO A VERIFICAR: dos 17 arquivos da pasta de comissao, 15 sao PDF.
Para cruzar por NF e preciso extrair texto do PDF. Se forem PDFs digitais,
funciona. Se forem digitalizacoes (imagem), exige OCR e a confiabilidade cai
muito — nesse caso o cruzamento automatico nao e recomendavel.

## Ordem de implementacao acordada

Por etapas, nunca tudo de uma vez. Rotina que abraca as 4 categorias de
primeira falha em silencio e o erro so aparece quando alguem questiona um numero.

1. **Faturamento** — parser ja maduro no atualizar_mes.py. Rotina diaria 18h,
   mes corrente, le direto do Drive, publica e notifica o que entrou e o que
   faltou. Rodar algumas semanas ate ganhar confianca.
2. **Sell out** — sao SEIS formatos (sao_joao, nilo_tozzo, dartora, imec,
   unidasul, zaffari), um bloco por cliente no DADOS_EMBEDDED. Um por vez.
3. **Estoque** — hoje so existe `estoque_sao_joao` no dashboard.
4. **Comissao** — por ultimo, por causa dos PDFs.

## Caminho do Drive (montado em 04/08/2026)

    ~/Library/CloudStorage/GoogleDrive-almeida.cristiano33@gmail.com/Meu Drive/PROJETO COMERCIAL IA

Subpastas: FATURAMENTO DAS EMPRESAS, SELL OUT PRINCIPAIS CLIENTES,
ESTOQUE DOS PRINCIPAIS CLIENTES, RELATORIOS DE COMISSAO.

## Nomenclatura: a rotina precisa ser tolerante

Exemplos reais colhidos em julho/2026 — um script rigido quebraria em metade:

- `FATURAMENTO EVERGREEN JULHO 26.xlsx` (junto) vs `EVER GREEN` no resto
- `FATURAMENTO FIAT LUX JULHO 26.docx` — **docx, nao planilha**
- `SELL OUT DARTORA CLESS JULHO 26 .xlsx` — espaco antes da extensao
- pasta `JULHO 26` no sell out, mas `JULHO` no estoque e faturamento
- pastas-mae com espaco no fim: `FATURAMENTO DAS EMPRESAS `, `RELATORIOS DE COMISSAO `

Casar por palavras-chave normalizadas (empresa + mes + ano), sem acento e sem
depender de espacos. Ao final, comparar o encontrado com a lista das 11
empresas e notificar o que faltou.

## Decisoes ja tomadas

- Publicacao: automatica ("publica sozinha sempre"), com notificacao no Mac
  quando algum cliente nao casar exatamente — avisa sem bloquear.
- Agendamento: uma vez por dia, 18h.
- Escopo: sempre o mes corrente.

---

## Percentuais de comissao por empresa (informado em 04/08/2026)

Sao os percentuais **totais pagos pelas empresas** sobre o faturamento.

| Empresa    | %     |
|------------|-------|
| GRANADO    | 5,0%  |
| PRUDENCE   | 5,0%  |
| BELLIZ     | 5,0%  |
| KISABOR    | 5,0%  |
| PAYOT      | 5,0%  |
| DEPIMIEL   | 5,0%  |
| EVER GREEN | 3,0%  |
| FIAT LUX   | 3,0%  |
| AQUAFAST   | 1,5%  |
| CLESS      | sem comissao |
| BOTANICA   | sem comissao |

CLESS e BOTANICA **nao pagam comissao para a equipe** (confirmado em 04/08/2026).
Ficam de fora de todo o calculo de comissao, mas **continuam nas demais analises**
— faturamento, ranking, participacao, YTD, sell out. Nao remover das outras telas.

Isso explica a ausencia da CLESS no bloco `comissoes_empresa`. A BOTANICA, porem,
ESTA nesse bloco — verificar ao implementar se e residuo de cadastro e deve sair.

### Rateio por vendedor

- CRISTIANO e EDIMAR: **100%** do valor
- Todos os demais vendedores: **60%** do valor

Ja esta codificado no index.html em tres pontos (linhas ~5180, ~12470, ~12560):
`F100 = ['CRISTIANO','EDIMAR']` -> fator 1; demais -> fator 0.6.
Confere com a regra informada.

Os percentuais por empresa, porem, NAO existem em lugar nenhum do codigo.
O bloco `comissoes_empresa` guarda faturamento mensal por empresa, nao a taxa.
Ao implementar o cenario 1, criar a tabela de taxas como constante unica e
referencia-la, em vez de espalhar numeros pelo codigo.

---

## Regras de extracao do faturamento (VALIDADAS contra o historico em 05/08/2026)

Cada regra abaixo foi testada somando o arquivo de junho/2026 e comparando com o
valor que ja estava no DADOS_EMBEDDED. Nao sao suposicoes.

### 1. Sempre o valor LIQUIDO

Quando o relatorio traz bruto e liquido, usar o **liquido**. Quando traz um valor
so, ele **ja e liquido** (confirmado pelo Cristiano em 05/08/2026).

Validacao: FIAT LUX junho/2026
- arquivo tinha coluna `VALOR LIQ`, soma = 499.893,30
- dashboard tinha 499.893,30 -> diferenca 0,00
- em julho o layout mudou para 59 colunas; o equivalente e `Valor total liquido`
  (nesse mes `Valor total bruto` da o mesmo numero, mas isso e coincidencia —
  fixar a regra no liquido, nao no que bate hoje)

### 2. Faturamento = somente VENDAS. Bonificacao vai para bloco proprio

Validacao: PRUDENCE junho/2026
- arquivo de junho NAO tinha coluna `Operacao` (so vendas), soma = 1.453.573,29
- dashboard tinha 1.453.573,29 -> diferenca 0,00
- em julho o arquivo passou a separar: Vendas 1.360.740,85 / Bonificacao 132.052,21
- bonificacao alimenta o bloco `prudence_bonificacao` (coluna BONIF. YTD do ranking)

Mesmo padrao na CLESS: junho sem coluna de tipo, soma 312.619,42 = dashboard.
Julho passou a ter `Tipo do pedido` com Venda/Bonificacao.

**Ao implementar**: se existir coluna de tipo/operacao com valores textuais
Venda/Bonificacao, filtrar somente venda. Se nao existir, somar tudo.

### 3. Codigos de operacao numericos = todos venda

A FIAT LUX traz `Operacao` com codigos (610201, 640301, 510202...). Nao sao
tipos de nota — **todas as notas sao venda** (confirmado pelo Cristiano).
Nao confundir com a coluna `Operacao` textual da Prudence.

### 4. Devolucoes vem negativas e devem ser somadas como estao

GRANADO julho: 219 linhas positivas, 37 negativas. A soma liquida (6.609.300,64)
e o faturamento correto. Nao filtrar negativos.

## Layouts por empresa (julho/2026)

| Empresa    | Cabecalho | Coluna de valor        | Observacao                        |
|------------|-----------|------------------------|-----------------------------------|
| GRANADO    | linha 1   | VALOR TOTAL LIQUIDO REAL 2 | devolucoes negativas          |
| PRUDENCE   | linha 1   | Valor                  | texto "R$ 1.623,02"; col Operacao |
| BELLIZ     | linha 1   | Valor Venda            | traz representante e regional     |
| EVER GREEN | linha 1   | Valor Total da Nota    |                                   |
| CLESS      | linha 1   | Valor do pedido        | col `Tipo do pedido` Venda/Bonif. |
| DEPIMIEL   | linha 1   | VALOR                  | texto "R$ 3 657,00" (espaco como  |
|            |           |                        | separador de milhar); NOTA com \t |
| FIAT LUX   | linha 2   | Valor total liquido    | 59 colunas, vazias intercaladas   |
| KISABOR    | ?         | ?                      | a mapear                          |
| PAYOT      | ?         | ?                      | a mapear                          |
| AQUAFAST   | ?         | ?                      | ainda nao enviado em julho        |
| BOTANICA   | ?         | ?                      | ainda nao enviado em julho        |

O layout MUDA de um mes para o outro na mesma empresa (FIAT LUX foi de 3 para 59
colunas entre junho e julho; PRUDENCE e CLESS ganharam coluna de tipo).
O parser precisa achar a coluna por palavra-chave a cada execucao, nunca por
posicao fixa nem por memoria do mes anterior.
