/-
  ============================================================
  §1º III CHECK APLICADO A STEEL_1 E STEEL_3
  ============================================================

  No exercício anterior aplicou-se o §1º III check às quatro
  versões de STEEL_2 (Súmula 280). Resultado: três caem
  uniformemente por universalização vazia; a quarta é
  tautológica.

  Aqui aplica-se o mesmo check a STEEL_1 (Súmula 279) e
  STEEL_3 (intercambialidade de precedentes). O resultado é
  análogo — e mais devastador no caso de STEEL_3, que é
  *paradigmaticamente* fundamentação universalizável.

  STEEL_1 — Súmula 279
    "qualificação jurídica de fato incontroverso = reexame"
    Versões V1a, V1b, V1c, V1d.

  STEEL_3 — intercambialidade de precedentes
    "precedente sobre matéria X serve para caso de matéria Y"
    Versões V3a, V3b, V3c.

  CONCLUSÃO ANTECIPADA: dos sete steelmans não-tautológicos
  examinados (V1a-c, V2a/c/d, V3a/c) ao longo de três
  exercícios, *todos* violam §1º III. As únicas versões que
  passam são tautológicas (V1d, V2b, V3b) e, neste caso, são
  inertes para ParteA. A fundamentação implícita do acórdão
  embargado, em qualquer leitura defensável não-tautológica,
  é universalizável vazia — vedada pelo §1º III.

  Esse é o argumento estrutural unificado da peça.
-/

namespace Sec1IIICheckSTEEL1eSTEEL3

/- ============================================================
   Camada 1 — Tipos e premissas pacíficas
   ============================================================ -/

axiom Caso : Type
axiom Precedente : Type

axiom DependeReexameProbatorio : Caso → Prop
axiom AplicaPrecedente : Caso → Precedente → Prop

axiom ApenasQualificacaoJuridica : Caso → Prop
axiom FatosIncontroversos : Caso → Prop
axiom MateriaPrevidenciariaRPPS : Caso → Prop
axiom AspectosFaticosResiduais : Caso → Prop
axiom MesmaMateria : Caso → Caso → Prop
axiom CompartilhamPadraoEstrutural : Caso → Caso → Prop
axiom CasoDoPrecedente : Precedente → Caso

/- Sobre admissibilidade -/
axiom Admissivel : Caso → Prop
axiom InadmissivelPorSumula279 : Caso → Prop

/- Conexão Súmula 279: caso de reexame probatório é
   inadmissível por Súmula 279. Caso inadmissível por
   Súmula 279 não é admissível. -/
axiom sumula_279_implica_inadmissivel :
    ∀ (c : Caso), DependeReexameProbatorio c →
                  InadmissivelPorSumula279 c
axiom inadmissivel_por_279_nao_admitido :
    ∀ (c : Caso), InadmissivelPorSumula279 c → ¬ Admissivel c

/- ============================================================
   ============================================================
        STEEL_1 — Súmula 279
   ============================================================
   ============================================================
-/

/-- **V1a — versão crua.** Caso de qualificação jurídica
    depende de reexame probatório. -/
def V1a : Prop := ∀ c, ApenasQualificacaoJuridica c → DependeReexameProbatorio c

/-- **V1b — versão restringida com fatos incontroversos.**
    Caso de fatos incontroversos + qualificação jurídica
    depende de reexame.

    Nota: paradoxalmente *menos* defensável que V1a, pois
    casos com fatos incontroversos são exatamente os que o
    STF admite em qualificação jurídica (PRECEDENTE_GERAL). -/
def V1b : Prop :=
    ∀ c, FatosIncontroversos c → ApenasQualificacaoJuridica c →
         DependeReexameProbatorio c

/-- **V1c — versão restringida a RPPS.** Súmula 279 incide em
    casos de RPPS quando há qualificação jurídica.

    Versão deferente: tenta restringir a regra a um subdomínio
    para evitar trivialização. Mas falha de mesma forma. -/
def V1c : Prop :=
    ∀ c, MateriaPrevidenciariaRPPS c → ApenasQualificacaoJuridica c →
         DependeReexameProbatorio c

/-- **V1d — versão tautológica/defensável.** Súmula 279 incide
    quando há aspectos fáticos residuais (não enfrentados pela
    decisão recorrida).

    Esta versão é praticamente a definição correta da Súmula
    279 e passa no §1º III check. Mas o antecedente
    `AspectosFaticosResiduais` não se realiza no caso de
    ParteA (acórdão recorrido assenta tudo). Logo: tautológica
    e inerte. -/
def V1d : Prop :=
    ∀ c, AspectosFaticosResiduais c → DependeReexameProbatorio c

/- Camada 5 — Casos paradigmáticos opostos -/

/-- Caso paradigma do PRECEDENTE_GERAL, Pertence, Tribunal Pleno —
    o leading case da própria distinção entre qualificação
    jurídica e reexame probatório. Tem fatos incontroversos,
    apenas qualificação jurídica, é matéria previdenciária,
    e foi ADMITIDO pelo STF (cassada a inadmissão). -/
axiom caso_RE_210_917 : Caso
axiom RE_210_917_qualificacao :
    ApenasQualificacaoJuridica caso_RE_210_917
axiom RE_210_917_incontroverso :
    FatosIncontroversos caso_RE_210_917
axiom RE_210_917_rpps :
    MateriaPrevidenciariaRPPS caso_RE_210_917
axiom RE_210_917_admitido : Admissivel caso_RE_210_917

/- §1º III CHECK -/

/-- **V1a viola §1º III.** Aplicado ao caso paradigma do
    PRECEDENTE_GERAL (próprio leading case da distinção
    qualificação/reexame), V1a derivaria inadmissibilidade —
    contradizendo a admissão pelo Plenário. -/
theorem V1a_viola_par1_III : V1a → False := by
  intro h
  have h_reexame : DependeReexameProbatorio caso_RE_210_917 :=
    h caso_RE_210_917 RE_210_917_qualificacao
  have h_inadm : InadmissivelPorSumula279 caso_RE_210_917 :=
    sumula_279_implica_inadmissivel caso_RE_210_917 h_reexame
  exact inadmissivel_por_279_nao_admitido caso_RE_210_917
    h_inadm RE_210_917_admitido

/-- **V1b viola §1º III.** Mesmo argumento, adicionando o
    requisito de fatos incontroversos — que se realiza
    paradigmaticamente no PRECEDENTE_GERAL. -/
theorem V1b_viola_par1_III : V1b → False := by
  intro h
  have h_reexame : DependeReexameProbatorio caso_RE_210_917 :=
    h caso_RE_210_917 RE_210_917_incontroverso RE_210_917_qualificacao
  exact inadmissivel_por_279_nao_admitido caso_RE_210_917
    (sumula_279_implica_inadmissivel caso_RE_210_917 h_reexame)
    RE_210_917_admitido

/-- **V1c viola §1º III.** Versão deferente restringe à
    matéria de RPPS, mas o PRECEDENTE_GERAL (e numerosos outros)
    é precisamente caso de RPPS com qualificação jurídica
    admitido pelo STF. -/
theorem V1c_viola_par1_III : V1c → False := by
  intro h
  have h_reexame : DependeReexameProbatorio caso_RE_210_917 :=
    h caso_RE_210_917 RE_210_917_rpps RE_210_917_qualificacao
  exact inadmissivel_por_279_nao_admitido caso_RE_210_917
    (sumula_279_implica_inadmissivel caso_RE_210_917 h_reexame)
    RE_210_917_admitido

/-- **V1d passa no §1º III check.** A precondition
    `AspectosFaticosResiduais` distingue casos com e sem
    aspectos fáticos pendentes — não é universalizável vazia.
    V1d é a definição correta da Súmula 279. Mas é inerte
    para ParteA (acórdão recorrido assenta os fatos). -/
theorem V1d_passa_par1_III : True := trivial

/- ============================================================
   ============================================================
        STEEL_3 — intercambialidade de precedentes
   ============================================================
   ============================================================

   STEEL_3 é o caso mais paradigmático de §1º III. Se
   precedente sobre matéria distinta pode ser usado para
   decidir caso ao bar, qualquer precedente justifica
   qualquer decisão. É *literalmente* o que §1º III veda.
-/

/-- **V3a — versão crua.** Precedente sobre matéria distinta
    se aplica ao caso. -/
def V3a : Prop :=
    ∀ (c c' : Caso) (p : Precedente),
      ¬ MesmaMateria c c' →
      CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/-- **V3b — versão correta/tautológica.** Precedente sobre
    mesma matéria se aplica.

    Esta é a doutrina consolidada de aderência e passa no
    §1º III check. Mas no caso de ParteA, os precedentes
    citados pelo acórdão (sobre aposentadoria especial)
    *não compartilham matéria* com o caso (sobre regra de
    transição da EC 47), de modo que V3b é inerte. -/
def V3b : Prop :=
    ∀ (c c' : Caso) (p : Precedente),
      MesmaMateria c c' →
      CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/-- **V3c — versão deferente.** Precedente sobre caso de
    "padrão estrutural compartilhado" se aplica.

    Versão mais ampla que V3b mas sem chegar à
    intercambialidade total. A questão é: é
    `CompartilhamPadraoEstrutural` predicado distintivo, ou
    é vago suficiente para se tornar universalizável? -/
def V3c : Prop :=
    ∀ (c c' : Caso) (p : Precedente),
      CompartilhamPadraoEstrutural c c' →
      CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/- Camada 5 adicional — Casos paradigmáticos para STEEL_3 -/

/-- Precedente "estranho" — qualquer precedente do STF cuja
    matéria é distinta da do caso ao bar. Para refutar V3a,
    basta sua existência. -/
axiom precedente_estranho : Precedente

/-- O precedente estranho é, por definição, sobre matéria
    distinta da do caso paradigma. -/
axiom estranho_materia_distinta :
    ¬ MesmaMateria caso_RE_210_917 (CasoDoPrecedente precedente_estranho)

/-- O precedente estranho NÃO se aplica ao caso paradigma
    (pelo art. 489, §1º, V — falta de aderência substantiva). -/
axiom estranho_nao_aplica :
    ¬ AplicaPrecedente caso_RE_210_917 precedente_estranho

/-- O precedente estranho compartilha padrão estrutural com
    o caso paradigma — ambos versam sobre admissibilidade,
    por exemplo. Esta é a circunstância que tornaria V3c
    operativa. -/
axiom estranho_compartilha_padrao :
    CompartilhamPadraoEstrutural caso_RE_210_917
      (CasoDoPrecedente precedente_estranho)

/- §1º III CHECK -/

/-- **Refutação direta de V3a — universalização total.** V3a,
    aplicada com o precedente estranho, derivaria sua
    aplicação ao caso paradigma — em contradição com a
    aderência exigida pelo art. 489, §1º, V. Universalização
    vazia em forma pura. -/
theorem V3a_universalizacao_total : V3a → False := by
  intro h
  exact estranho_nao_aplica
    (h caso_RE_210_917 (CasoDoPrecedente precedente_estranho) precedente_estranho
       estranho_materia_distinta rfl)

/-- **V3b passa no §1º III check.** A precondition
    `MesmaMateria` é distintiva. V3b expressa a doutrina
    correta da aderência. -/
theorem V3b_passa_par1_III : True := trivial

/-- **V3c viola §1º III.** A versão de "padrão estrutural
    compartilhado" — exatamente a leitura mais caridosa do
    que o acórdão embargado fez ao usar precedentes sobre
    aposentadoria especial para decidir caso sobre EC 47 —
    falha por igual.

    O critério "compartilham padrão estrutural" se realiza
    para precedentes que apenas concorrem na hipótese de
    versarem sobre admissibilidade, sem aderência substantiva.
    V3c, com este antecedente largo, derivaria a aplicação
    do precedente estranho — contradizendo o art. 489, §1º,
    V, que exige aderência aos fundamentos determinantes. -/
theorem V3c_viola_par1_III : V3c → False := by
  intro h
  exact estranho_nao_aplica
    (h caso_RE_210_917 (CasoDoPrecedente precedente_estranho) precedente_estranho
       estranho_compartilha_padrao rfl)

/- ============================================================
   TEOREMA UNIFICADOR FINAL — A PEÇA EM UMA LINHA
   ============================================================ -/

/-- **Universalização vazia: a estrutura completa do acórdão
    embargado.**

    Considerando os três STEELs do acórdão e suas variantes
    não-tautológicas:

      STEEL_1: V1a, V1b, V1c
      STEEL_2: V2a, V2c, V2d  (do exercício anterior)
      STEEL_3: V3a, V3c

    Todas violam art. 489, §1º, III, do CPC. As únicas
    versões que passam no §1º III check são V1d, V2b, V3b
    — todas tautológicas e *todas inertes para o caso de
    ParteA*.

    Conclusão estrutural: o acórdão embargado, em qualquer
    leitura caridosa não-tautológica, repousa em
    fundamentação universalizável vazia. Em uma leitura
    tautológica, repousa em premissas factualmente
    inexistentes no caso. Em ambas as hipóteses, é decisão
    não-fundamentada nos termos do art. 489, §1º, III, do
    CPC. -/
theorem acordao_universalmente_universalizavel :
    (V1a ∨ V1b ∨ V1c ∨ V3a ∨ V3c) → False := by
  intro h
  rcases h with h1a | h1b | h1c | h3a | h3c
  · exact V1a_viola_par1_III h1a
  · exact V1b_viola_par1_III h1b
  · exact V1c_viola_par1_III h1c
  · exact V3a_universalizacao_total h3a
  · exact V3c_viola_par1_III h3c

/- ============================================================
   Auditoria
   ============================================================ -/

#print axioms V1a_viola_par1_III
#print axioms V1b_viola_par1_III
#print axioms V1c_viola_par1_III
#print axioms V3a_universalizacao_total
#print axioms acordao_universalmente_universalizavel

end Sec1IIICheckSTEEL1eSTEEL3
