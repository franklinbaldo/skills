# jbig2enc: licenciamento e alternativas de formato

Análise de viabilidade jurídica e técnica que embasou a adoção do
[`jbig2enc`](https://github.com/agl/jbig2enc) como backend **opcional** de
compressão bitonal na skill `pdf-compression` (flag `--jbig2` de
`compress.py`), ao lado do CCITT Group 4 (`bw` mode, ainda o padrão) e JPEG
(`gray`/`color` modes).

**Status: implementado**, incluindo duas correções de review (PR #17) que
valem registrar aqui porque mudam garantias de corretude, não só estilo:

- **Normalização do dicionário do XObject.** `_set_jbig2_stream()` reaproveita
  o xref da imagem original (em vez de criar um objeto novo, como faria
  `Page.replace_image()`), então qualquer chave antiga incompatível
  (`/Decode`, `/ImageMask`, `/Mask`, `/SMask`...) precisa ser explicitamente
  zerada antes de gravar o stream JBIG2 — do contrário um `/Decode [1 0]`
  residual inverte preto/branco, ou um `/ImageMask true` residual transforma
  o XObject numa máscara de estêncil incompatível com `/ColorSpace`. A
  correção limpa (via `null`, semanticamente equivalente a "ausente" no PDF)
  toda chave fora do conjunto conhecido de um XObject de imagem simples antes
  de gravar as chaves novas.
- **Comparação de tamanho contra o stream real, não o container TIFF.**
  `Page.replace_image()` decodifica o TIFF/G4 de volta para um bitmap bruto
  imediatamente; o `doc.save(..., deflate=True)` da pipeline então
  recodifica esse bitmap como `/FlateDecode` — o payload G4 nunca chega ao
  PDF salvo. Um TIFF/G4 de ~15 KB pode virar um stream final de ~9,5 KB só
  com Flate sobre o bitmap bruto. Comparar o candidato JBIG2 contra o
  tamanho do arquivo TIFF (como a primeira versão desta PR fazia) podia
  aceitar um JBIG2 maior que o G4 real, contrariando a garantia "só quando
  for menor". A correção materializa os dois candidatos (JBIG2 e
  G4-via-`replace_image`) num PDF de uma página descartável, salvo com as
  mesmas flags da pipeline real, e compara o tamanho do stream que
  efetivamente seria salvo.

`compress.py --mode bw --jbig2` chama o binário `jbig2` (modo
generic-region, sem symbol/text-region matching e sem refinamento — ver
seções 3 e 5), decodifica o resultado de volta via o próprio decoder JBIG2
do MuPDF e compara pixel a pixel com o bitmap binarizado; só substitui o
CCITT G4 quando essa verificação passa **e** o arquivo, medido da forma
descrita acima, fica menor. Sem o binário `jbig2` no `PATH`, a skill cai de
volta para CCITT G4 automaticamente e imprime orientação de instalação
honesta para a máquina atual — `apt-get`/`brew` têm o pacote pronto; Fedora e
Arch não empacotam o encoder nos repositórios oficiais (só o decoder
`jbig2dec`, no caso do Fedora, ou a AUR, no caso do Arch), então recebem
instruções de build/AUR em vez de um comando que falharia. Não há binário
empacotado no repositório nem instalação automática silenciosa; é só mais
um pacote de sistema a instalar quando fizer falta, igual a qualquer outra
CLI que o agente já sabe instalar sob demanda.

`scripts/test_compress_jbig2.py` cobre as duas correções acima com
reproduções diretas dos cenários encontrados no review (xref com `/Decode
[1 0]`, xref com `/ImageMask true`, e um caso onde o JBIG2 vence o TIFF mas
perde para o G4 real), além de um teste ponta a ponta comparando pixel a
pixel a saída `--jbig2` contra a saída G4-only.

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
| **JBIG2 lossless** | `JBIG2Decode` (PDF 1.4+) | Apache-2.0 (jbig2enc) | Codificação aritmética por contexto supera MMR (CCITT G4) em texto binário mesmo só com o generic region coder (sem dicionário de símbolos — ver nota abaixo); o modo `-s` (symbol/text region), não usado aqui, ganharia mais ainda ao compartilhar glifos repetidos entre páginas. |
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

## 5. Plano de implementação e status

1. ✅ Manter Pillow + TIFF/G4 (`compress.py --mode bw`) como fallback
   universal e como **padrão** — `--jbig2` é estritamente opt-in, sem mudar
   o comportamento de quem não passar a flag.
2. ✅ `jbig2enc` entra como backend opcional, usado apenas para páginas já
   classificadas como bitonais/escaneadas (reaproveita o `bw_img` já
   binarizado pela mesma heurística de `is_scanned_page`/adaptive threshold
   — não há um segundo threshold nem reprocessamento).
3. ✅ Usa **somente o generic region coder** do `jbig2enc` (sem `-s`/symbol
   matching, sem `-r`/refinamento — ver seção 3). É o modo bit-exato mais
   simples de auditar; symbol/text-region mode fica como possível trabalho
   futuro, não implementado.
4. ✅ Cada candidato JBIG2 é decodificado de volta (via o decoder JBIG2 do
   próprio MuPDF, injetando o stream bruto num documento fitz descartável)
   e comparado bit a bit com o bitmap 1-bit original antes de ser aceito.
   Validado também de ponta a ponta com o encoder `jbig2` e o decoder
   independente `jbig2dec` (pacotes Debian `jbig2`/`jbig2dec`).
5. ✅ Só escolhe a saída JBIG2 quando o arquivo resultante é **efetivamente
   menor** que o CCITT G4 equivalente para aquela imagem — caso contrário,
   mantém o CCITT G4 já calculado.
6. ⏳ Testado com MuPDF (via a própria verificação de roundtrip) e produção
   local com `jbig2dec`. **Ainda não testado** em Acrobat, Chrome/PDFium,
   Firefox/PDF.js nem nos visualizadores usados no peticionamento judicial
   — fazer essa verificação antes de adotar `--jbig2` por padrão em fluxos
   de produção sensíveis.
7. ✅ Dependência externa (binário `jbig2`, pacote de sistema — não é
   pacote PyPI) documentada nos "Common Mistakes" do `SKILL.md`, com a
   mensagem de aviso que a própria `compress.py` imprime quando o binário
   está ausente.
8. ⏳ Segmentação MRC para páginas mistas continua como trabalho futuro,
   fora do escopo desta implementação (que cobre apenas páginas já
   classificadas como bitonais).
