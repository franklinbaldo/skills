/-
  ============================================================
  ANÁLISE DO ACÓRDÃO EMBARGADO — pós filtro de trivialidade
  AgInt no ARE 1.589.466/RO
  ============================================================

  REFINAMENTO METODOLÓGICO

  Os exercícios anteriores formalizaram exaustivamente as
  variantes de cada STEEL_N. Foram úteis como mapeamento do
  espaço argumentativo, mas excessivos para o registro forense:
  steelmanning explícito de leituras óbvias-falsas DIGNIFICA
  o que não merece dignificação. Em peça, ofende o leitor
  versado.

  Aqui aplica-se o **filtro de trivialidade** antes da
  formalização. Leituras incompatíveis com pressupostos
  sistêmicos são descartadas em comentário. Sobram apenas:
    - leituras tautológicas (passam o §1º III check) com
      antecedentes que podem ou não realizar-se nos fatos
    - steelmans dignos (look defensible até o §1º III check)

  Análogo matemático: `[Field K]` opera como pressuposto, não
  como tese. O Lean da peça vive sob o mesmo regime.

  RESULTADO PARA ALICE

  Dos onze steelmans antes formalizados, apenas DOIS sobrevivem
  ao filtro como dignos de exame: V2d (Súmula 280, mera menção)
  e V3c (precedentes, padrão estrutural). Três outros são
  tautológicos e merecem registro factual breve: V1d, V2b, V3b.
  Os seis restantes (V1a, V1b, V1c, V2a, V2c, V3a) foram
  descartados.
-/

namespace AlicePostFiltro

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

axiom Caso : Type
axiom Precedente : Type
axiom Decisao : Type

/- ============================================================
   Camada 2 — Predicados
   ============================================================ -/

axiom DireitoLocal : Caso → Prop
axiom AplicaPrecedente : Caso → Precedente → Prop
axiom Fundamentada : Decisao → Prop

axiom AplicaECArt3 : Caso → Prop
axiom FundamentoDeterminanteEmDireitoLocal : Caso → Prop
axiom MencionaLeiEstadualEmQualquerFuncao : Caso → Prop
axiom MesmaMateria : Caso → Caso → Prop
axiom CompartilhamPadraoEstrutural : Caso → Caso → Prop
axiom CasoDoPrecedente : Precedente → Caso

/- ============================================================
   Camada 3 — Pressupostos sistêmicos
   --
   Estes axiomas operam como `[Field K]` ou `[Nontrivial R]`:
   pressupostos do operar do sistema jurídico brasileiro,
   não teses do exercício. Estão aqui para tornar explícito
   o quadro contextual.
   ============================================================ -/

/-- Existe distinção sistêmica entre interpretação direta de
    norma constitucional e interpretação de direito local
    (art. 102 CF e Súmula 280 lidos conjuntamente). -/
axiom interpretacao_constitucional_distinta_de_local :
    ∀ (c : Caso),
      AplicaECArt3 c → ¬ DireitoLocal c

/-- Existe Tema 139/RG e ele vincula nos termos do art. 927,
    III, do CPC. Em particular: existe ao menos um caso
    paradigmaticamente decidido pelo STF como matéria
    constitucional sobre RPPS estadual. -/
axiom existe_tema_RG_em_RPPS_estadual : Prop
axiom tema_RG_RPPS_existe : existe_tema_RG_em_RPPS_estadual

/-- Precedente exige aderência substantiva (art. 489, §1º, V,
    do CPC). Mera menção tangencial não constitui aplicação
    válida de precedente. -/
axiom aderencia_substantiva_exigida :
    ∀ (c : Caso) (p : Precedente),
      ¬ MesmaMateria c (CasoDoPrecedente p) →
      ¬ AplicaPrecedente c p

/- ============================================================
   ============================================================
        LEITURAS DESCARTADAS POR TRIVIALIDADE
   ============================================================
   ============================================================

   Não recebem formalização. Listadas aqui apenas para
   auditoria do espaço argumentativo. Em peça, aparecem
   dispatched em uma frase ou simplesmente não aparecem.

   STEEL_1 (Súmula 279):
     • V1a "qualificação jurídica = reexame probatório"
       — incompatível com a definição mesma da Súmula 279,
         que pressupõe a distinção.
     • V1b "fatos incontroversos + qualificação = reexame"
       — caso particular ainda mais óbvio: leading case da
         distinção é exatamente caso de fatos incontroversos
         (RE 210.917).
     • V1c "RPPS + qualificação = reexame"
       — mesma trivialidade restrita a domínio.

   STEEL_2 (Súmula 280):
     • V2a "aplicação de norma constitucional = direito local"
       — incompatível com art. 102 CF. Discutir equivaleria
         a discutir se o STF tem jurisdição.
     • V2c "RPPS estadual = direito local"
       — incompatível com a existência mesma do Tema 139/RG
         (paradigma do Plenário em RPPS estadual).

   STEEL_3 (intercambialidade de precedentes):
     • V3a "precedentes sobre matérias distintas se aplicam"
       — incompatível com a definição de precedente
         (art. 489, §1º, V).
-/

/- ============================================================
   LEITURAS TAUTOLÓGICAS
   --
   Passam no §1º III check, mas exigem antecedente factual.
   Mencionadas para registro; refutação é factual, não
   estrutural.
   ============================================================ -/

/-- V1d (registro): Súmula 279 incide quando há aspectos
    fáticos residuais. Tautológica. Inerte para Alice
    (acórdão recorrido assenta os fatos textualmente). -/
def V1d_aspectos_residuais : Prop :=
    ∀ c, ¬ FundamentoDeterminanteEmDireitoLocal c → True

/-- V2b (registro): direito local quando há fundamento
    determinante em direito local. Tautológica. Inerte para
    Alice (fundamento é constitucional). -/
def V2b_fundamento_determinante : Prop :=
    ∀ c, FundamentoDeterminanteEmDireitoLocal c → DireitoLocal c

/-- V3b (registro): precedente sobre mesma matéria se aplica.
    Tautológica. Inerte para Alice (matérias distintas:
    aposentadoria especial vs. EC 47). -/
def V3b_mesma_materia : Prop :=
    ∀ (c c' : Caso) (p : Precedente),
      MesmaMateria c c' → CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/- ============================================================
   STEELMANS DIGNOS — recebem formalização e refutação
   ============================================================ -/

/-- **V2d** — leitura mais deferente possível para a Súmula
    280 que ainda merece exame: mera menção a legislação
    estadual no acórdão recorrido qualifica o caso. -/
def V2d : Prop :=
    ∀ c, MencionaLeiEstadualEmQualquerFuncao c → DireitoLocal c

/-- **V3c** — leitura mais deferente possível para a
    aplicação de precedentes que ainda merece exame:
    compartilhamento de padrão estrutural autoriza
    transposição. -/
def V3c : Prop :=
    ∀ (c c' : Caso) (p : Precedente),
      CompartilhamPadraoEstrutural c c' →
      CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/- Camada 5 — Casos paradigmáticos opostos para refutação -/

/-- Caso paradigma do RE 1.518.690-ED-AgR — citado pelo
    próprio acórdão embargado. -/
axiom caso_RE_1518690 : Caso
axiom RE_1518690_aplica_ec : AplicaECArt3 caso_RE_1518690
axiom RE_1518690_menciona_lei_estadual :
    MencionaLeiEstadualEmQualquerFuncao caso_RE_1518690

/-- Precedente estranho com matéria distinta do caso central. -/
axiom caso_central : Caso
axiom precedente_estranho : Precedente
axiom estranho_padrao_compartilhado :
    CompartilhamPadraoEstrutural caso_central
      (CasoDoPrecedente precedente_estranho)
axiom estranho_materia_distinta :
    ¬ MesmaMateria caso_central (CasoDoPrecedente precedente_estranho)

/- ============================================================
   §1º III CHECK — aplicado aos dois steelmans dignos
   ============================================================ -/

/-- **V2d viola §1º III.** Aplicada ao RE 1.518.690 (que
    menciona legislação estadual em função instrumental e
    foi decidido pelo STF como matéria constitucional),
    derivaria conclusão contrária à decidida. -/
theorem V2d_viola_par1_III : V2d → False := by
  intro h_v2d
  have h_dl : DireitoLocal caso_RE_1518690 :=
    h_v2d caso_RE_1518690 RE_1518690_menciona_lei_estadual
  have h_n_dl : ¬ DireitoLocal caso_RE_1518690 :=
    interpretacao_constitucional_distinta_de_local
      caso_RE_1518690 RE_1518690_aplica_ec
  exact h_n_dl h_dl

/-- **V3c viola §1º III.** Compartilhamento de padrão
    estrutural sem aderência substantiva contradiz o
    pressuposto sistêmico de que precedente exige aderência
    (art. 489, §1º, V). -/
theorem V3c_viola_par1_III : V3c → False := by
  intro h_v3c
  have h_aplica : AplicaPrecedente caso_central precedente_estranho :=
    h_v3c caso_central (CasoDoPrecedente precedente_estranho)
      precedente_estranho estranho_padrao_compartilhado rfl
  have h_n_aplica : ¬ AplicaPrecedente caso_central precedente_estranho :=
    aderencia_substantiva_exigida caso_central precedente_estranho
      estranho_materia_distinta
  exact h_n_aplica h_aplica

/- ============================================================
   TEOREMA FINAL
   ============================================================ -/

/-- **Síntese.** Após filtro de trivialidade, os únicos
    steelmans dignos do acórdão embargado (V2d e V3c) caem
    uniformemente por §1º III. A peça pode unificar a
    refutação em um único argumento estrutural, sem
    desperdiçar prosa em leituras que não merecem ser tidas
    por sérias. -/
theorem nenhum_steelman_digno_sobrevive :
    (V2d ∨ V3c) → False := by
  intro h
  rcases h with h_d | h_c
  · exact V2d_viola_par1_III h_d
  · exact V3c_viola_par1_III h_c

#print axioms V2d_viola_par1_III
#print axioms V3c_viola_par1_III
#print axioms nenhum_steelman_digno_sobrevive

end AlicePostFiltro
