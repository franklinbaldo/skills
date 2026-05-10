# Fase 4 — Síntese de Derrotas

## Princípio crítico

**Toda derrota marcada deve referenciar:**
- **(a)** o teorema Lean que a sustenta formalmente, e
- **(b)** a ficha qualitativa da Fase 3.

Marcação sem (a) é especulação. Marcação sem (b) é Lean tomado como oráculo.
Derrotas válidas requerem ambos.

## Template de tabela de derrotas

| Atacante | Atacado | Tipo | Teorema Lean | Ref. Fase 3 | Resultado |
|---|---|---|---|---|---|
| P1 | A1 (Warrant) | `ataque_1_nome` | §Teorema 1 | A1 DERROTADO |
| P2 | A1 (Claim) | `ataque_2_nome` | §Teorema 2 | A1 DERROTADO (confirma) |
| P3 | A1 (aplicação) | `ataque_3_nome` | §Teorema 3 | A1 DERROTADO (confirma) |

Para ataques descartados na Fase 3, incluir linha com resultado "descartado
na Fase 3" e referência à razão (sem teorema Lean na coluna).

## Template de grafo resolutivo Mermaid

```mermaid
graph LR
    A1["A1: [título] ❌ DERROTADO"]
    A2["A2: [título] (cai por arrasto)"]
    P1["P1: [título] ✓"]
    P2["P2: [título] ✓"]

    P1 -->|derrota Warrant| A1
    P2 -->|derrota Claim| A1
    A2 -.->|suportava| A1
```

Convenção: `❌` para derrotado, `✓` para sobrevivente, `(cai por arrasto)`
para pacote instrumental cujo suporte central foi derrotado. Arestas cheias
para ataques vitoriosos; tracejadas para suporte instrumental.

## Síntese argumentativa

Após a tabela e o grafo, redigir síntese com três componentes:

1. **Argumentos derrotados**: listar A* derrotados e o ângulo principal de
   cada derrota (Warrant / Claim / Data / aplicação / Rebuttal).
2. **Argumentos sobreviventes**: A* sem derrota marcada e a razão (sem
   atacante, ou atacante descartado na Fase 3).
3. **Cobertura conjunta dos P* vitoriosos**: os ataques que sobreviveram são
   suficientes para sustentar o pedido da peça? Há lacunas?

## Tratamento de ataques sem teorema Lean (caminho excepcional)

Se um ataque do grafo Argdown (Fase 1) foi considerado sólido na Fase 3 mas
o teorema Lean correspondente não compilou (por razão técnica, não por falha
dogmática):

- **Não marcar como derrota na tabela principal**
- Incluir nota de rodapé: "ataque P* tem sustentação dogmática sólida
  (Fase 3, §X), mas o teorema Lean não foi concluído — derrota não marcada
  formalmente"
- Avaliar se o caminho informal é suficiente para a Fase 5 ou se requer
  novo ciclo da Fase 2

Este caminho excepcional deve ser raro. Se vários ataques caem aqui, o
problema está nas fases anteriores.

## Heurística de revisão final

Antes de passar à Fase 5, verificar:

- [ ] Toda derrota na tabela tem referência a teorema Lean e a parágrafo da Fase 3?
- [ ] O grafo Mermaid é consistente com a tabela?
- [ ] Argumentos instrumentais que "caem por arrasto" estão identificados como
  tal (não como derrotados diretamente)?
- [ ] A síntese responde: os ataques sobreviventes cobrem o pedido da peça?

## Output esperado

- Tabela de derrotas com referências cruzadas
- Grafo resolutivo Mermaid
- Síntese argumentativa (três componentes)
- Recomendações para a Fase 5: quais ataques liderar, quais subsumir,
  quais suprimir (triviais ou não sustentados)

O documento serve de insumo para a Fase 5 (tradução forense — a peça).
