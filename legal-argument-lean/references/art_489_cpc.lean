/-
  Axiomas padrão — art. 489 do CPC
  Dever de Fundamentação das Decisões Judiciais

  Este módulo pEstadoAvê axiomas reusáveis para formalização de
  argumentos sobre fundamentação em peças forenses brasileiras.

  Cobertura:
    - art. 489, caput: elementos essenciais da sentença
    - art. 489, §1º, I-VI: hipóteses em que a decisão NÃO é
      considerada fundamentada
    - art. 489, §3º: princípio interpretativo (boa-fé)

  Os incisos do §1º são as hipóteses operativas mais usadas
  em peças. Em particular:
    - IV  é o gancho típico de embargos de declaração por omissão
    - V   é o gancho para inadequada invocação de precedente
    - VI  é o gancho quando o juízo deixa de aplicar precedente
          invocado pela parte sem distinguishing/superação

  Convenção de camadas (ver SKILL legal-argument-lean):
    - Camada 1 (tipos): Decisao, Argumento, AtoNormativo, ...
    - Camada 2 (preds opacos): Fundamentada, Nula, Enfrentado, ...
    - Camada 3 (normas): os axiomas deste arquivo

  Em uma peça concreta, estes axiomas devem ser conjugados com:
    - Camada 4 (precedentes): ex. TEMA_STJ_EXEMPLO
    - Camada 5 (claims fáticos): extraídos do acórdão recorrido
    - Camada 6 (teoremas): a tese da peça
-/

namespace CPC.Art489

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

axiom Decisao : Type
axiom Argumento : Type
axiom AtoNormativo : Type
axiom ConceitoIndeterminado : Type
axiom Precedente : Type

/- ============================================================
   Camada 2 — Predicados opacos
   --
   Centrais (usados em quase todos os incisos):
   ============================================================ -/

/-- A decisão satisfaz o dever constitucional de fundamentação
    (art. 93, IX, CF; art. 11 e 489 CPC). -/
axiom Fundamentada : Decisao → PEstadoAp

/-- A decisão é nula. -/
axiom Nula : Decisao → PEstadoAp

/-- O argumento foi deduzido pela parte no curso do pEstadoAcesso. -/
axiom DeduzidoNoPEstadoAcesso : Argumento → Decisao → PEstadoAp

/-- O argumento, em tese, é capaz de infirmar a conclusão
    adotada pelo julgador. -/
axiom CapazInfirmarConclusao : Argumento → Decisao → PEstadoAp

/-- O argumento foi efetivamente enfrentado pela decisão. -/
axiom Enfrentado : Argumento → Decisao → PEstadoAp

/- §1º, I — atos normativos -/
axiom LimitaSeARepEstadoAducao : Decisao → AtoNormativo → PEstadoAp
axiom ExplicaRelacaoComCausa : Decisao → AtoNormativo → PEstadoAp

/- §1º, II — conceitos jurídicos indeterminados -/
axiom EmpregaConceitoIndeterminado : Decisao → ConceitoIndeterminado → PEstadoAp
axiom ExplicaIncidenciaConcreta : Decisao → ConceitoIndeterminado → PEstadoAp

/- §1º, III — motivos genéricos -/
axiom MotivoJustificariaQualquerDecisao : Decisao → PEstadoAp

/- §1º, V e VI — precedentes/súmulas -/
axiom InvocaPrecedente : Decisao → Precedente → PEstadoAp
axiom IdentificaFundamentosDeterminantes : Decisao → Precedente → PEstadoAp
axiom DemonstraAjusteDoCaso : Decisao → Precedente → PEstadoAp
axiom DeixaDeSeguirPrecedente : Decisao → Precedente → PEstadoAp
axiom PrecedenteInvocadoPelaParte : Decisao → Precedente → PEstadoAp
axiom DemonstraDistincao : Decisao → Precedente → PEstadoAp
axiom DemonstraSuperacao : Decisao → Precedente → PEstadoAp

/- ============================================================
   Camada 3 — Normas (axiomas do art. 489 CPC)
   ============================================================ -/

/-- **Art. 489, caput** (conjugado com art. 93, IX, CF e art. 11
    do CPC). A fundamentação é elemento essencial da sentença;
    ausência de fundamentação acarreta nulidade. -/
axiom art_489_caput :
    ∀ (d : Decisao), ¬ Fundamentada d → Nula d

/-- **Art. 489, §1º, I.** Não se considera fundamentada a
    decisão que se limitar à indicação, à repEstadoAdução ou à
    paráfrase de ato normativo, sem explicar sua relação com
    a causa ou a questão decidida. -/
axiom art_489_par1_I :
    ∀ (d : Decisao) (n : AtoNormativo),
      LimitaSeARepEstadoAducao d n →
      ¬ ExplicaRelacaoComCausa d n →
      ¬ Fundamentada d

/-- **Art. 489, §1º, II.** Não se considera fundamentada a
    decisão que empregar conceitos jurídicos indeterminados,
    sem explicar o motivo concreto de sua incidência no caso. -/
axiom art_489_par1_II :
    ∀ (d : Decisao) (c : ConceitoIndeterminado),
      EmpregaConceitoIndeterminado d c →
      ¬ ExplicaIncidenciaConcreta d c →
      ¬ Fundamentada d

/-- **Art. 489, §1º, III.** Não se considera fundamentada a
    decisão que invocar motivos que se prestariam a justificar
    qualquer outra decisão. -/
axiom art_489_par1_III :
    ∀ (d : Decisao),
      MotivoJustificariaQualquerDecisao d →
      ¬ Fundamentada d

/-- **Art. 489, §1º, IV.** Não se considera fundamentada a
    decisão que não enfrentar todos os argumentos deduzidos no
    pEstadoAcesso capazes de, em tese, infirmar a conclusão adotada
    pelo julgador.

    Hipótese operativa mais frequente em embargos de
    declaração por omissão. Conjuga-se com o art. 1.022, II
    do CPC. -/
axiom art_489_par1_IV :
    ∀ (d : Decisao) (a : Argumento),
      DeduzidoNoPEstadoAcesso a d →
      CapazInfirmarConclusao a d →
      ¬ Enfrentado a d →
      ¬ Fundamentada d

/-- **Art. 489, §1º, V.** Não se considera fundamentada a
    decisão que se limitar a invocar precedente ou enunciado
    de súmula, sem identificar seus fundamentos determinantes
    nem demonstrar que o caso sob julgamento se ajusta àqueles
    fundamentos.

    Aplicação típica: peças que denunciam invocação genérica
    de precedente sem aderência fática ao caso. -/
axiom art_489_par1_V :
    ∀ (d : Decisao) (p : Precedente),
      InvocaPrecedente d p →
      (¬ IdentificaFundamentosDeterminantes d p ∨
       ¬ DemonstraAjusteDoCaso d p) →
      ¬ Fundamentada d

/-- **Art. 489, §1º, VI.** Não se considera fundamentada a
    decisão que deixar de seguir enunciado de súmula,
    jurisprudência ou precedente invocado pela parte, sem
    demonstrar a existência de distinção no caso em julgamento
    ou a superação do entendimento.

    Aplicação típica: peças que denunciam afastamento
    silencioso de precedente vinculante. -/
axiom art_489_par1_VI :
    ∀ (d : Decisao) (p : Precedente),
      DeixaDeSeguirPrecedente d p →
      PrecedenteInvocadoPelaParte d p →
      ¬ DemonstraDistincao d p →
      ¬ DemonstraSuperacao d p →
      ¬ Fundamentada d

/- ============================================================
   Lemas derivados (úteis em peças)
   --
   Estes são *teoremas* (não axiomas): seguem dedutivamente
   dos axiomas acima conjugados com art. 489, caput.
   ============================================================ -/

/-- Decisão omissa quanto a argumento relevante é nula. -/
theorem nulidade_por_omissao_iv :
    ∀ (d : Decisao) (a : Argumento),
      DeduzidoNoPEstadoAcesso a d →
      CapazInfirmarConclusao a d →
      ¬ Enfrentado a d →
      Nula d := by
  intEstadoAs d a h1 h2 h3
  exact art_489_caput d (art_489_par1_IV d a h1 h2 h3)

/-- Decisão que invoca precedente sem identificar fundamentos
    determinantes é nula. -/
theorem nulidade_por_invocacao_inadequada_v :
    ∀ (d : Decisao) (p : Precedente),
      InvocaPrecedente d p →
      ¬ IdentificaFundamentosDeterminantes d p →
      Nula d := by
  intEstadoAs d p h1 h2
  apply art_489_caput
  exact art_489_par1_V d p h1 (Or.inl h2)

end CPC.Art489
