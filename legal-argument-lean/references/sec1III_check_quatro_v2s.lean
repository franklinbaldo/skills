/-
  ============================================================
  §1º III CHECK APLICADO AOS QUATRO STEELMANS — STEEL_2
  ============================================================

  HIPÓTESE METODOLÓGICA

  No exercício anterior (`steelmanning_exaustivo_STEEL2.lean`)
  refutaram-se as quatro versões V2a, V2b, V2c, V2d por
  estratégias distintas:

    V2a → contradição lógica (com RE 1.518.690)
    V2b → inertness factual (precondition falha)
    V2c → reductio (Tema 139/RG)
    V2d → violação ao art. 489, §1º, V (mera menção ≠ FD)

  Pergunta metodológica: aplicando o §1º III check ANTES das
  outras estratégias, quantas dessas refutações se reduzem ao
  mesmo argumento estrutural — universalização vazia?

  RESULTADO

  Três dos quatro steelmans caem uniformemente por §1º III:

    V2a viola §1º III  (universalizável → deriva False)
    V2b passa §1º III  (não-universalizável; é tautológica)
    V2c viola §1º III  (universalizável → deriva False)
    V2d viola §1º III  (universalizável → deriva False)

  V2b sobrevive ao check porque a precondition
  (FundamentoDeterminanteEmDireitoLocal) é distintiva: o
  axioma classifica diferentemente casos com e sem
  fundamento determinante local. Mas V2b já era inerte para
  Alice por motivo factual independente.

  CONSEQUÊNCIA PARA A PEÇA

  Em vez de quatro estratégias distintas — uma por
  steelman —, a peça pode usar um único argumento estrutural
  (universalização) para derrubar três dos quatro, e
  observar que o quarto é inócuo. Texto mais sucinto e
  conceitualmente mais forte: o defeito da fundamentação não
  é específico, é estrutural.
-/

namespace Sec1IIICheckQuatroV2s

/- ============================================================
   Camada 1 — Tipos e premissas
   ============================================================ -/

axiom Caso : Type

axiom AplicaECArt3 : Caso → Prop
axiom DireitoLocal : Caso → Prop
axiom FundamentoDeterminanteEmDireitoLocal : Caso → Prop
axiom EnvolveRPPSEstadual : Caso → Prop
axiom MencionaLeiEstadualEmQualquerFuncao : Caso → Prop

/- ============================================================
   Camada 2 — As quatro versões steelmanned de STEEL_2
   ============================================================ -/

def V2a : Prop := ∀ c, AplicaECArt3 c → DireitoLocal c
def V2b : Prop := ∀ c, FundamentoDeterminanteEmDireitoLocal c → DireitoLocal c
def V2c : Prop := ∀ c, EnvolveRPPSEstadual c → DireitoLocal c
def V2d : Prop := ∀ c, MencionaLeiEstadualEmQualquerFuncao c → DireitoLocal c

/- ============================================================
   Camada 5 — Casos paradigmáticos opostos
   --
   Para cada steelman A → DireitoLocal, identifica-se um caso
   c* tal que A(c*) é verdadeiro e DireitoLocal(c*) é
   manifestamente falso. Bastando UM contraexemplo para a
   refutação por §1º III.
   ============================================================ -/

/-- Caso paradigma do RE 1.518.690-ED-AgR — citado pelo
    próprio acórdão embargado. Aplica art. 3º EC 47 e foi
    decidido como matéria constitucional, não direito local. -/
axiom caso_RE_1518690 : Caso
axiom RE_1518690_aplica_ec : AplicaECArt3 caso_RE_1518690
axiom RE_1518690_nao_eh_local : ¬ DireitoLocal caso_RE_1518690
axiom RE_1518690_menciona_lei_estadual :
    MencionaLeiEstadualEmQualquerFuncao caso_RE_1518690

/-- Caso paradigma do Tema 139/RG (RE 590.260, Lewandowski,
    Plenário, j. 24.06.2009). Versa sobre RPPS estadual e
    menciona legislação estadual (típico de matérias de
    RPPS), mas foi decidido como matéria constitucional pelo
    Plenário do STF — não direito local. -/
axiom caso_Tema_139 : Caso
axiom Tema_139_envolve_RPPS_estadual : EnvolveRPPSEstadual caso_Tema_139
axiom Tema_139_menciona_lei_estadual :
    MencionaLeiEstadualEmQualquerFuncao caso_Tema_139
axiom Tema_139_nao_eh_local : ¬ DireitoLocal caso_Tema_139

/- ============================================================
   §1º III CHECK — uniformemente aplicado
   ============================================================ -/

/-- **V2a viola §1º III.** Universalizável: aplicado ao caso
    do RE 1.518.690 (que aplica EC art. 3 e foi decidido como
    matéria constitucional pelo STF), deriva conclusão
    contrária à decidida. -/
theorem V2a_viola_par1_III : V2a → False := by
  intro h
  exact RE_1518690_nao_eh_local
    (h caso_RE_1518690 RE_1518690_aplica_ec)

/-- **V2c viola §1º III.** Universalizável: aplicado ao caso
    do Tema 139/RG (envolve RPPS estadual e foi decidido como
    matéria constitucional pelo Plenário), deriva conclusão
    contrária. -/
theorem V2c_viola_par1_III : V2c → False := by
  intro h
  exact Tema_139_nao_eh_local
    (h caso_Tema_139 Tema_139_envolve_RPPS_estadual)

/-- **V2d viola §1º III.** Universalizável: aplicado tanto ao
    caso do RE 1.518.690 quanto ao do Tema 139/RG (ambos
    mencionam legislação estadual em função instrumental e
    foram decididos como matéria constitucional), deriva
    conclusão contrária. -/
theorem V2d_viola_par1_III : V2d → False := by
  intro h
  exact RE_1518690_nao_eh_local
    (h caso_RE_1518690 RE_1518690_menciona_lei_estadual)

/-- Variante do mesmo argumento via Tema 139, demonstrando
    que V2d cai sob *múltiplos* contraexemplos — o que
    fortalece a caracterização de universalização vazia. -/
theorem V2d_viola_par1_III_via_tema_139 : V2d → False := by
  intro h
  exact Tema_139_nao_eh_local
    (h caso_Tema_139 Tema_139_menciona_lei_estadual)

/-- **V2b passa no §1º III check** — não é universalizável
    de forma vazia.

    Para violar §1º III, V2b precisaria de um caso onde
    `FundamentoDeterminanteEmDireitoLocal` é verdadeiro mas
    `DireitoLocal` é falso. Não há tal caso: por construção,
    se o fundamento determinante é direito local, então o
    caso é decidido por direito local — definição.

    V2b é, portanto, tautológica (ou quase). Distingue
    estruturalmente entre casos com e sem fundamento
    determinante local. NÃO viola §1º III.

    Sua falência se dá por outro motivo: precondition não se
    realiza no caso de Alice (já demonstrado em
    `steelmanning_exaustivo_STEEL2.lean`). -/
theorem V2b_passa_par1_III : True := trivial
-- (declaração simbólica: V2b não tem refutação por §1º III)

/- ============================================================
   TEOREMA UNIFICADOR
   ============================================================ -/

/-- **Refutação unificada por §1º III.**

    Três das quatro versões steelmanned (V2a, V2c, V2d) caem
    por uma única estratégia estrutural: universalização
    vazia. A peça pode unificar a argumentação contra o
    acórdão em um eixo comum: o fundamento implícito do
    acórdão, qualquer que seja sua leitura caridosa entre as
    três versões fortes, é fundamentação universalizável,
    vedada pelo art. 489, §1º, III, do CPC.

    A quarta versão (V2b), única que passa no §1º III check,
    é tautológica e não fornece base para a aplicação da
    Súmula 280 ao caso concreto (precondition factualmente
    inexistente). -/
theorem refutacao_unificada_via_par1_III :
    (V2a ∨ V2c ∨ V2d) → False := by
  intro h
  rcases h with h_a | h_c | h_d
  · exact V2a_viola_par1_III h_a
  · exact V2c_viola_par1_III h_c
  · exact V2d_viola_par1_III h_d

/- ============================================================
   COMPARATIVO ANTES/DEPOIS DO §1º III CHECK
   ============================================================

   ANTES (em `steelmanning_exaustivo_STEEL2.lean`):

     V2a  →  refutada por contradição via RE 1.518.690 +
             3 axiomas estruturais (juris consolidada,
             interpretação constitucional, etc.)
     V2c  →  refutada por reductio com fato sobre
             admissibilidade do Tema 139
     V2d  →  refutada por violação a art. 489 §1º V
             via axioma de ligação

     Três estratégias distintas, três famílias de axiomas.

   DEPOIS (com §1º III check):

     V2a, V2c, V2d  →  uma única estratégia
                       (universalização → False)
     V2b           →  caso especial (inertness)

     Uma estratégia estrutural, refutação aplicável uniforme.

   GANHO: a peça consegue dizer, em um único argumento, que
   a tese implícita do acórdão sobre a Súmula 280 — em
   qualquer leitura caridosa não-tautológica — é
   universalizável de forma vazia, e portanto fundamentação
   defeituosa.
-/

#print axioms V2a_viola_par1_III
#print axioms V2c_viola_par1_III
#print axioms V2d_viola_par1_III
#print axioms refutacao_unificada_via_par1_III

end Sec1IIICheckQuatroV2s
