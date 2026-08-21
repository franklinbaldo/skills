# Fase 1 — Argdown (Decomposição Argumentativa)

## Por que Argdown

Argdown (https://argdown.org) unifica o que nas tradições de Toulmin (1958) e
Dung (1995) ficava distribuído em dois instrumentos separados: representa tanto
a anatomia de cada argumento (claims, premissas, warrants) quanto a topologia
do sistema argumentativo (suporte e ataque entre argumentos). Sintaxe de
linguagem de marcação (Markdown-like), com parser oficial em TypeScript, plugin
VS Code e exportadores para Mermaid, Graphviz, JSON/apx.

Para LLMs é formato natural: estruturado, sem ambiguidade entre anatomia e
topologia, com documentação indexada. O output desta fase alimenta diretamente
a Fase 2 (Lean): a LLM-formalizadora lê o grafo Argdown e deriva um teorema
por linha de ataque.

## Convenção adotada neste pipeline

| Símbolo        | Significado                                          |
| -------------- | ---------------------------------------------------- |
| `[A1: título]` | Claim do acórdão (posição atacada)                   |
| `[P1: título]` | Claim da peça (posição atacante)                     |
| `[D-A1]`       | Data de A1 — base fática                             |
| `[W-A1]`       | Warrant de A1 — regra completa com ressalvas         |
| `<arg-A1>`     | Argumento que reconstrói e sustenta A1               |
| `<arg-P1>`     | Argumento que reconstrói e sustenta P1 (e ataca A\*) |

Ataques: a última linha numerada de `<arg-P*>` com prefixo `-` aponta para
`[A*]` (sintaxe Argdown nativa para ataque entre statements).

Nomear o ângulo do ataque no título do argumento (Warrant / Claim / Data /
aplicação Data→Claim / Rebuttal). Isso informa o tipo de teorema Lean.

## Regra crítica — Warrant completo

**O Warrant (`[W-A*]`) deve ser registrado em sua integralidade, incluindo
ressalvas e exceções.**

Se o acórdão invoca um precedente com ressalva e opera com versão truncada,
o `[W-A*]` registra o Warrant completo. A discrepância entre o Warrant
registrado e o Warrant operado pelo acórdão é a substância do ataque de P\*.

## Gate de qualificação da omissão

Não representar automaticamente toda ausência textual como omissão. Antes de
criar uma claim `[P*: omissão ...]`, responder em ordem:

1. **Enfrentamento expresso:** o argumento foi respondido diretamente? Se sim,
   não há omissão quanto a ele; avaliar erro, incoerência ou insuficiência.
2. **Rejeição implícita:** a estrutura fundamentativa descarta logicamente o
   argumento? Se sim, registrar a inferência e testar sua validade antes de
   classificar como omissão.
3. **Decisividade:** o argumento era capaz, em tese, de infirmar a conclusão?
   Se não, não usar o art. 489, §1º, IV como atalho.
4. **Determinabilidade:** os compromissos já assumidos pelo tribunal determinam
   **univocamente** a resposta ao ponto omitido?
   - `recognitiva`: a integração recupera consequência já determinada;
   - `geratoria`: o tribunal ainda precisa escolher entre respostas compatíveis;
   - `direcionamento_sem_unicidade`: os compromissos orientam, mas não
     determinam uma única resposta; tratar como subtipo geratório.

Anotar claims de omissão com `cognicao: "recognitiva"`, `"geratoria"` ou
`"direcionamento_sem_unicidade"`. Se o material não permite classificar, usar
`cognicao: "pendente"` e levar a dúvida à Fase 3. A classificação descreve a
estrutura cognitiva do saneamento; não cria, por si só, regra autônoma de
admissibilidade.

## Template de arquivo Argdown

```argdown
===
title: [Caso] — Decomposição Argumentativa
===

# Posição do acórdão

[A1: claim central]: Afirmação central do acórdão.

<arg-A1: fundamentação central>

(1) [D-A1]: Fatos e documentos (Data).
(2) [W-A1: warrant]: Regra que conecta Data à Claim — completo, com
     ressalvas. Backing: [autoridade, citação].
----
(3) [A1: claim central]

[A2: claim instrumental]: Claim auxiliar que sustenta A1.
  +> [A1: claim central]

# Posição da peça

[P1: tese embargante]: Claim da peça que ataca A1.

<arg-P1: ângulo do ataque — ex: Warrant truncado>

(1) [W-A1: warrant]
(2) [F-P1]: Fato específico do caso que aciona a ressalva ou revela a
     omissão.
----
(3) [P1: tese embargante]
  - [A1: claim central]
```

## Anotações de proveniência e status

No pipeline complexo, claims de dados (`[D-*]`, `[F-*]`, `[W-*]`) devem ser
anotadas com proveniência, status e localização usando a sintaxe de dados do
Argdown (`{ }`). No workflow direto, a anotação pode ser abreviada apenas
quando a fonte estiver transcrita inequivocamente no docstring Lean.
Essas anotações são lidas pela LLM-formalizadora ao produzir axiomas da
Camada 5 no Lean e pela Fase 3 (análise subjetiva) para avaliar ônus
argumentativo.

**Chaves:**

| Chave    | Valores           | Significado                                                              |
| -------- | ----------------- | ------------------------------------------------------------------------ |
| `prov`   | `endogena`        | Tribunal chegou à conclusão por raciocínio próprio                       |
|          | `fonte_declarada` | Documento cita explicitamente a origem                                   |
|          | `fonte_inferida`  | Pressuposto provavelmente de documento anterior não citado               |
|          | `confirmada`      | Fonte inferida confirmada pelo procurador                                |
|          | `pendente`        | Não determinado — estado honesto, não trava o pipeline                   |
| `fonte`  | string livre      | Identificação da fonte quando `prov=fonte_declarada` ou `fonte_inferida` |
| `local`  | string livre      | Página, folha, ID, evento, item ou timestamp exato                       |
| `autor`  | string livre      | Pessoa, parte, órgão ou tribunal responsável pela afirmação              |
| `status` | `necessaria`      | Sem esta claim o efeito do ato não ocorreria                             |
|          | `contingente`     | Presente no documento mas não load-bearing — "dito de passagem"          |
|          | `pendente`        | Não determinável com o material disponível                               |

**Exemplo anotado:**

```argdown
[F-P1: cargo originário de M.B.] {prov: "fonte_declarada", fonte: "Decreto 7.999/1997", local: "art. 1º", autor: "Estado de Rondônia", status: "necessaria"}:
O cargo originário de M.B. é Especialista em Supervisão Escolar.

[D-P4: regimes constitucionais distintos] {prov: "fonte_inferida", fonte: "apelação — a confirmar", status: "pendente"}:
A ADI 3.772 decidiu no contexto do art. 37, XVI, CF; a LC 680/2012
opera no art. 40, §5º, CF.
```

**Claims com `pendente`** geram pergunta ao formalizante: "o acórdão
pressupõe [X] — você tem o documento de origem para confirmar?" O
pipeline continua; o status é registrado e avaliado na Fase 3.

**Claims `contingente`** de documentos anteriores que se propagam ao
acórdão são argumento processual: o acórdão está ancorado em fundamento
que não era necessário na decisão recorrida.

As anotações correspondem diretamente aos tipos `ClaimMeta.Proveniencia`
e `ClaimMeta.StatusClaim` em `references/ClaimMeta.lean`.

## Heurísticas

1. **Warrant completo?** Se o precedente tem ressalva, ela está em `[W-A*]`?
   Discrepância entre Warrant registrado e Warrant operado pelo acórdão = núcleo
   do ataque de P\*.

2. **Tipo de ataque?** Identificar em cada `<arg-P*>`: Warrant / Claim / Data /
   aplicação Data→Claim / Rebuttal não examinado. Nomear no título do argumento.

3. \**A* instrumentais?\*\* Claims A\* sem atacantes diretos que sustentam A1
   devem ser explicitadas com `+>`. Caem por arrasto se A1 for derrotado —
   mas isso é conclusão da Fase 4, não desta fase.

4. \**Independência de P*?\*\* P\* que atacam A1 por ângulos distintos são
   argumentos independentes, mesmo que apontem para a mesma claim.

5. **Anotar proveniência nas claims de dados.** Especialmente: claims com
   `prov: "fonte_inferida"` são candidatos a verificação antes de protocolar;
   claims com `status: "contingente"` na fonte original são argumento
   processual se propagadas ao acórdão.

## Output esperado

Um arquivo `.argdown` (ou bloco `argdown` em Markdown) com:

- Todas as claims do acórdão (A\*), instrumentais incluídas
- Todas as claims da peça (P\*), uma por vício identificado
- Todos os argumentos `<arg-A*>` e `<arg-P*>`, com Warrants completos
- Claims de dados anotadas com `prov`, `fonte`, `local`, `autor` e `status`
- Claims de omissão anotadas com `cognicao`

O arquivo serve de insumo direto para a Fase 2 (Lean). Cada linha de ataque
na topologia Argdown corresponde a um teorema candidato na Fase 2.
