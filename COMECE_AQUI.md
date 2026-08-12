# COMECE POR AQUI — retomada em chat novo

Última sessão: 12/08/2026, ~17h50.

## O que fazer AGORA

**Nada urgente em aberto.** A fila de tarefas técnicas foi zerada em 12/08.
O que resta depende do Cristiano:

- **Canal do cliente:** ele vai preencher a coluna CANAL em
  `_saida/Base_Clientes_Canal.xlsx` (543 clientes, lista suspensa com
  alimentar / farma / indireto). Quando devolver, montar a análise por canal.

- **Conferir a divergência de junho no financeiro.** A planilha
  `FINANCEIRO/CONTROLE DE CUSTO E CONTROLE DE RECEITAS 26.xlsx` tem DUAS
  fontes de receita que não fecham entre si em junho: a soma das empresas dá
  R$ 370.791,55 e o bloco RESUMO dá R$ 369.568,23 (dif R$ 1.223,32). O
  coletor adota a SOMA DAS EMPRESAS, que reconcilia com a abertura por
  empresa da tela, e avisa sempre que discordarem. A causa provável é uma
  fórmula do RESUMO com intervalo desatualizado — vale o Cristiano olhar,
  porque tende a se repetir nos próximos meses.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:
1. `CONTEXTO.md` — arquitetura, regras de negócio, armadilhas, pendências
2. `COMO_FUNCIONA.md` — manual da operação (onde salvar arquivo, o que checa)

E respeite estas regras de trabalho, que vieram de erros reais:

1. **`python3 validar_js.py` antes de publicar.** O JS está todo num arquivo;
   erro de sintaxe deixa o site EM BRANCO. Já aconteceu.
2. **Scripts longos em segundo plano** (`nohup ... &` + `sleep` + `tail`). A
   conexão cai depois de ~4 min.
3. **Conferir DEPOIS de gravar, não só antes.** Uma gravação já apagou 42
   meses congelados e só apareceu na conferência posterior.
4. **Verificar se a substituição de texto realmente aconteceu.** Já contei a
   definição de uma função como se fosse a chamada e publiquei código morto.
   Conferir com `grep -c` esperando o número certo de ocorrências.
5. **`publicar.sh` versiona SÓ o index.html.** Mudou um `.py`? Commitar à
   mão depois, senão a mudança fica sem versionamento. Aconteceu duas vezes
   em 12/08.
6. **Ler o arquivo real antes de supor o formato.** Cada cliente tem um
   layout diferente e eles mudam sem aviso.

## Estado do sistema

Tudo publicado e no ar. **11 categorias** no ciclo automático, rotina às 18h.
Julho fechado em R$ 11.004.891,35, batendo entre faturamento, vendedores e
comissões.
