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

| Símbolo | Significado |
|---|---|
| `[A1: título]` | Claim do acórdão (posição atacada) |
| `[P1: título]` | Claim da peça (posição atacante) |
| `[D-A1]` | Data de A1 — base fática |
| `[W-A1]` | Warrant de A1 — regra completa com ressalvas |
| `<arg-A1>` | Argumento que reconstrói e sustenta A1 |
| `<arg-P1>` | Argumento que reconstrói e sustenta P1 (e ataca A*) |

Ataques: a última linha numerada de `<arg-P*>` com prefixo `-` aponta para
`[A*]` (sintaxe Argdown nativa para ataque entre statements).

Nomear o ângulo do ataque no título do argumento (Warrant / Claim / Data /
aplicação Data→Claim / Rebuttal). Isso informa o tipo de teorema Lean.

## Regra crítica — Warrant completo

**O Warrant (`[W-A*]`) deve ser registrado em sua integralidade, incluindo
ressalvas e exceções.**

Se o acórdão invoca um precedente com ressalva e opera com versão truncada,
o `[W-A*]` registra o Warrant completo. A discrepância entre o Warrant
registrado e o Warrant operado pelo acórdão é a substância do ataque de P*.

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

## Heurísticas

1. **Warrant completo?** Se o precedente tem ressalva, ela está em `[W-A*]`?
   Discrepância entre Warrant registrado e Warrant operado pelo acórdão = núcleo
   do ataque de P*.

2. **Tipo de ataque?** Identificar em cada `<arg-P*>`: Warrant / Claim / Data /
   aplicação Data→Claim / Rebuttal não examinado. Nomear no título do argumento.

3. **A* instrumentais?** Claims A* sem atacantes diretos que sustentam A1
   devem ser explicitadas com `+>`. Caem por arrasto se A1 for derrotado —
   mas isso é conclusão da Fase 4, não desta fase.

4. **Independência de P*?** P* que atacam A1 por ângulos distintos são
   argumentos independentes, mesmo que apontem para a mesma claim.

## Output esperado

Um arquivo `.argdown` (ou bloco `argdown` em Markdown) com:

- Todas as claims do acórdão (A*), instrumentais incluídas
- Todas as claims da peça (P*), uma por vício identificado
- Todos os argumentos `<arg-A*>` e `<arg-P*>`, com Warrants completos

O arquivo serve de insumo direto para a Fase 2 (Lean). Cada linha de ataque
na topologia Argdown corresponde a um teorema candidato na Fase 2.
