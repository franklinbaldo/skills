# Fontes do acervo-livros

Este arquivo registra como cada API se comportava em 2026-10-03. Envie sempre um
User-Agent identificável: o Wikimedia devolve 403 para requisição sem User-Agent.

## Project Gutenberg

**Busca.** `https://www.gutenberg.org/ebooks/search.opds/?query=<termo>` devolve um Atom/OPDS.
- As entradas de livro têm `id` no formato `…/ebooks/<n>.opds`, com o título em `title` e o
  autor em `content`.
- As primeiras entradas costumam ser de navegação ("Authors", "Subjects") e devem ser
  ignoradas.
- Às vezes `content` traz a contagem de downloads em vez do autor.
- O sufixo ` l.pt` na consulta filtra por idioma.

**Licença.** `https://www.gutenberg.org/ebooks/<n>.opds` traz `<rights>Public domain in the USA.</rights>`.
O script só baixa quando esse campo contém "public domain".

**Arquivos.** O script tenta nesta ordem:
1. `/ebooks/<n>.epub3.images`
2. `/ebooks/<n>.epub.noimages`
3. `/ebooks/<n>.html.images`
4. `/cache/epub/<n>/pg<n>.txt`

O endereço `/ebooks/<n>.txt.utf-8` redirecionava para uma URL quebrada e respondia 404,
por isso o TXT vem direto do cache.

**Gutendex** (`gutendex.com`) é um espelho JSON de terceiros. Estava lento (cerca de 50 s)
e devolvendo 503 com frequência, por isso não é usado.

## Wikisource

**API.** `https://<lang>.wikisource.org/w/api.php`. O script usa duas ações:
- **Busca:** `action=query&list=search&srnamespace=0`. O namespace 0 reúne as obras.
- **Texto:** `action=parse&prop=text|links&redirects=1&disableeditsection=1`, com
  `formatversion=2`.

**Subpáginas.** Os links que começam com `Título/` e existem viram capítulos.

**O que é descartado.** O cabeçalho de navegação usa as classes `ws-noexport` e
`headertemplate`, que o conversor descarta. Notas de rodapé (`sup`, `mw-references`) e
tabelas também saem.

**WS Export** (`ws-export.wmcloud.org`, que gera EPUB) devolveu 403 a partir de IP de nuvem.
Não depende dele.

## Internet Archive

**Busca.** `https://archive.org/advancedsearch.php`, com `q` incluindo
`mediatype:texts AND (licenseurl:*publicdomain* OR possible-copyright-status:"NOT_IN_COPYRIGHT")`.

**Metadados.** `https://archive.org/metadata/<identifier>`. O script confere de novo a
licença e escolhe o arquivo nesta ordem:
1. `.epub`, exceto `_lcp.epub`, que tem DRM de empréstimo;
2. `_djvu.txt`;
3. `.pdf`.

**Download.** `https://archive.org/download/<identifier>/<arquivo>`.

**Qualidade.** O EPUB "produced by the Internet Archive" é OCR automático. Ele traz um aviso
no início e pode ter erros e cabeçalhos de página no meio do texto.

## Fontes avaliadas e não incluídas

- **Domínio Público (MEC, dominiopublico.gov.br).** Não tem API. As páginas JSP são
  instáveis e os PDFs são muitas vezes escaneados. Para Machado, Alencar e outros autores
  brasileiros, o Wikisource-pt cobre melhor.
- **Standard Ebooks.** É ótimo, mas o feed OPDS completo exige assinatura, e o download
  pela página pública dependeria de raspar HTML. Um candidato para incluir depois via
  `standardebooks.org/ebooks/<autor>/<obra>/downloads/`.
- **Bibliotecas-sombra** (Anna's Archive, LibGen, Z-Library, Sci-Hub). Fora de escopo por
  princípio, não por limitação técnica.
