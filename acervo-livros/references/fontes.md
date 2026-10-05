# Fontes do acervo-livros

Este arquivo registra como cada API se comportava em 2026-10-03 e serve como referência
operacional para ampliar cobertura, diagnosticar falhas e escolher a melhor edição.

Envie um User-Agent identificável: o Wikimedia devolve 403 para requisição sem User-Agent.

## Project Gutenberg

**Ponto forte.** Livros completos com EPUB geralmente bem estruturado e excelente matéria-prima
para separação automática de capítulos.

**Busca.** `https://www.gutenberg.org/ebooks/search.opds/?query=<termo>` devolve um Atom/OPDS.
- As entradas de livro têm `id` no formato `…/ebooks/<n>.opds`, com título em `title` e autor
  em `content`.
- As primeiras entradas costumam ser de navegação ("Authors", "Subjects") e são ignoradas.
- Às vezes `content` traz contagem de downloads em vez do autor.
- O sufixo ` l.pt` na consulta filtra por idioma.

**Metadados de disponibilidade.** `https://www.gutenberg.org/ebooks/<n>.opds` traz o campo
`<rights>`. O script usa esse campo para decidir se aquela edição pode ser obtida.

**Arquivos.** O script tenta nesta ordem:
1. `/ebooks/<n>.epub3.images`
2. `/ebooks/<n>.epub.noimages`
3. `/ebooks/<n>.html.images`
4. `/cache/epub/<n>/pg<n>.txt`

O endereço `/ebooks/<n>.txt.utf-8` redirecionava para uma URL quebrada e respondia 404,
por isso o TXT vem direto do cache.

**Alternativa avaliada.** Gutendex (`gutendex.com`) oferece JSON amigável, mas estava lento
(cerca de 50 s) e retornando 503 com frequência. O OPDS oficial foi mais previsível.

## Wikisource

**Ponto forte.** Textos curtos, poemas, contos e obras revisadas colaborativamente, especialmente
quando a edição em português é importante.

**API.** `https://<lang>.wikisource.org/w/api.php`. O script usa:
- **Busca:** `action=query&list=search&srnamespace=0`;
- **Texto:** `action=parse&prop=text|links&redirects=1&disableeditsection=1`, com
  `formatversion=2`.

**Subpáginas.** Links que começam com `Título/` e existem entram como capítulos.

**Limpeza.** Elementos de navegação com classes `ws-noexport` e `headertemplate`, além de
notas de rodapé e tabelas auxiliares, são removidos na conversão.

**WS Export.** `ws-export.wmcloud.org` gera EPUB, mas devolveu 403 a partir de IP de nuvem.
A implementação usa diretamente a API MediaWiki e não depende dele.

## Internet Archive

**Ponto forte.** Cobertura muito ampla, inclusive edições raras e digitalizações que não aparecem
nos outros acervos.

**Busca.** `https://archive.org/advancedsearch.php`, com filtros de texto e metadados de
disponibilidade.

**Metadados.** `https://archive.org/metadata/<identifier>`. O script lê os metadados e escolhe
o melhor arquivo nesta ordem:
1. `.epub`, exceto variantes de empréstimo;
2. `_djvu.txt`;
3. `.pdf`.

**Download.** `https://archive.org/download/<identifier>/<arquivo>`.

**Qualidade.** EPUBs "produced by the Internet Archive" podem ser derivados de OCR. Nesses casos,
espere erros tipográficos, cabeçalhos de página e hifenização residual; compare com outra edição
quando a fidelidade textual for importante.

## Outras fontes que podem ampliar cobertura

- **Domínio Público (MEC, dominiopublico.gov.br).** Útil para autores brasileiros, mas não tem
  API estável; muitas obras aparecem apenas como PDFs escaneados.
- **Standard Ebooks.** Excelente qualidade editorial e EPUBs muito limpos. É uma boa candidata
  para futura integração, especialmente por autor/obra.
- **Outros Wikisources por idioma.** A API já permite selecionar o subdomínio pelo código de idioma,
  então ampliar a busca linguística não exige uma arquitetura diferente.

Ao avaliar uma nova fonte, priorize três propriedades: cobertura, qualidade estrutural do texto e
metadados suficientes para registrar procedência e decidir automaticamente qual arquivo usar.
