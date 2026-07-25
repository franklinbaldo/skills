# Fase 2 — Briefing Lean (LLM-formalizadora)

## Regra dura

**Nunca ajustar axiomas para forçar compilação.**

Se um teorema não compila, o problema não está no Lean — está na análise da
Fase 1 (Argdown). Voltar à Fase 1 e revisar. Axiomas ajustados para fazer o
proof checker aceitar a conclusão contaminam a Fase 3 (análise subjetiva) e
invalidam o pipeline inteiro.

## Composição do briefing

O briefing para a LLM-formalizadora (que pode ser uma sessão separada de
contexto) contém:

1. **Material original**: acórdão + peça (ou trecho relevante)
2. **Decomposição Argdown** (output da Fase 1): claims A*, claims P*, warrants,
   topologia de ataques

A LLM-formalizadora lê o grafo Argdown e produz o arquivo Lean.

## O que produzir

Um teorema candidato por linha de ataque do grafo Argdown. Para cada teorema:

- **Nome**: `ataque_N_[descricao_curta]`
- **Tipo**: a proposição jurídica que se quer estabelecer (ex.: `¬ Fundamentada d`)
- **Axiomas usados**: documentados nos comentários do arquivo Lean
- **Conclusão jurídica**: o que o teorema, se compilar, estabelece em termos dogmáticos

## Estrutura do arquivo Lean — seis camadas

O arquivo Lean deve usar literalmente estes cabeçalhos de comentário:

```lean
/- Camada 1 — Tipos básicos -/
-- Tipos opacos do caso: servidora, cargo, tribunal, decisão, precedente

/- Camada 2 — Predicados opacos -/
-- Qualificações jurídicas não-dedutivas (decididas, não computadas)

/- Camada 3 — Pressupostos sistêmicos -/
-- Operam como contexto do sistema jurídico, não teses do exercício
-- (análogo a [Field K]: coisas que ambos os lados presumem)

/- Camada 4 — Normas e precedentes -/
-- Axiomas-construtor com citação no docstring (/-- ... -/)

/- Camada 5 — Fatos do caso -/
-- Extraídos do acórdão e dos autos; cada axiom com citação da fonte

/- Camada 6 — Teoremas -/
-- Um por ataque identificado na Fase 1
```

Imports obrigatórios (ordem topológica):

```lean
import Tipos
import ClaimMeta       -- obrigatório no pipeline complexo
import Saidas.Aplicar
import Saidas.Distinguir
import Saidas.Superar
import art_927_cpc     -- se o caso envolve precedente vinculante
import art_926_cpc     -- se o caso envolve jurisprudência do próprio tribunal
import art_1022_cpc    -- se o caso envolve cabimento de ED
import art_489_cpc     -- para vícios de fundamentação em geral
import art_10_cpc      -- se há decisão surpresa
import art_5_e_6_cpc   -- se há boa-fé objetiva ou cooperação
```

Importar apenas os módulos relevantes ao caso.

No pipeline complexo, cada axioma da Camada 5 deve ter axiomas-companheiros
`TemProveniencia`, `TemStatus` e `TemLocalizador`. A ficha não altera a prova,
mas impede que `#print axioms` seja lido sem contexto epistemológico. O
cabeçalho do arquivo também deve registrar o commit das bibliotecas e os
rótulos de estabilidade conforme `references/VERSIONING.md`.

## Auditoria automática

Encerrar **sempre** com `#print axioms` para cada teorema:

```lean
#print axioms ataque_1_nome
#print axioms ataque_2_nome
-- ...
```

O output do `#print axioms` é o insumo principal da Fase 3. Não pular.

## Compilação

```bash
# Da raiz do repositório:
cd legal-argument-lean/pipeline/[nome_caso]
LEAN_PATH=../../references lean 02_lean_fase2.lean
```

O arquivo deve compilar limpo (sem `sorry`, sem erros). Se não compilar,
reportar o erro e voltar à Fase 1 antes de continuar.
