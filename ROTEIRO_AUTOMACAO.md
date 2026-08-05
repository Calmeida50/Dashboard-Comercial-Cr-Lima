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
| CLESS      | ???   |
| BOTANICA   | ???   |

PENDENTE: CLESS e BOTANICA nao foram informadas.
- CLESS tem faturamento (R$ 2,36 mi YTD 2026) mas nao aparece no bloco
  `comissoes_empresa` do DADOS_EMBEDDED. Verificar se e intencional.
- BOTANICA aparece em `comissoes_empresa` mas nao teve % informado.
  Faturamento irrisorio (R$ 2.735 YTD), pode ser residual.

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
