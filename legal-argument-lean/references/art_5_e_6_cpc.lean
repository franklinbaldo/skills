/-
  Axiomas padrão — arts. 5º e 6º do CPC
  Boa-fé Processual Objetiva e Dever de Cooperação

  Art. 5º: "Aquele que de qualquer forma participa do
  processo deve comportar-se de acordo com a boa-fé."

  Art. 6º: "Todos os sujeitos do processo devem cooperar
  entre si para que se obtenha, em tempo razoável, decisão de
  mérito justa e efetiva."

  ┌──────────────────────────────────────────────────────────┐
  │  O QUE TORNA A BOA-FÉ "OBJETIVA"                         │
  ├──────────────────────────────────────────────────────────┤
  │                                                          │
  │  A boa-fé processual prevista no art. 5º é OBJETIVA, e   │
  │  não subjetiva. A distinção é estrutural:                │
  │                                                          │
  │    BOA-FÉ SUBJETIVA: estado psicológico (acreditar       │
  │      agir corretamente, ignorar vício). Avalia-se a      │
  │      INTENÇÃO do sujeito.                                │
  │                                                          │
  │    BOA-FÉ OBJETIVA: padrão de conduta exteriormente      │
  │      verificável. Avalia-se o COMPORTAMENTO,             │
  │      independentemente da intenção. Equivale a um        │
  │      padrão razoável de probidade processual aferido     │
  │      externamente.                                       │
  │                                                          │
  │  A objetividade da boa-fé é operacionalizada pelas       │
  │  FIGURAS PARCELARES: cada uma é um padrão exterior,      │
  │  reconhecido pela doutrina e jurisprudência, cuja        │
  │  ocorrência se afere pela sequência observável de atos   │
  │  do sujeito — sem indagação sobre seu estado mental.     │
  │                                                          │
  │  As figuras parcelares aqui axiomatizadas:               │
  │    • venire contra factum proprium                       │
  │    • tu quoque                                           │
  │    • supressio (perda por inércia + confiança gerada)    │
  │    • surrectio (aquisição por exercício + confiança)     │
  │    • adimplemento substancial                            │
  │    • dever de cooperação (art. 6º)                       │
  │                                                          │
  │  Logo: dizer "X violou a boa-fé objetiva" é dizer        │
  │  "X incorreu em alguma das figuras parcelares". A        │
  │  pergunta sobre o que X pensava é juridicamente          │
  │  irrelevante.                                            │
  └──────────────────────────────────────────────────────────┘

  CONEXÕES ESTRUTURAIS

  • Com `art_926_cpc.lean`: o venire contra factum proprium
    INSTITUCIONAL (do tribunal) é a aplicação da boa-fé
    objetiva ao plano da jurisprudência. Quando o tribunal
    aplica tese T1 em caso análogo e depois T2 (incompatível
    com T1) sem distinguishing, viola simultaneamente a
    coerência (art. 926) e a boa-fé objetiva (art. 5º).

  • Com `art_489_cpc.lean`: a invocação de motivos genéricos
    (§1º, III) e o afastamento silente de precedente (§1º, VI)
    são, respectivamente, formas de quebra da boa-fé
    institucional e de venire institucional.

  • Com `art_10_cpc.lean`: o contraditório substancial é a
    expressão concreta do dever de cooperação (art. 6º).
    Decidir de surpresa é descumprir o dever de cooperação.

  Sujeitos vinculados: TODOS (parte, advogado, juiz, tribunal,
  terceiros, MP). É expressamente o que dizem os arts. 5º e
  6º. Importante para arguir venire institucional (do
  tribunal) em peças PGE.
-/

namespace CPC.Art5e6

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

/-- Qualquer sujeito processual: partes, advogados, juiz,
    tribunal, terceiros intervenientes, Ministério Público. -/
axiom Sujeito : Type

axiom Processo : Type
axiom Conduta : Type
axiom Pretensao : Type
axiom Direito : Type
axiom NormaProcessual : Type
axiom Decisao : Type

/- ============================================================
   Camada 2 — Predicados opacos
   ============================================================ -/

/-- O sujeito age conforme a boa-fé objetiva no processo. -/
axiom AgeBoaFeObjetiva : Sujeito → Processo → Prop

/-- O sujeito participa do processo (gancho do art. 5º). -/
axiom ParticipaDoProcesso : Sujeito → Processo → Prop

/-- O sujeito cumpre o dever de cooperação (art. 6º). -/
axiom CumpreDeverCooperacao : Sujeito → Processo → Prop

/- Caracterização objetiva (sem referência a intenção) -/

/-- O sujeito praticou a conduta no processo, em momento
    anterior. -/
axiom PraticouCondutaAnterior : Sujeito → Conduta → Processo → Prop

/-- O sujeito praticou a conduta no processo, em momento
    posterior. -/
axiom PraticouCondutaPosterior : Sujeito → Conduta → Processo → Prop

/-- A conduta gera, *exteriormente*, expectativa legítima de
    continuidade ou consistência (predicado avaliado pela
    forma da conduta, não pela intenção). -/
axiom GeraExpectativaLegitima : Conduta → Sujeito → Prop

/-- A segunda conduta contraria a expectativa gerada pela
    primeira (relação observável entre as duas condutas). -/
axiom ContrariaExpectativa : Conduta → Conduta → Prop

/-- O sujeito permaneceu inerte por período prolongado quanto
    à pretensão. -/
axiom InerciaProlongada : Sujeito → Pretensao → Processo → Prop

/-- O exercício prolongado e reiterado de uma posição gerou
    confiança legítima. -/
axiom ExercicioProlongadoGeraConfianca : Sujeito → Direito → Processo → Prop

/-- O sujeito descumpriu a norma processual e agora a invoca
    contra outrem. -/
axiom DescumpriuENormaInvoca : Sujeito → NormaProcessual → Processo → Prop

/-- A obrigação foi adimplida em parte substancial,
    insuficiente para justificar resolução. -/
axiom AdimplidaEmParteSubstancial : Sujeito → Processo → Prop

/- ============================================================
   Camada 2.5 — Figuras parcelares (predicados de violação)
   ============================================================ -/

/-- Venire contra factum proprium: comportamento contraditório
    que frustra expectativa legítima gerada por conduta
    anterior do mesmo sujeito. -/
axiom VenireContraFactumProprium : Sujeito → Conduta → Conduta → Processo → Prop

/-- Tu quoque: invocação, contra outrem, de regra processual
    que o próprio sujeito descumpriu. -/
axiom TuQuoque : Sujeito → NormaProcessual → Processo → Prop

/-- Supressio: perda da pretensão pela inércia prolongada do
    titular, conjugada à confiança legítima da contraparte. -/
axiom Supressio : Sujeito → Pretensao → Processo → Prop

/-- Surrectio: aquisição de posição jurídica em razão do
    exercício prolongado, conjugado à confiança legítima. -/
axiom Surrectio : Sujeito → Direito → Processo → Prop

/-- Adimplemento substancial: óbice à resolução da obrigação
    quando o cumprimento parcial é juridicamente relevante. -/
axiom AdimplementoSubstancial : Sujeito → Processo → Prop

/- ============================================================
   Camada 3 — Definições operativas das figuras
   --
   Cada axioma define uma figura parcelar EXCLUSIVAMENTE em
   termos de padrões exteriores observáveis — sem qualquer
   referência a estados mentais. É a operacionalização da
   objetividade da boa-fé.
   ============================================================ -/

/-- **Venire — definição objetiva.** Configura-se venire
    contra factum proprium quando o sujeito praticou conduta
    anterior que gerou expectativa legítima e, posteriormente,
    pratica conduta que contraria essa expectativa.

    Note: a definição não menciona a "intenção" do sujeito de
    contradizer. Só importa o que se observa externamente:
    duas condutas, expectativa gerada, contradição. -/
axiom venire_definicao :
    ∀ (s : Sujeito) (c1 c2 : Conduta) (p : Processo),
      PraticouCondutaAnterior s c1 p →
      PraticouCondutaPosterior s c2 p →
      GeraExpectativaLegitima c1 s →
      ContrariaExpectativa c2 c1 →
      VenireContraFactumProprium s c1 c2 p

/-- **Tu quoque — definição objetiva.** Configura-se tu
    quoque quando o sujeito descumpriu norma processual e
    agora a invoca contra outrem. -/
axiom tu_quoque_definicao :
    ∀ (s : Sujeito) (n : NormaProcessual) (p : Processo),
      DescumpriuENormaInvoca s n p →
      TuQuoque s n p

/-- **Supressio — definição objetiva.** Configura-se
    supressio quando há inércia prolongada do titular,
    conjugada à confiança legítima gerada na contraparte. -/
axiom supressio_definicao :
    ∀ (s : Sujeito) (pr : Pretensao) (p : Processo),
      InerciaProlongada s pr p →
      Supressio s pr p

/-- **Surrectio — definição objetiva.** Configura-se
    surrectio pelo exercício prolongado e reiterado de uma
    posição que gera confiança legítima. -/
axiom surrectio_definicao :
    ∀ (s : Sujeito) (d : Direito) (p : Processo),
      ExercicioProlongadoGeraConfianca s d p →
      Surrectio s d p

/-- **Adimplemento substancial — definição objetiva.** -/
axiom adimplemento_substancial_definicao :
    ∀ (s : Sujeito) (p : Processo),
      AdimplidaEmParteSubstancial s p →
      AdimplementoSubstancial s p

/- ============================================================
   Camada 3.5 — Cada figura implica violação da boa-fé
   --
   Aqui se afirma que toda figura parcelar é causa suficiente
   de violação à boa-fé objetiva. Esta é a estrutura da
   "operacionalização": dizer "violou a boa-fé" é dizer
   "incorreu em pelo menos uma das figuras".
   ============================================================ -/

/-- Quem incorre em venire contra factum proprium NÃO age
    conforme a boa-fé objetiva. -/
axiom venire_viola_boa_fe :
    ∀ (s : Sujeito) (c1 c2 : Conduta) (p : Processo),
      VenireContraFactumProprium s c1 c2 p →
      ¬ AgeBoaFeObjetiva s p

/-- Quem incorre em tu quoque não age conforme a boa-fé. -/
axiom tu_quoque_viola_boa_fe :
    ∀ (s : Sujeito) (n : NormaProcessual) (p : Processo),
      TuQuoque s n p →
      ¬ AgeBoaFeObjetiva s p

/-- A configuração de supressio reflete violação à boa-fé
    pela continuidade de pretensão cuja inércia gerou
    confiança contrária. -/
axiom supressio_viola_boa_fe :
    ∀ (s : Sujeito) (pr : Pretensao) (p : Processo),
      Supressio s pr p →
      ¬ AgeBoaFeObjetiva s p

/- ============================================================
   Camada 3.6 — Norma central do art. 5º (dever, não fato)
   --
   IMPORTANTE: A boa-fé objetiva é um DEVER imposto pelo art.
   5º, não uma descrição factual do comportamento. Por isso,
   axiomatizamos um predicado de DEVER (`DevendoAgirBoaFe`)
   distinto do predicado FACTUAL (`AgeBoaFeObjetiva`). A
   violação configura-se quando o dever existe mas a conduta
   real não satisfaz o padrão.
   ============================================================ -/

/-- Predicado normativo: o sujeito tem o dever de agir
    conforme a boa-fé objetiva no processo. -/
axiom DevendoAgirBoaFe : Sujeito → Processo → Prop

/-- **Art. 5º do CPC.** Quem participa do processo tem o
    DEVER de agir conforme a boa-fé objetiva.

    Note: o art. 5º institui o dever; sua violação é objeto
    dos axiomas das figuras parcelares acima. -/
axiom art_5_dever_geral_boa_fe :
    ∀ (s : Sujeito) (p : Processo),
      ParticipaDoProcesso s p →
      DevendoAgirBoaFe s p

/-- Violação configurada: há dever mas não há conformidade. -/
axiom violacao_art_5 :
    ∀ (s : Sujeito) (p : Processo),
      DevendoAgirBoaFe s p →
      ¬ AgeBoaFeObjetiva s p →
      ∃ figura_parcelar : Prop, figura_parcelar

/- ============================================================
   Camada 3.7 — Cooperação (art. 6º)
   --
   Mesma estrutura: dever vs. fato.
   ============================================================ -/

/-- Predicado normativo do dever de cooperação. -/
axiom DevendoCooperar : Sujeito → Processo → Prop

/-- **Art. 6º do CPC.** Todos os sujeitos do processo têm o
    DEVER de cooperar entre si para obtenção de decisão de
    mérito justa e efetiva, em tempo razoável. -/
axiom art_6_dever_cooperacao :
    ∀ (s : Sujeito) (p : Processo),
      ParticipaDoProcesso s p →
      DevendoCooperar s p

/-- A violação ao dever de cooperação é forma de violação à
    boa-fé objetiva (cooperação é instância qualificada da
    boa-fé processual). -/
axiom descumprimento_cooperacao_viola_boa_fe :
    ∀ (s : Sujeito) (p : Processo),
      ¬ CumpreDeverCooperacao s p →
      ¬ AgeBoaFeObjetiva s p

/- ============================================================
   Camada 6 — Lemas derivados
   ============================================================ -/

/-- Demonstrada a base fática do venire (conduta anterior +
    expectativa + conduta posterior contrária), conclui-se
    pela violação da boa-fé. Útil para alegar venire
    institucional (do tribunal) em peças PGE: aplicação de
    tese T1 em caso análogo é a "conduta anterior" que gera
    expectativa de aplicação consistente; aplicação de T2
    incompatível, sem distinguishing, é a "conduta
    posterior" que contraria a expectativa. -/
theorem violacao_boa_fe_por_venire :
    ∀ (s : Sujeito) (c1 c2 : Conduta) (p : Processo),
      PraticouCondutaAnterior s c1 p →
      PraticouCondutaPosterior s c2 p →
      GeraExpectativaLegitima c1 s →
      ContrariaExpectativa c2 c1 →
      ¬ AgeBoaFeObjetiva s p := by
  intros s c1 c2 p h_ant h_pos h_exp h_contr
  exact venire_viola_boa_fe s c1 c2 p
    (venire_definicao s c1 c2 p h_ant h_pos h_exp h_contr)

/-- Quem invoca norma processual contra outrem após
    descumpri-la não age conforme a boa-fé. -/
theorem violacao_boa_fe_por_tu_quoque :
    ∀ (s : Sujeito) (n : NormaProcessual) (p : Processo),
      DescumpriuENormaInvoca s n p →
      ¬ AgeBoaFeObjetiva s p := by
  intros s n p h
  exact tu_quoque_viola_boa_fe s n p (tu_quoque_definicao s n p h)

end CPC.Art5e6
