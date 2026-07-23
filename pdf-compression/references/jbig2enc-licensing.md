# jbig2enc: licenciamento e alternativas de formato

Análise de viabilidade jurídica e técnica para eventual adoção do
[`jbig2enc`](https://github.com/agl/jbig2enc) como backend opcional de
compressão bitonal na skill `pdf-compression`, hoje limitada a CCITT Group 4
(`bw` mode) e JPEG (`gray`/`color` modes). **Não implementado ainda** — este
documento é o estudo que embasa a decisão.

## 1. Licença do código

- `jbig2enc` é distribuído sob **Apache License 2.0**. Permite uso, modificação,
  incorporação e redistribuição — inclusive em produto proprietário — sem
  obrigação de abrir o código do projeto que o incorpora. Na redistribuição é
  preciso preservar avisos de copyright/licença e identificar modificações
  relevantes. ([agl/jbig2enc](https://github.com/agl/jbig2enc))
- A dependência principal, **Leptonica**, usa licença BSD-2-Clause (também
  permissiva).
- Chamar o binário `jbig2` como subprocesso (o padrão de integração desta
  skill, igual ao que já é feito com `pymupdf`/`Pillow` via CLI) não gera
  qualquer efeito de copyleft sobre o código desta skill — não há linking
  estático nem incorporação de código-fonte.
- O projeto está ativo: a versão 0.32 foi publicada em junho de 2026
  (modernização para C++17, build multi-sistema — CMake/Meson/autotools —
  e correções de validação de argumentos e portabilidade).

## 2. Patentes do formato

- O repositório mantém um arquivo `doc/PATENTS` com um histórico das patentes
  relevantes ao JBIG1/JBIG2, todas expiradas (a mais recente, uma patente
  coreana depositada em 1997, expirou em 2004). A
  [issue #58](https://github.com/agl/jbig2enc/issues/58) ("Update on patent
  situation") lista patentes adicionais (IBM, Mitsubishi Electric etc.,
  depositadas entre 1979–1984), também todas expiradas.
- A documentação do OCRmyPDF confirma: todas as patentes americanas
  conhecidas relativas a JBIG2 expiraram até 2017. A ressalva teórica é sobre
  patentes desconhecidas em outras jurisdições — não há garantia universal.
  A decodificação JBIG2 nunca foi objeto de patente e é suportada
  nativamente por praticamente todo visualizador de PDF desde 2001.

**Registro sugerido para análise de dependências:**

> jbig2enc é uma implementação livre sob Apache-2.0, apta a uso comercial. As
> patentes conhecidas relacionadas ao JBIG2 estão expiradas; não se afirma,
> porém, garantia universal de inexistência de qualquer patente desconhecida
> em todas as jurisdições.

Conclusão: não há impedimento jurídico relevante, em 2026, para uso do
`jbig2enc` nesta skill.

## 3. Ressalva operacional conhecida

O próprio README do projeto documenta que o **refinement coding causa crash
no Acrobat** (não está claro se é bug do Acrobat ou do encoder). Se um
backend JBIG2 for implementado, refinamento **não deve ser habilitado** sem
testes de compatibilidade em Acrobat, Chrome/PDFium, Firefox/PDF.js, MuPDF e
os visualizadores usados no fluxo de peticionamento judicial.

## 4. JBIG2 lossless segue sendo a melhor opção prática para texto binário

Nenhum formato mais recente substitui claramente o JBIG2 lossless para
páginas escaneadas binarizadas (texto em preto e branco) dentro de um PDF
convencional — a razão é que codecs recentes foram desenhados para
fotografia/HDR/cor, não para dicionários de glifos repetidos:

| Formato | Filtro nativo em PDF | Licença | Por que (não) serve aqui |
| --- | --- | --- | --- |
| **JBIG2 lossless** | `JBIG2Decode` (PDF 1.4+) | Apache-2.0 (jbig2enc) | Dicionário de símbolos compartilhados entre ocorrências e entre páginas — vantagem estrutural para texto binário. |
| DjVu/JB2 | Nenhum (formato próprio) | DjVuLibre é GPL-2 | Tecnicamente similar (dicionário de formas), mas exigiria entregar `.djvu` em vez de PDF — quebra interoperabilidade. |
| JPEG XL lossless | Nenhum (sem `JXLDecode`) | BSD-3-Clause + concessão de patentes | Ótimo lossless genérico, mas sem filtro de imagem em PDF e sem foco em símbolos repetidos. |
| AVIF lossless | Nenhum | BSD (libavif), royalty-free (AOMedia) | Deriva do AV1, feito para foto; não é filtro nativo de PDF. |
| JPEG 2000 lossless | `JPXDecode` (PDF 1.5+) | Royalty-free | Único concorrente moderno com filtro nativo de PDF. Bom para mapas/tons de cinza, mas sem dicionário de símbolos — perde para JBIG2 em texto puro. |
| Brotli em PDF | Filtro genérico proposto para PDF 2.0 | BSD-3-Clause (libbrotli) | Compressor genérico de stream, não entende glifos/padrões — não é sucessor do JBIG2. |

Para páginas **mistas** (texto + foto + fundo colorido), o ganho maior
tende a vir de uma arquitetura MRC (Mixed Raster Content) — máscara de texto
em JBIG2 lossless + fundo/primeiro plano em JPEG/JPEG2000 de resolução menor
+ camada OCR — em vez de trocar o codec único da página inteira. Isso é
trabalho futuro, fora do escopo deste documento.

## 5. Recomendação de implementação (quando for feita)

1. Manter Pillow + TIFF/G4 (`compress.py --mode bw`) como fallback universal
   — continua funcionando sem dependências externas.
2. Adicionar `jbig2enc` como backend **opcional**, usado apenas para páginas
   já classificadas como bitonais/escaneadas (mesma heurística de
   `is_scanned_page`).
3. Usar **somente o modo lossless** do `jbig2enc` (sem `-s`/symbol matching
   com perdas, sem refinamento habilitado — ver seção 3).
4. Após codificar, decodificar o resultado e comparar bit a bit com o bitmap
   1-bit original antes de aceitar a saída.
5. Só escolher a saída JBIG2 quando o arquivo resultante for **efetivamente
   menor** que o CCITT G4 equivalente — caso contrário, manter o fallback.
6. Testar a compatibilidade do PDF gerado nos visualizadores listados na
   seção 3 antes de tornar o backend padrão.
7. Documentar a dependência externa (binário `jbig2` precisa estar instalado
   no sistema — não é um pacote PyPI) nos "Common Mistakes" do `SKILL.md`.
