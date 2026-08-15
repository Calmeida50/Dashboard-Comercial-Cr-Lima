# COMECE POR AQUI — retomada em chat novo

Última sessão: 15/08/2026.

## O que fazer AGORA

**Nada urgente em aberto.** Tudo publicado, versionado e no ar.

Pendências que dependem do Cristiano:

- **Acesso da equipe — DECISÃO PENDENTE E A MAIS IMPORTANTE.** O repositório e
  o site estão PÚBLICOS desde 27/06: faturamento, comissões por vendedor,
  receitas, custos e base de clientes acessíveis a quem tiver o endereço.
  Assinar GitHub Pro/Team NÃO resolve (o Pages segue público; no Free, tornar o
  repo privado derruba o site). Caminho recomendado: Cloudflare Pages +
  Cloudflare Access (grátis até 50 usuários, login por PIN no e-mail). E para
  "travar telas por pessoa" não basta esconder menu — todo o dado está no
  index.html; é preciso gerar uma versão por perfil.
  **Ordem importa:** conectar o Cloudflare ANTES de fechar o GitHub, senão o
  site sai do ar.

- **Canal do cliente:** preencher a coluna CANAL em
  `_saida/Base_Clientes_Canal.xlsx` (543 clientes: alimentar / farma /
  indireto). Melhora também a lacuna de mix do Ranking de Clientes.

- **Cluster da São João**, se a rede fornecer. Hoje assume-se 100% da rede como
  alvo, o que é razoável mas menos preciso que o cluster da Panvel.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:
1. `CONTEXTO.md` — arquitetura, regras de negócio, armadilhas, histórico
2. `COMO_FUNCIONA.md` — manual da operação (onde salvar arquivo, o que checa)

E respeite estas regras, que vieram de erros reais:

1. **`python3 validar_js.py` antes de publicar.** O JS está todo num arquivo;
   erro de sintaxe deixa o site EM BRANCO.
2. **Scripts longos em segundo plano** (`nohup ... &` + `sleep` + `tail`). A
   conexão cai depois de ~4 min.
3. **Conferir DEPOIS de gravar, não só antes.**
4. **Verificar se a substituição de texto aconteceu**, com `grep -c` esperando
   o número certo de ocorrências.
5. **`publicar.sh` versiona SÓ o index.html.** Mudou um `.py`? Commitar à mão.
6. **Ler o arquivo real antes de supor o formato.**
7. **Ao mexer em tabela, conferir cabeçalho x corpo x linha de total** (contar
   `<th>`, `<td>` e colspans) e remapear os índices de formatação do Excel.
8. **Não decidir tipo de arquivo pelo NOME** quando dá para olhar as colunas.
9. **Desconfiar de trechos com `/* _fix... */`** — correções aplicadas por
   script já deixaram três bugs de variável fora de escopo, todos silenciosos.
10. **Dinheiro de comissão nunca arredonda.** Use `fmtFull()`.
11. **Vendedor errado? Corrija em `equivalencias.py`**, nunca na tela. Confira
    antes se já existe regra para o cliente (num dict, a ÚLTIMA vence).
12. **Meses anteriores ao corte já estão PAGOS — não se mexe.**
13. **Todo indicador agregado precisa dizer sobre o que agrega.** "Lojas com 1
    unidade" somado entre SKUs não são lojas. "Presença média" com inativos não
    é presença. Três correções em dois dias vieram disso.
14. **Na Apresentação, respeitar as regras de negócio do CONTEXTO.md**: não
    expor o percentual do corte e não mostrar o concorrente na tela.

## Estado do sistema

**14 categorias** no ciclo automático, rotina às 18h (que também publica
sozinha se o index mudar). Julho fechado em R$ 11.004.891,35, batendo entre
faturamento, vendedores e comissões. Agosto da Panvel entrando semanalmente,
marcado como parcial. Seis empresas da São João e três da Panvel com
classificação completa (linha/categoria/grupo) e mix ativo vindo da planilha.
