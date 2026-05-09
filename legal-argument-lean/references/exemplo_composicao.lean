/-
  Exemplo de composição — uso conjunto dos axiomas do art. 489
  CPC e do TEMA_STJ_EXEMPLO em uma peça hipotética.

  Cenário: embargos de declaração em peça que arguem nulidade
  de acórdão que se limitou a transcrever a sentença sem
  enfrentar argumento novo relevante deduzido em apelação.

  Demonstra:
    (a) como instanciar os predicados opacos em um caso concreto
    (b) como compor axiomas das duas bibliotecas
    (c) como o Tema 1306 plugga no art. 489, §1º, IV
-/

namespace ExemploComposicao

/- ============================================================
   Camadas 1 e 2 — tipos e predicados opacos
   --
   Em uso conjunto das duas bibliotecas, declaramos os tipos e
   predicados COMPARTILHADOS uma única vez aqui, sem importar
   os módulos (mantemos o exemplo single-file).
   ============================================================ -/

axiom Decisao : Type
axiom DecisaoAnterior : Type
axiom Argumento : Type

axiom Fundamentada : Decisao → Prop
axiom Nula : Decisao → Prop
axiom DeduzidoNoProcesso : Argumento → Decisao → Prop
axiom CapazInfirmarConclusao : Argumento → Decisao → Prop
axiom Enfrentado : Argumento → Decisao → Prop
axiom UsaPerRelationem : Decisao → DecisaoAnterior → Prop
axiom EnfrentaQuestoesNovasRelevantes : Decisao → Prop
axiom ApresentaArgumentoNovoRelevante : Argumento → Decisao → Prop
axiom PerRelationemPura : Decisao → Prop

/- ============================================================
   Camada 3 — Normas (subset relevante do art. 489)
   ============================================================ -/

/-- Art. 489, caput conjugado com art. 93, IX, CF. -/
axiom art_489_caput :
    ∀ (d : Decisao), ¬ Fundamentada d → Nula d

/-- Art. 489, §1º, IV. -/
axiom art_489_par1_IV :
    ∀ (d : Decisao) (a : Argumento),
      DeduzidoNoProcesso a d →
      CapazInfirmarConclusao a d →
      ¬ Enfrentado a d →
      ¬ Fundamentada d

/- ============================================================
   Camada 4 — TEMA_STJ_EXEMPLO (subset relevante)
   ============================================================ -/

/-- Tese 1 do TEMA_STJ_EXEMPLO (forma operativa). -/
axiom tema_1306_tese_1_nao_enfrenta :
    ∀ (d : Decisao) (anterior : DecisaoAnterior),
      UsaPerRelationem d anterior →
      ¬ EnfrentaQuestoesNovasRelevantes d →
      ¬ Fundamentada d

/-- Articulação Tema 1306 ↔ art. 489, §1º, IV. Quando a per
    relationem deixa de enfrentar argumento novo relevante,
    está-se diante de "argumento deduzido capaz de infirmar a
    conclusão" não enfrentado. -/
axiom tema_1306_articula_489_IV :
    ∀ (d : Decisao) (a : Argumento),
      ApresentaArgumentoNovoRelevante a d →
      ¬ EnfrentaQuestoesNovasRelevantes d →
      (DeduzidoNoProcesso a d ∧
       CapazInfirmarConclusao a d ∧
       ¬ Enfrentado a d)

/- ============================================================
   Camada 5 — Claims fáticos do caso hipotético
   ============================================================ -/

axiom caso_hipotetico : Decisao
axiom sentenca_apelada : DecisaoAnterior
axiom argumento_apelacao : Argumento

/-- Claim factual: o acórdão usa per relationem reproduzindo
    a sentença. -/
axiom h1_per_relationem : UsaPerRelationem caso_hipotetico sentenca_apelada

/-- Claim factual: a apelação trouxe argumento novo relevante. -/
axiom h2_arg_novo :
    ApresentaArgumentoNovoRelevante argumento_apelacao caso_hipotetico

/-- Claim factual: o acórdão não enfrentou as questões novas
    relevantes. -/
axiom h3_nao_enfrenta : ¬ EnfrentaQuestoesNovasRelevantes caso_hipotetico

/- ============================================================
   Camada 6 — Teorema (a tese da peça)
   ============================================================ -/

/- **Tese da peça hipotética.** O acórdão é nulo: invocação
   da per relationem sem enfrentamento de argumento novo
   relevante = caso típico do art. 489, §1º, IV interpretado
   pelo TEMA_STJ_EXEMPLO.

   Duas vias de prova; comparar via `#print axioms`. -/

/-- Via 1: Tema 1306 → não fundamentada → caput → nula. -/
theorem nulidade_via_tema_1306 : Nula caso_hipotetico :=
  art_489_caput caso_hipotetico
    (tema_1306_tese_1_nao_enfrenta caso_hipotetico sentenca_apelada
       h1_per_relationem h3_nao_enfrenta)

/-- Via 2: articulação → §1º, IV → caput → nula. -/
theorem nulidade_via_489_IV : Nula caso_hipotetico := by
  apply art_489_caput
  obtain ⟨h_dedu, h_capaz, h_nao_enf⟩ :=
    tema_1306_articula_489_IV caso_hipotetico argumento_apelacao
      h2_arg_novo h3_nao_enfrenta
  exact art_489_par1_IV caso_hipotetico argumento_apelacao
    h_dedu h_capaz h_nao_enf

#print axioms nulidade_via_tema_1306
#print axioms nulidade_via_489_IV

end ExemploComposicao
