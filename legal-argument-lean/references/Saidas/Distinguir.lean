import Tipos

/-
  ============================================================
  SAÍDA — DISTINGUIR (distinguishing)
  ============================================================

  Módulo estrutural. Define o que constitui distinção correta
  de precedente.

  ANCORAGEM DOGMÁTICA. O distinguishing é a alternativa
  legítima à aplicação quando o caso sob julgamento difere,
  em seus fundamentos relevantes, do caso paradigma. O
  art. 489, §1º, VI, CPC exige que a decisão que "deixa de
  seguir" precedente demonstre a distinção (ou a superação,
  cf. módulo Saidas.Superar).

  ESTRUTURA INTERNA. Distinguir não basta dizer "esse caso é
  diferente". Exige:
    (a) identificação dos fundamentos determinantes do
        precedente (premissa: para diferir, é preciso saber
        de quê);
    (b) demonstração concreta de que o caso sob julgamento
        não satisfaz aqueles fundamentos.

  ESCOPO. Independente do regime: o distinguishing tem
  estrutura idêntica para precedente do próprio tribunal
  (art. 926) e para precedente vinculante (art. 927). Nesse
  ponto não há qualificação dogmática.
-/

namespace Saidas.Distinguir

open Comum

variable (d : Decisao) (p : Precedente)

/- ============================================================
   Camada 2 — Predicados estruturais
   ============================================================ -/

/-- A decisão demonstra distinção (distinguishing) entre o
    caso sob julgamento e o caso paradigma do precedente. -/
axiom DemonstraDistincao : Decisao → Precedente → Prop

/-- A decisão identifica os fundamentos determinantes do
    precedente — pré-requisito do distinguishing genuíno
    (não se distingue do que não se identificou). -/
axiom IdentificaFundamentosDoPrecedente : Decisao → Precedente → Prop

/-- A decisão demonstra concretamente que o caso sob julgamento
    não satisfaz os fundamentos determinantes do precedente. -/
axiom MostraDiferencaSubstantivaNoCaso : Decisao → Precedente → Prop

/- ============================================================
   Camada 3 — Definição composta
   ============================================================ -/

/-- **Distinção correta de precedente.** Saída legítima do
    tribunal diante de precedente cuja ratio não captura o
    caso. Requer cumulativamente: identificação dos fundamentos
    do precedente, demonstração de diferença substantiva no
    caso, declaração formal da distinção. -/
@[simp]
def DistingueCorretamente (d : Decisao) (p : Precedente) : Prop :=
    DemonstraDistincao d p ∧
    IdentificaFundamentosDoPrecedente d p ∧
    MostraDiferencaSubstantivaNoCaso d p

/- ============================================================
   Camada 4 — Lemas de utilidade
   ============================================================ -/

/-- Distinção correta requer identificação dos fundamentos. -/
theorem distingue_implica_identifica :
    DistingueCorretamente d p → IdentificaFundamentosDoPrecedente d p := by
  intro h; exact h.2.1

/-- Distinção correta requer demonstração de diferença. -/
theorem distingue_implica_diferenca :
    DistingueCorretamente d p → MostraDiferencaSubstantivaNoCaso d p := by
  intro h; exact h.2.2

end Saidas.Distinguir
