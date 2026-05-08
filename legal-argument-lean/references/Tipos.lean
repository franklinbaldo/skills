/-
  ============================================================
  TIPOS COMUNS — fundação da biblioteca de saídas
  ============================================================

  Este módulo define os tipos básicos usados pelos módulos de
  saída (Aplicar, Distinguir, Superar) e pelos módulos de
  regime (art. 926, art. 927). Importado por todos.

  Mantido enxuto deliberadamente: apenas tipos opacos, sem
  predicados nem normas. Permite que diferentes módulos
  trabalhem sobre os mesmos `Decisao`, `Precedente` etc.
-/

namespace Comum

axiom Decisao : Type
axiom Precedente : Type
axiom Caso : Type
axiom Tribunal : Type
axiom Servidor : Type
axiom Cargo : Type

end Comum
