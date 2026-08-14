# COMECE POR AQUI — retomada em chat novo

Última sessão: 14/08/2026.

## O que fazer AGORA

**Nada urgente em aberto.** Tudo publicado, versionado e no ar.
O que resta depende do Cristiano:

- **Categoria dos itens inativos da Belliz (São João).** A planilha dela só tem
  os 61 ativos, então 78 produtos aparecem sem categoria. A da Granado traz
  Status com ativos e inativos e cobre 100%. Refazer a da Belliz nesse formato
  (Status | Categoria | Descrição) resolve — o coletor já aceita os dois.

- **Canal do cliente:** ele vai preencher a coluna CANAL em
  `_saida/Base_Clientes_Canal.xlsx` (543 clientes: alimentar / farma /
  indireto). Quando devolver, montar a análise por canal. Isso também melhora
  a lacuna de mix do Ranking de Clientes, que hoje sugere oportunidades sem
  saber se fazem sentido para o canal daquele cliente.

- **Acesso da equipe — DECISÃO PENDENTE E IMPORTANTE.** O repositório e o site
  estão PÚBLICOS desde 27/06: faturamento, comissões por vendedor, receitas,
  custos e base de clientes acessíveis a quem tiver o endereço. Antes de
  liberar para a equipe, fechar isso. Assinar GitHub Pro/Team NÃO resolve (o
  Pages continua público; no plano Free, tornar o repo privado derruba o site).
  Caminho recomendado: Cloudflare Pages + Cloudflare Access (grátis até 50
  usuários, login por PIN no e-mail, políticas por caminho). E, para "travar
  telas por pessoa", não basta esconder menu: todo o dado está no index.html.
  Precisa gerar uma versão por perfil, só com os dados daquele perfil.

- **KITs da Panvel aparecem como INATIVO** (29 itens) porque não constam no
  cluster. Podem ser falso inativo. Se a Panvel controlar kits em outro lugar,
  pedir um cluster que os inclua.

## Antes de mexer em qualquer coisa

Leia, nesta ordem:
1. `CONTEXTO.md` — arquitetura, regras de negócio, armadilhas, histórico
2. `COMO_FUNCIONA.md` — manual da operação (onde salvar arquivo, o que checa)

E respeite estas regras de trabalho, que vieram de erros reais:

1. **`python3 validar_js.py` antes de publicar.** O JS está todo num arquivo;
   erro de sintaxe deixa o site EM BRANCO.
2. **Scripts longos em segundo plano** (`nohup ... &` + `sleep` + `tail`). A
   conexão cai depois de ~4 min. Os coletores da Panvel levam 1-3 min.
3. **Conferir DEPOIS de gravar, não só antes.** Uma gravação já apagou 42
   meses congelados e só apareceu na conferência posterior.
4. **Verificar se a substituição de texto realmente aconteceu**, com `grep -c`
   esperando o número certo de ocorrências.
5. **`publicar.sh` versiona SÓ o index.html.** Mudou um `.py`? Commitar à mão
   depois. Passou batido 3x em dois dias.
6. **Ler o arquivo real antes de supor o formato.** Cada cliente tem um layout
   diferente e eles mudam sem aviso — a Panvel mudou dentro de um mesmo dia.
7. **Ao mexer em tabela, conferir cabeçalho x corpo x linha de total.** Contar
   `<th>`, `<td>` e os colspans; e no Excel, remapear os índices de formatação,
   que são posicionais.
8. **Nada de decidir tipo de arquivo pelo NOME** quando dá para olhar as
   colunas. Nomes mudam de significado; layout não.
9. **Desconfiar de trechos com comentário `/* _fix... */`.** São correções
   aplicadas por script sobre o `index.html` e já deixaram TRÊS bugs de
   variável fora de escopo, todos silenciosos (`p.val26` em 3 telas, `nome` no
   Excel de comissões). Ao mexer numa função, conferir se as variáveis citadas
   existem naquele escopo.
10. **Dinheiro de comissão nunca arredonda.** Use `fmtFull()`, não `fmt()`.

## Estado do sistema

**14 categorias** no ciclo automático, rotina às 18h (que também publica
sozinha se o index mudar). Julho fechado em R$ 11.004.891,35, batendo entre
faturamento, vendedores e comissões. Agosto da Panvel entrando semanalmente,
marcado como parcial.
