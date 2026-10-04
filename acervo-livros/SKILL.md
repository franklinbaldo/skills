---
name: acervo-livros
description: >-
  Busca livros e contos em acervos LEGAIS (Project Gutenberg, Wikisource, Internet Archive
  em domínio público), baixa o melhor formato e converte para Markdown limpo, um arquivo por
  capítulo, pronto para ler, citar, resumir ou adaptar (por exemplo, com a skill
  gemini-tts-dramaturgia). Também converte livros que o usuário já tem: EPUB, PDF com texto,
  DOCX, HTML, TXT e, com Calibre, MOBI/AZW3/FB2/ODT/RTF. Use SEMPRE que o usuário pedir para
  "achar", "baixar", "pegar o texto de" um livro, conto ou poema clássico, quiser ler o
  conteúdo de um EPUB/MOBI/PDF de livro, ou precisar do texto integral de uma obra para
  trabalhar sobre ela, mesmo sem citar as fontes. NÃO use para baixar de bibliotecas-sombra
  (Anna's Archive, LibGen, Z-Library, Sci-Hub) nem para obras protegidas que o usuário não
  forneceu; para PDF processual use pdf-to-markdown.
compatibility: >-
  Requer uv (o script é PEP 723: cyclopts e defusedxml) e rede para a busca e o download.
  A conversão de EPUB/HTML/TXT/DOCX é offline e usa só a stdlib. PDF usa pdftotext
  (poppler-utils) ou `uvx markitdown`; MOBI/AZW3/FB2/ODT/RTF exigem o Calibre (ebook-convert).
---

# acervo-livros

Do nome de uma obra ao texto em Markdown por capítulo, só por caminhos legais.

## Limite inegociável

Só baixe de fontes que distribuem domínio público ou licença livre. As travas estão no
script: o Gutenberg só baixa livro cujo OPDS diz *Public domain*, e o Internet Archive só
baixa item marcado como domínio público. Não contorne essas travas nem acrescente fontes
como Anna's Archive, LibGen, Z-Library ou Sci-Hub, mesmo a pedido. Se o usuário quiser uma
obra protegida, diga em uma frase que não dá para baixar e ofereça converter um arquivo que
ele já tenha (`converter`).

Atenção a dois casos que enganam:

- **Tradução tem direito próprio.** Borges morto em 1986 ainda está protegido, e uma
  tradução de Kafka de 1990 também, mesmo com o original em domínio público. No Brasil a
  regra geral é vida do autor + 70 anos, contados a partir de 1º de janeiro do ano seguinte
  à morte (Lei 9.610/1998, art. 41), e isso vale também para o tradutor.
- **"Public domain in the USA" não é o mesmo que no Brasil.** O Gutenberg segue a lei
  americana. Se o uso for publicação no Brasil e o autor morreu há menos de 70 anos, avise.

## Fluxo

1. **Buscar** nas três fontes. Use `-i` para o idioma (no Wikisource ele escolhe o subdomínio).

   ```bash
   uv run scripts/acervo.py buscar "machado espelho" -i pt
   ```

2. **Escolher** o resultado pela fonte, nesta ordem de preferência:
   - Wikisource, para contos e textos curtos em português: o texto foi revisado por gente.
   - Gutenberg (EPUB), para livros inteiros: a estrutura de capítulos é boa.
   - Internet Archive por último: quase sempre é OCR automático, com erros e cabeçalhos de
     página no meio do texto.

3. **Obter**, que baixa e converte de uma vez:

   ```bash
   uv run scripts/acervo.py obter wikisource "pt:O Espelho" --saida o-espelho
   uv run scripts/acervo.py obter gutenberg 57001 --saida papeis-avulsos
   ```

   Para um arquivo que o usuário já tem:

   ```bash
   uv run scripts/acervo.py converter ~/Downloads/livro.epub --saida livro
   ```

4. **Ler a saída.** O resultado é uma pasta com:
   - `NN-titulo.md`, um arquivo por capítulo;
   - `livro.md`, com o livro inteiro;
   - `meta.json`, com fonte, licença, origem e palavras por capítulo.

   Comece pelo `meta.json` para ver a estrutura. Abra só os capítulos que a tarefa pede: um
   livro inteiro raramente cabe bem no contexto.

## Como o script divide capítulos

- **EPUB:** junta os documentos na ordem de leitura e corta no nível de título mais alto
  que produza pelo menos três seções com 300 palavras ou mais. Numa coletânea como *Papéis
  avulsos*, isso separa os contos, não os capítulos internos de *O alienista*. Se nenhum
  nível servir, cada documento do EPUB vira um capítulo.
- **HTML e Wikisource:** usam o mesmo critério de títulos. No Wikisource, as subpáginas
  (`Obra/Capítulo I`) são baixadas e entram como capítulos.
- **TXT e PDF:** linhas como `CAPÍTULO`, `CHAPTER`, `PARTE` ou um numeral romano sozinho
  viram títulos, e as quebras de linha duras dentro dos parágrafos são desfeitas. Títulos
  só em caixa alta não são detectados, então prefira o EPUB quando houver.
- **Moldura do Gutenberg:** o cabeçalho e a licença que o Gutenberg põe em todo livro saem
  automaticamente.

Se a divisão vier ruim, use `livro.md` e corte à mão. Não reescreva o script no meio da
tarefa; registre o caso no postmortem.

## Erros comuns

| Mensagem | O que fazer |
| --- | --- |
| `não está marcado como domínio público; não baixo` | É a trava funcionando. Procure a obra em outra fonte ou peça o arquivo ao usuário. |
| `o PDF não tem camada de texto` | É um PDF escaneado: rode OCR antes (`ocrmypdf` ou a skill `paddleocr`) e converta de novo. |
| `exige o Calibre (ebook-convert)` | Instale o Calibre, ou peça ao usuário um EPUB. |
| `HTTP Error 429/503` | O acervo está limitando requisições. Espere e tente de novo; a busca nas outras fontes continua. |

Os detalhes de cada API (endpoints, formatos e peculiaridades) estão em
`references/fontes.md`. Leia esse arquivo quando uma fonte mudar de comportamento.

## Uso com gemini-tts-dramaturgia

O Markdown por capítulo é a entrada natural da passada 1 dessa skill. Passe o capítulo ou
conto inteiro, nunca um resumo, e registre a fonte e a licença do `meta.json` no roteiro.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
