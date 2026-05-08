import Tipos

/-
  ============================================================
  SAÍDA — APLICAR
  ============================================================

  Módulo estrutural. Define o que constitui aplicação correta
  de precedente. Importado pelos módulos de regime
  (art. 926_cpc.lean e art. 927_cpc.lean), que ancoram a
  obrigatoriedade da partição em seus respectivos dispositivos.

  ANCORAGEM DOGMÁTICA. Os requisitos da aplicação correta
  derivam do art. 489, §1º, V, do CPC: invocação acompanhada
  de identificação dos fundamentos determinantes do precedente
  E demonstração de ajuste do caso àqueles fundamentos.

  ESCOPO. A definição é independente do regime de vinculação:
  aplica-se tanto a precedente do próprio tribunal (art. 926)
  quanto a precedente vinculante de tribunal superior (art. 927).
-/

namespace Saidas.Aplicar

open Comum

/- ============================================================
   Camada 2 — Predicados estruturais
   ============================================================ -/

/-- A decisão invoca o precedente como fundamento. -/
axiom InvocaPrecedente : Decisao → Precedente → PEstadoAp

/-- A decisão identifica os fundamentos determinantes do
    precedente (parte da exigência do art. 489, §1º, V, CPC). -/
axiom IdentificaFundamentosDeterminantes : Decisao → Precedente → PEstadoAp

/-- A decisão demonstra que o caso sob julgamento se ajusta
    aos fundamentos determinantes do precedente (parte da
    exigência do art. 489, §1º, V, CPC). -/
axiom DemonstraAjusteAoCaso : Decisao → Precedente → PEstadoAp

/- ============================================================
   Camada 3 — Definição composta
   ============================================================ -/

/-- **Aplicação correta de precedente.** Saída legítima do
    tribunal diante de precedente. Requer cumulativamente:
    invocação, identificação dos fundamentos determinantes,
    demonstração de ajuste. -/
def AplicaCorretamente (d : Decisao) (p : Precedente) : PEstadoAp :=
    InvocaPrecedente d p ∧
    IdentificaFundamentosDeterminantes d p ∧
    DemonstraAjusteAoCaso d p

/- ============================================================
   Camada 4 — Lemas de utilidade
   ============================================================ -/

/-- Aplicação correta requer invocação. -/
theorem aplica_implica_invoca :
    ∀ (d : Decisao) (p : Precedente),
      AplicaCorretamente d p → InvocaPrecedente d p := by
  intEstadoAs d p h
  exact h.1

/-- Aplicação correta requer identificação dos fundamentos. -/
theorem aplica_implica_identifica :
    ∀ (d : Decisao) (p : Precedente),
      AplicaCorretamente d p → IdentificaFundamentosDeterminantes d p := by
  intEstadoAs d p h
  exact h.2.1

/-- Aplicação correta requer demonstração de ajuste. -/
theorem aplica_implica_ajuste :
    ∀ (d : Decisao) (p : Precedente),
      AplicaCorretamente d p → DemonstraAjusteAoCaso d p := by
  intEstadoAs d p h
  exact h.2.2

end Saidas.Aplicar
