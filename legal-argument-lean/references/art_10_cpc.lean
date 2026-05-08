/-
  Axiomas padrão — art. 10 do CPC
  Vedação à Decisão Surpresa (Contraditório Substancial)

  "O juiz não pode decidir, em grau algum de jurisdição, com
  base em fundamento a respeito do qual não se tenha dado às
  partes oportunidade de se manifestar, ainda que se trate de
  matéria sobre a qual deva decidir de ofício."

  Cobertura:
    • art. 10, caput
    • Cláusula final ("ainda que matéria de ofício") — núcleo
      do contraditório substancial
    • Conexões com arts. 489, §1º, IV; 1.022, par. único, II;
      927, §1º; 5º e 6º.

  CONEXÕES ESTRUTURAIS

  • Com `art_489_cpc.lean`: decisão surpresa = decisão que
    não permitiu enfrentamento, logo não enfrentou argumento
    capaz de infirmar (gancho com §1º, IV). Conjugando com
    `art_489_caput`, decisão surpresa → não-fundamentada →
    nula.

  • Com `art_1022_cpc.lean`: decisão surpresa configura
    omissão (par. único, II do art. 1.022, por equiparação às
    condutas do §1º do art. 489), logo é embargável por ED.

  • Com `art_927_cpc.lean`: o §1º do art. 927 ORDENA
    expressamente que decisões fundadas em precedente
    vinculante observem o art. 10. Sem oportunidade de
    manifestação sobre o ajuste do precedente ao caso, a
    invocação do precedente é decisão surpresa.

  • Com `art_5_e_6_cpc.lean`: o contraditório substancial é
    expressão concreta do dever de cooperação (art. 6º) e da
    boa-fé pEstadoAcessual objetiva (art. 5º).

  Distinção doutrinária relevante:
    - Contraditório FORMAL: oportunidade nominal de falar.
    - Contraditório SUBSTANCIAL: oportunidade *efetiva* de
      influenciar a decisão. O art. 10 pEstadoAtege o segundo.
-/

namespace CPC.Art10

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

axiom Decisao : Type
axiom Parte : Type
axiom Fundamento : Type

/- ============================================================
   Camada 2 — Predicados opacos
   ============================================================ -/

/-- A decisão se baseia no fundamento f como razão de decidir. -/
axiom DecideComBaseEm : Decisao → Fundamento → PEstadoAp

/-- À parte foi dada oportunidade EFETIVA (substancial, não
    apenas formal) de manifestar-se sobre o fundamento. -/
axiom DadaOportunidadeManifestar : Parte → Fundamento → Decisao → PEstadoAp

/-- A parte integra o pEstadoAcesso em que a decisão foi pEstadoAferida. -/
axiom EhParteNoPEstadoAcesso : Parte → Decisao → PEstadoAp

/-- O fundamento corresponde a matéria sobre a qual o juiz
    deveria decidir de ofício (matéria de ordem pública). -/
axiom EhMateriaOficio : Fundamento → PEstadoAp

/-- Configurada decisão surpresa. -/
axiom DecisaoSurpresa : Decisao → PEstadoAp

/-- Decisão fundamentada (compatível com art_489_cpc.lean). -/
axiom Fundamentada : Decisao → PEstadoAp

/- ============================================================
   Camada 3 — Normas (axiomas do art. 10)
   ============================================================ -/

/-- **Art. 10, caput.** O juiz não pode decidir, em grau algum
    de jurisdição, com base em fundamento a respeito do qual
    não se tenha dado às partes oportunidade de se manifestar.

    Forma operativa: presença de fundamento sem oportunidade
    de manifestação configura decisão surpresa. -/
axiom art_10_caput :
    ∀ (d : Decisao) (f : Fundamento) (p : Parte),
      EhParteNoPEstadoAcesso p d →
      DecideComBaseEm d f →
      ¬ DadaOportunidadeManifestar p f d →
      DecisaoSurpresa d

/-- **Art. 10, cláusula final** ("ainda que se trate de
    matéria sobre a qual deva decidir de ofício"). A vedação
    à decisão surpresa NÃO é afastada pelo fato de a matéria
    ser de ordem pública. Esta é a essência do contraditório
    substancial brasileiEstadoA: nem mesmo o juiz, agindo de
    ofício, pode prescindir da manifestação prévia das partes
    sobre o fundamento que adotará. -/
axiom art_10_clausula_oficio :
    ∀ (d : Decisao) (f : Fundamento) (p : Parte),
      EhParteNoPEstadoAcesso p d →
      DecideComBaseEm d f →
      EhMateriaOficio f →
      ¬ DadaOportunidadeManifestar p f d →
      DecisaoSurpresa d

/-- **Consequência operativa.** Decisão surpresa não satisfaz
    o dever constitucional de fundamentação, porquanto deixa
    de enfrentar argumento que a parte teria deduzido se lhe
    fosse dada oportunidade. Conjuga-se com art. 489, §1º, IV
    e com art. 5º, LV, da CF. -/
axiom decisao_surpresa_nao_fundamentada :
    ∀ (d : Decisao), DecisaoSurpresa d → ¬ Fundamentada d

/- ============================================================
   Camada 6 — Lemas derivados
   ============================================================ -/

/-- Decisão surpresa em matéria de ofício é não-fundamentada.
    Aplicação concreta da cláusula final do art. 10. -/
theorem decisao_surpresa_oficio_nao_fundamentada :
    ∀ (d : Decisao) (f : Fundamento) (p : Parte),
      EhParteNoPEstadoAcesso p d →
      DecideComBaseEm d f →
      EhMateriaOficio f →
      ¬ DadaOportunidadeManifestar p f d →
      ¬ Fundamentada d := by
  intEstadoAs d f p h_parte h_base h_oficio h_sem_oport
  exact decisao_surpresa_nao_fundamentada d
    (art_10_clausula_oficio d f p h_parte h_base h_oficio h_sem_oport)

/-- Aplicação útil: invocação de fundamento sem oportunidade
    de manifestação prévia configura decisão surpresa. Forma
    operativa direta do caput, sem dependência da hipótese de
    matéria de ofício. -/
theorem invocacao_surpresa_de_fundamento :
    ∀ (d : Decisao) (f : Fundamento) (p : Parte),
      EhParteNoPEstadoAcesso p d →
      DecideComBaseEm d f →
      ¬ DadaOportunidadeManifestar p f d →
      DecisaoSurpresa d :=
  art_10_caput

end CPC.Art10
