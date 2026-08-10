---
name: datajud
description: >-
  Consulta metadados processuais oficiais no DataJud/CNJ: capa, classe, assuntos,
  órgão, grau, datas, contagens, facetas e linha de movimentação. Use para saber
  quais processos existem, quantos são, onde tramitam e o que aconteceu na linha
  processual. Não use para afirmar o teor, fundamento ou ratio de sentença,
  decisão, voto ou acórdão. Para teor do TJRO, use juris-tjro; para autos
  carregados e reconstrução documental, use notebooklm-processos.
compatibility: >-
  Requires Python 3 and outbound HTTPS access to the public DataJud/CNJ API.
  No private credential is required; the bundled stdlib client carries the CNJ
  public API key and handles retry/backoff.
---

# DataJud — metadados e movimentação

A função desta skill é responder perguntas sobre a **existência, classificação,
volume e trajetória processual** de casos registrados no DataJud.

Contrato da fonte:

```text
DataJud sabe:   processo, capa, classe, assunto, órgão, grau, datas, movimentos
DataJud não sabe: fundamento jurídico, ratio, argumento, conteúdo integral do ato
```

Nunca preencha o segundo conjunto por inferência a partir do primeiro.

## Regra de roteamento

Escolha a fonte pela proposição que precisa ser provada:

- “o processo existe / em que grau está / qual foi o último movimento?” → DataJud;
- “quantos processos com classe/assunto/órgão/período?” → DataJud;
- “o TJRO decidiu X por causa de Y?” → [`juris-tjro`](../juris-tjro/SKILL.md);
- “o que os documentos deste processo dizem, inclusive peças e anexos?” →
  [`notebooklm-processos`](../notebooklm-processos/SKILL.md) quando o corpus estiver
  carregado;
- “a jurisprudência atual do STJ/STF/outro tribunal diz X?” → pesquisa externa/
  fonte oficial adequada.

Um movimento chamado “Sentença”, “Decisão” ou “Provimento” prova que o ato foi
registrado, não o que o ato fundamentou.

## Fluxo

1. Defina se a pergunta é sobre **um processo**, **uma lista**, **uma contagem** ou
   **uma distribuição**.
2. Use o modo mais barato que resolve a pergunta.
3. Não puxe movimentos completos quando capa/último estado bastarem.
4. Quando o próximo passo depender do conteúdo de um ato, pare e roteie para a
   fonte de teor.
5. Apresente apenas os movimentos/metadados que mudam a conclusão.

## CLI

Toda interação deve passar por `scripts/datajud.py`.

Processo:

```bash
python scripts/datajud.py processo 7027457-61.2021.8.22.0001
python scripts/datajud.py processo 7027457-61.2021.8.22.0001 --movimentos
```

Descobrir códigos:

```bash
python scripts/datajud.py codigos "execucao fiscal" --por classe
python scripts/datajud.py codigos "aposentadoria" --por assunto
```

Buscar:

```bash
python scripts/datajud.py buscar \
  [--classe COD] [--assunto TEXTO] [--assunto-codigo COD] \
  [--orgao TEXTO] [--grau G1|G2|JE|TR|SUP] \
  [--de DD/MM/AAAA] [--ate DD/MM/AAAA] \
  [--recentes] [--tamanho N] [--tribunal tjro] [--json]
```

Contar e agregar:

```bash
python scripts/datajud.py contar --classe 1116 --de 01/01/2025 --ate 31/12/2025
python scripts/datajud.py facetas --por classe
python scripts/datajud.py facetas --classe 1116 --por orgao --limite 10
```

Use `--tribunal stj|stf|trf1|tjsp|...` quando necessário. O padrão é TJRO.

## Escolha econômica do modo

- **“qual o andamento?”** → `processo`;
- **“quantos?”** → `contar`;
- **“quais?”** → `buscar`;
- **“como se distribuem?”** → `facetas`;
- **“qual o código da classe/assunto?”** → `codigos`.

Não faça `buscar` grande para depois contar localmente quando `contar` responde
sem transferir o corpus.

## Composição com juris-tjro

DataJud e JURIS são complementares, não concorrentes.

Um fluxo útil para caso do TJRO pode ser:

```text
DataJud: localizar processo/grau/movimento/data
→ JURIS: localizar o documento correspondente e ler o teor
→ análise: separar o que veio do metadata do que veio do texto
```

Quando apresentar uma conclusão composta, mantenha a proveniência explícita:
“DataJud registra movimento X em data Y; o inteiro teor no JURIS afirma Z”. Não
fundir as duas evidências numa frase sem origem.

## Armadilhas que continuam load-bearing

O script já trata:

- HTTP 429 e `es_rejected_execution_exception` em HTTP 200;
- `track_total_hits: true` para não saturar contagens em 10.000;
- `.keyword` em `grau`/campos textuais de agregação;
- datas de ajuizamento `AAAAMMDDHHMMSS`;
- múltiplos documentos do mesmo CNJ por grau;
- filtragem de assuntos vizinhos em `codigos`;
- chave pública do CNJ.

Se houver HTTP 401, confira a chave pública atual na documentação oficial do
DataJud antes de concluir que o serviço caiu.

## Como apresentar

Sintetize. Para um processo, destaque apenas eventos que mudam o estado útil:
distribuição, decisão, sentença, remessa, julgamento, trânsito, baixa e outros
marcos pertinentes ao pedido.

Para listas/estatísticas, mostre o recorte e a dimensão usada. Não despeje JSON
nem centenas de movimentos.

Sempre deixe claro quando a resposta é **metadado oficial sem inteiro teor**.

## Definition of Done

A consulta termina quando:

- a pergunta foi resolvida pelo modo mais econômico;
- o tribunal/grau/período usados estão claros quando relevantes;
- movimentos irrelevantes não ocupam a resposta;
- nenhuma conclusão de fundamento foi inferida de metadata;
- quando teor se tornou necessário, a investigação foi roteada para a fonte
  correta;
- em respostas compostas, metadata e teor permanecem distinguíveis por
  proveniência.

A skill é bem-sucedida quando responde rapidamente **onde, quando, quantos e
qual movimento** — e sabe parar antes de fingir saber **por quê**.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
