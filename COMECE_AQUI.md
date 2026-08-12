# COMECE POR AQUI — retomada em chat novo

Última sessão: 12/08/2026, ~14h30.

## O que fazer AGORA (primeira tarefa)

**Recalcular a cobertura da São João.** A aba Cobertura mostra só até junho e
apenas 5 produtos por empresa (de 86 na Granado, 139 na Belliz).

Causa: `atualizar_sellout.py` apenas PRESERVA `cobertura_mensal` — nunca
calcula. O dado veio de um carregamento antigo. O próprio comentário no topo
do arquivo admite isso: *"PRESERVA: cobertura_mensal (dentro de produtos)"*.

O conserto: calcular no coletor, a partir dos arquivos de sell out da São João,
que trazem venda **loja a loja**. Para cada SKU e cada mês:

```
qtd_venda = nº de lojas com venda > 0
qtd_zero  = nº de lojas da rede sem venda daquele SKU
lojas     = lista das lojas sem venda (o modal detalha)
```

Estrutura atual do campo:
```json
{"jan": {"qtd_zero": 26, "qtd_venda": 1231, "lojas": [...]}}
```

Respeitar o corte: só de junho em diante. Jan–mai fica como está.

Já pronto: as 3 colunas (Venda 2025, Venda 2026, 26x25) usam
`val_2026[mes]`/`val_2025[mes]`, que existem para TODOS os produtos e meses —
vão aparecer sozinhas quando a cobertura cobrir mais SKUs. `MESES_COB` já
lista os 12 meses.

## Depois disso

- **Canal do cliente:** o Cristiano vai preencher a coluna CANAL em
  `_saida/Base_Clientes_Canal.xlsx` (543 clientes, lista suspensa com
  alimentar / farma / indireto). Quando devolver, montar a análise por canal.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:
1. `CONTEXTO.md` — arquitetura, regras de negócio, armadilhas, pendências
2. `COMO_FUNCIONA.md` — manual da operação (onde salvar arquivo, o que checa)

E respeite estas quatro regras de trabalho, que vieram de erros reais:

1. **`python3 validar_js.py` antes de publicar.** O JS está todo num arquivo;
   erro de sintaxe deixa o site EM BRANCO. Já aconteceu.
2. **Scripts longos em segundo plano** (`nohup ... &` + `sleep` + `tail`). A
   conexão cai depois de ~4 min.
3. **Conferir DEPOIS de gravar, não só antes.** Uma gravação já apagou 42
   meses congelados e só apareceu na conferência posterior.
4. **Verificar se a substituição de texto realmente aconteceu.** Já contei a
   definição de uma função como se fosse a chamada e publiquei código morto.

## Estado do sistema

Tudo publicado e no ar. 10 categorias no ciclo automático, rotina às 18h.
Julho fechado em R$ 11.004.891,35, batendo entre faturamento, vendedores e
comissões.
