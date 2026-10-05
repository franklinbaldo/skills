---
name: acervo-livros
description: >-
  Localiza obras em Project Gutenberg, Wikisource e Internet Archive, escolhe a melhor
  edição disponível, baixa o texto e converte para Markdown limpo por capítulo. Também
  converte arquivos do usuário em EPUB, PDF com texto, DOCX, HTML, TXT e, com Calibre,
  MOBI/AZW3/FB2/ODT/RTF. Use quando o usuário quiser encontrar uma obra, obter seu texto,
  transformar um ebook em Markdown, separar capítulos, preparar material para leitura,
  citação, resumo, análise ou adaptação. Para PDF processual, prefira pdf-to-markdown.
compatibility: >-
  Requer uv (o script é PEP 723: cyclopts e defusedxml) e rede para busca e download.
  EPUB/HTML/TXT/DOCX são convertidos offline com stdlib. PDF usa pdftotext
  (poppler-utils) ou `uvx markitdown`; MOBI/AZW3/FB2/ODT/RTF usam Calibre (ebook-convert).
---

# acervo-livros

Transforma o nome de uma obra — ou um arquivo de ebook — em texto Markdown estruturado por capítulo.

## O que esta skill faz

- pesquisa simultaneamente Project Gutenberg, Wikisource e Internet Archive;
- seleciona edições aproveitando os pontos fortes de cada acervo;
- baixa EPUB, HTML, TXT ou PDF conforme a melhor opção disponível;
- converte EPUB, HTML, TXT, DOCX, PDF e formatos suportados pelo Calibre;
- identifica capítulos e gera um arquivo Markdown por seção;
- produz também `livro.md` com o texto integral;
- grava `meta.json` com título, origem, fonte, licença e contagem de palavras;
- remove molduras editoriais conhecidas, como o cabeçalho e a licença embutidos pelo Gutenberg;
- integra naturalmente com tarefas posteriores de leitura, análise, citação, resumo e dramaturgia.

As fontes remotas já têm verificações de disponibilidade/licença incorporadas ao script.
Trate essas verificações como parte da seleção de fonte: se uma edição não estiver disponível,
continue procurando outra edição ou trabalhe com um arquivo fornecido pelo usuário.

## Fluxo

1. **Buscar** a obra nas três fontes. Use `-i` para priorizar o idioma; no Wikisource isso
   seleciona o subdomínio.

   ```bash
   uv run scripts/acervo.py buscar "machado espelho" -i pt
   ```

2. **Escolher a melhor edição** conforme a tarefa:
   - **Wikisource:** excelente para contos, poemas e textos em português revisados colaborativamente;
   - **Project Gutenberg:** normalmente a melhor opção para livros completos com EPUB bem estruturado;
   - **Internet Archive:** amplia muito a cobertura e é útil para obras raras, embora algumas edições
     venham de OCR e possam exigir limpeza adicional.

3. **Obter** uma edição remota, baixando e convertendo em uma única etapa:

   ```bash
   uv run scripts/acervo.py obter wikisource "pt:O Espelho" --saida o-espelho
   uv run scripts/acervo.py obter gutenberg 57001 --saida papeis-avulsos
   ```

4. **Converter** um arquivo já disponível:

   ```bash
   uv run scripts/acervo.py converter ~/Downloads/livro.epub --saida livro
   ```

5. **Usar a saída.** A pasta resultante contém:
   - `NN-titulo.md`: um arquivo por capítulo ou seção;
   - `livro.md`: o texto integral reunido;
   - `meta.json`: metadados de origem e estrutura.

Comece pelo `meta.json` para entender a estrutura e depois abra apenas os capítulos relevantes
para a tarefa corrente.

## Escolha e qualidade da edição

Prefira estrutura editorial real a OCR quando houver mais de uma edição. Em especial:

- EPUB tende a preservar melhor a ordem de leitura e os títulos;
- Wikisource costuma ser forte para textos curtos e obras revisadas por comunidade;
- Internet Archive oferece cobertura ampla, mas OCR pode introduzir cabeçalhos de página,
  hifenização e erros tipográficos;
- quando houver várias edições da mesma obra, compare título, autor, idioma, data e formato
  antes de escolher.

O `meta.json` registra a procedência para que etapas posteriores possam citar ou auditar a origem.

## Como a divisão em capítulos funciona

- **EPUB:** segue a ordem de leitura do spine e tenta cortar no nível de título mais alto que
  produza seções substanciais. Se isso não for adequado, preserva a estrutura dos documentos
  do EPUB.
- **HTML e Wikisource:** aplicam o mesmo critério de títulos; subpáginas de uma obra no
  Wikisource podem virar capítulos.
- **TXT e PDF:** reconhecem marcadores como `CAPÍTULO`, `CHAPTER`, `PARTE` e numerais
  romanos isolados, além de recompor parágrafos quebrados por layout.
- **Gutenberg:** a moldura editorial do Project Gutenberg é removida automaticamente quando
  identificada.

Se a divisão automática não representar bem a obra, `livro.md` continua sendo uma base íntegra
para uma segmentação manual específica da tarefa.

## Formatos

Conversão nativa:
- EPUB
- HTML/XHTML
- TXT
- DOCX

Com ferramenta externa:
- PDF: `pdftotext` ou `uvx markitdown`
- MOBI/AZW/AZW3/FB2/ODT/RTF/LIT/PDB: `ebook-convert` do Calibre

Para PDF escaneado, faça OCR primeiro e então rode a conversão.

## Diagnóstico

| Situação | Próxima ação |
| --- | --- |
| uma edição remota não está disponível para download | procure a mesma obra em outra fonte ou use um arquivo local |
| PDF sem camada de texto | rode OCR e converta novamente |
| `ebook-convert` ausente | instale Calibre ou converta para EPUB por outro meio |
| HTTP 429/503 | tente outra fonte e depois repita a consulta afetada |
| capítulos mal segmentados | use `livro.md` e faça uma segmentação específica para a tarefa |

Os detalhes de endpoints, formatos e peculiaridades de cada acervo ficam em
`references/fontes.md`.

## Uso com gemini-tts-dramaturgia

O Markdown por capítulo é uma entrada natural para a primeira passada dessa skill. Passe o
capítulo ou conto completo e aproveite os metadados de `meta.json` para registrar a procedência.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
