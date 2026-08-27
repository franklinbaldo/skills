---
name: juris-tjro
description: >-
  Consulta jurisprudência e inteiro teor no sistema JURIS do TJRO: acórdãos,
  sentenças, votos, decisões, ementas e relatórios de 1º e 2º graus. Use quando a
  proposição depende do que o TJRO efetivamente decidiu, fundamentou ou escreveu.
  Não use para contagem ampla de processos, panorama de tramitação ou linha de
  movimentos — para isso use DataJud. Para reconstrução documental de autos
  carregados, use notebooklm-processos.
compatibility: >-
  Requires Python 3 and outbound HTTPS access to the TJRO JURIS API. The bundled
  client is stdlib-only and does not require a private credential.
---

# JURIS TJRO — teor e fundamento

A função desta skill é responder perguntas sobre **o conteúdo dos atos judiciais
do TJRO**.

Contrato da fonte:

```text
JURIS sabe: inteiro teor, ementa, voto, sentença, decisão, relatório, fundamento
JURIS não é a melhor fonte para: volume processual, linha de tramitação, estado atual
```

A pergunta central é: **qual proposição jurídica ou fática o documento do
tribunal sustenta?**

## Regra de roteamento

- “o TJRO decidiu/entendeu/fundamentou X?” → JURIS;
- “qual foi o teor daquela sentença/acórdão/voto?” → JURIS;
- “há precedentes locais sobre X?” → JURIS;
- “em que fase está o processo / qual último movimento?” →
  [`datajud`](../datajud/SKILL.md);
- “quantos processos existem por classe/assunto/órgão?” → DataJud;
- “o que dizem as peças, anexos e documentos de um processo carregado?” →
  [`notebooklm-processos`](../notebooklm-processos/SKILL.md);
- “qual a jurisprudência atual de STJ/STF/outro tribunal?” → fonte externa
  adequada.

Não use um snippet de resultado para afirmar ratio decidendi quando o inteiro
teor está disponível.

## Fluxo

1. Defina a proposição que precisa ser sustentada.
2. Busque com o termo mais distintivo possível.
3. Use filtros para reduzir ruído.
4. Leia o inteiro teor dos candidatos relevantes antes de afirmar fundamento.
5. Separe holding/desfecho, fundamento, contexto fático e eventual obiter.
6. Compare precedentes apenas depois de saber que tratam realmente da mesma
   questão material.
7. Quando a pergunta virar tramitação/estado atual, pare e passe ao DataJud.

## CLI

Toda interação deve passar por `scripts/juris.py`.

Busca:

```bash
uv run scripts/juris.py buscar "<termo>" \
  [--tipo ACÓRDÃO EMENTA SENTENÇA VOTO DECISÃO RELATÓRIO] \
  [--classe "APELAÇÃO CÍVEL"] [--orgao "2ª Câmara"] [--relator "SOBRENOME"] \
  [--contendo palavra1 "expressão exata"] \
  [--de DD/MM/AAAA] [--ate DD/MM/AAAA] \
  [--recentes] [--tamanho N] [--trecho-perto TERMO] [--json]
```

Documentos de um processo:

```bash
uv run scripts/juris.py processo 7030969-47.2024.8.22.0001
```

Inteiro teor:

```bash
uv run scripts/juris.py texto 21458095
uv run scripts/juris.py texto 21458095 --max 8000
```

Facetas:

```bash
uv run scripts/juris.py facetas "improbidade" --limite 20
```

## Estratégia de busca

A busca textual do servidor é **OR e analisada**. Mais palavras podem aumentar o
ruído.

Portanto:

1. coloque no termo principal a expressão mais distintiva;
2. use `--contendo` para condições adicionais obrigatórias;
3. use `--recentes` somente quando recência for parte da pergunta;
4. quando um resultado parecer decisivo, abra o `texto <id>`.

Exemplo:

```bash
uv run scripts/juris.py buscar "18,25%" --tipo ACÓRDÃO --contendo "polícia civil"
```

## Unidade mínima de precedente

Ao usar um julgado como suporte, tente preservar:

```text
CNJ / identificação
+ órgão julgador
+ data
+ tipo de documento
+ questão decidida
+ desfecho
+ fundamento realmente utilizado
+ trecho/localização suficiente
```

Não trate ementa como substituto automático do voto/inteiro teor quando a
controvérsia depende da fundamentação.

## Composição com DataJud

Para um processo concreto do TJRO, as duas fontes podem formar uma cadeia:

```text
DataJud → localiza grau, data e movimento relevante
JURIS   → recupera o documento e seu teor
```

Mantenha as provas separadas. Exemplo de formulação correta:

> O DataJud registra o julgamento em determinada data; no inteiro teor disponível
> no JURIS, o colegiado fundamenta o resultado em X.

Evite:

> O DataJud mostra que o tribunal entendeu X.

Isso atribui conteúdo a uma fonte que só forneceu metadata.

## Comparação de precedentes

Antes de afirmar “o TJRO vem decidindo”, verifique se os resultados compartilham
a mesma questão relevante. Não conte como apoio equivalente decisões que apenas
contêm as mesmas palavras.

Para cada candidato, pergunte:

- a questão jurídica é a mesma?
- o contexto fático/processual importa para o resultado?
- o fundamento é central ou incidental?
- houve distinção, ressalva ou mudança de entendimento?
- o ato é sentença isolada, voto, acórdão colegiado ou outro documento?

Uma lista longa de hits não substitui uma amostra menor lida em profundidade.

## Armadilhas load-bearing

O script já trata:

- `tipo` como array, evitando HTTP 500;
- filtro de datas client-side porque range no servidor quebra;
- normalização do CNJ;
- limpeza de HTML/base64 do inteiro teor;
- endpoint real `POST /search/varios_parametros/`.

Nunca use `GET /search/documentos/` como se filtrasse corretamente; ele pode
devolver o corpus sem respeitar os parâmetros esperados.

## Como apresentar

Sintetize os julgados relevantes. Para cada um, informe identificação, órgão,
data e a proposição que ele realmente sustenta. Se a conclusão depender do
inteiro teor, diga que ele foi lido; se só houver snippet/ementa, limite a força
da afirmação.

Não despeje HTML nem JSON cru.

## Definition of Done

A pesquisa termina quando:

- a proposição jurídica investigada está explícita;
- os candidatos relevantes foram filtrados por questão, não só por palavra;
- o inteiro teor foi lido quando necessário para afirmar fundamento;
- holding/desfecho e contexto foram distinguidos de linguagem incidental;
- não se usou JURIS como substituto para estado processual/contagem;
- quando DataJud participou, metadata e teor permanecem separados por
  proveniência;
- a resposta diz o que os documentos sustentam sem transformar coincidência de
  termos em jurisprudência consolidada.

A skill é bem-sucedida quando responde **o que o TJRO efetivamente disse e por
quê**, e sabe não responder perguntas que pertencem ao DataJud.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
