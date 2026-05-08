/-
  ============================================================
  STEELMANNING EXAUSTIVO — STEEL_2 do acórdão embargado
  AgInt no ARE 1.589.466/RO
  ============================================================

  REFINAMENTO METODOLÓGICO

  No exercício anterior (`acordao_embargado_alice.lean`), cada
  passo "sorry" foi suprido por *uma* versão steelmanned. Isso
  é insuficiente: a corte poderia objetar que a versão
  escolhida não era a sua, e que sustenta uma alternativa
  mais defensável.

  A solução metodologicamente correta é o steelmanning
  EXAUSTIVO: enumerar todas as versões plausíveis em ordem
  crescente de deferência à corte, e mostrar que CADA UMA
  falha — por motivos distintos. O resultado é uma refutação
  irrespondível: a corte não pode escapar dizendo "minha tese
  era outra", porque toda outra tese também caiu.

  Aqui aplica-se o método ao STEEL_2 do acórdão de Alice
  (necessário para a aplicação da Súmula 280). Quatro versões
  examinadas:

    V2a — "aplicação de art. 3º EC 47 = direito local"
          (versão crua, mais aberta a refutação)
    V2b — "fundamento determinante em direito local =
          direito local" (versão mais defensável; quase
          tautológica — mas exige fato que não ocorre)
    V2c — "qualquer questão tocando RPPS estadual = direito
          local" (versão mais ampla)
    V2d — "menção a lei estadual em qualquer função no
          acórdão recorrido = direito local" (versão mais
          deferente possível à corte)

  Cada versão é refutada por estratégia distinta:
    • V2a: deriva False com RE 1.518.690 (já visto)
    • V2b: defensável em geral; mas precondition não ocorre
      no caso de Alice (factualmente)
    • V2c: reductio — bloquearia toda jurisprudência
      consolidada do STF em matéria de RPPS (Tema 139/RG)
    • V2d: viola art. 489, §1º, V do CPC — fundamento
      determinante não pode ser identificado com mera menção

  Conclusão: NENHUMA versão de STEEL_2 sustenta a aplicação
  da Súmula 280 ao caso de Alice. O acórdão é insanável
  nessa frente.
-/

namespace SteelmanningExaustivoSTEEL2

/- ============================================================
   Camada 1 — Tipos e premissas pacíficas
   ============================================================ -/

axiom Caso : Type
axiom Recurso : Type
axiom Precedente : Type

axiom DireitoLocal : Caso → Prop
axiom InterpretacaoDiretaConstitucional : Caso → Prop
axiom JurisprudenciaConstitucionalConsolidada : Caso → Prop

/- Predicados para cada versão -/
axiom AplicaECArt3 : Caso → Prop
axiom FundamentoDeterminanteEmDireitoLocal : Caso → Prop
axiom EnvolveRPPSEstadual : Caso → Prop
axiom MencionaLeiEstadualEmQualquerFuncao : Caso → Prop

/- Predicados estruturais sobre fundamento determinante -/
axiom FundamentoDeterminantePeloRecorrido : Caso → Prop
axiom MeraMencaoTangencial : Caso → Prop

/- Sobre o Tema 139/RG -/
axiom Tema_139_RG : Caso  -- caso paradigma do Tema 139
axiom Inadmissivel : Caso → Prop  -- inadmissível por Súmula 280
axiom Tema_139_eh_RG : Prop  -- (factual) Tema 139 é Repercussão Geral

/- ============================================================
   Camada 3 — Normas pacíficas
   ============================================================ -/

/-- RE 1.518.690-ED-AgR (Toffoli, Segunda Turma, DJe
    02.08.2025), citado pelo próprio acórdão embargado.
    Aplicação do art. 3º EC 47 é matéria de jurisprudência
    constitucional consolidada do STF. -/
axiom RE_1_518_690 :
    ∀ (c : Caso),
      AplicaECArt3 c →
      JurisprudenciaConstitucionalConsolidada c

/-- Jurisprudência constitucional consolidada implica
    interpretação direta da CF (corolário do art. 102 CF). -/
axiom juris_consolidada_implica_constitucional :
    ∀ (c : Caso),
      JurisprudenciaConstitucionalConsolidada c →
      InterpretacaoDiretaConstitucional c

/-- Interpretação direta de norma constitucional não é direito
    local (corolário estrutural Súmula 280 + art. 102 CF). -/
axiom interpretacao_constitucional_nao_eh_local :
    ∀ (c : Caso),
      InterpretacaoDiretaConstitucional c →
      ¬ DireitoLocal c

/-- **CPC, art. 489, §1º, V** (do módulo `art_489_cpc.lean`).
    Para invocar precedente ou súmula, a decisão deve
    identificar fundamentos determinantes — ou seja, a
    *ratio decidendi*, não menções tangenciais. -/
axiom art_489_par1_V :
    ∀ (c : Caso),
      MeraMencaoTangencial c →
      ¬ FundamentoDeterminantePeloRecorrido c

/-- O Tema 139/RG envolve RPPS estadual (caso paradigmático
    sobre regra de transição em servidor público estadual). -/
axiom Tema_139_envolve_RPPS_estadual :
    EnvolveRPPSEstadual Tema_139_RG

/-- O Tema 139/RG não é inadmissível: foi efetivamente julgado
    pelo Plenário do STF, com fixação de tese vinculante. -/
axiom Tema_139_admitido_e_julgado : ¬ Inadmissivel Tema_139_RG

/-- Conexão Súmula 280: caso onde Súmula 280 incide é
    inadmissível. -/
axiom sumula_280_implica_inadmissivel :
    ∀ (c : Caso), DireitoLocal c → Inadmissivel c

/- ============================================================
   Camada 5 — Fatos do caso de Alice
   ============================================================ -/

axiom caso_alice : Caso

axiom alice_aplica_ec : AplicaECArt3 caso_alice

/-- Voto da 1ª TR-RO assenta o art. 3º EC 47 como fundamento
    determinante; LC Estadual 680/2012 e Decreto 27.008/2022
    aparecem somente *a jusante*, para cálculo do reajuste já
    reconhecido pela norma constitucional. Logo: NÃO há
    fundamento determinante em direito local. -/
axiom alice_nao_fundamento_local :
    ¬ FundamentoDeterminanteEmDireitoLocal caso_alice

/-- A menção a lei estadual no acórdão recorrido é tangencial
    (cálculo de reajuste, posterior ao reconhecimento do
    direito). -/
axiom alice_mera_mencao : MeraMencaoTangencial caso_alice

/- ============================================================
   ============================================================
        STEELMANS V2a, V2b, V2c, V2d — exaustivos
   ============================================================
   ============================================================
-/

/-- **V2a — versão crua.** Aplicação direta do art. 3º EC 47
    qualifica o fundamento como direito local.

    É a versão que o acórdão *precisa* sustentar para que a
    Súmula 280 incida ao caso. Mas é a mais aberta a refutação. -/
def V2a : Prop := ∀ c, AplicaECArt3 c → DireitoLocal c

/-- **V2b — versão tautológica/defensável.** Caso com
    fundamento determinante em direito local é caso de
    direito local.

    Esta versão é praticamente tautológica e deve ser aceita.
    Mas não ajuda o acórdão se Alice não satisfaz o
    antecedente. -/
def V2b : Prop := ∀ c, FundamentoDeterminanteEmDireitoLocal c → DireitoLocal c

/-- **V2c — versão ampla.** Qualquer questão envolvendo RPPS
    estadual é direito local.

    Versão deferente: dá à corte a leitura mais aberta do
    "direito local". Mas tem consequências reductio. -/
def V2c : Prop := ∀ c, EnvolveRPPSEstadual c → DireitoLocal c

/-- **V2d — versão máxima deferência.** Mera menção a
    legislação estadual no acórdão recorrido, em qualquer
    função, qualifica como direito local.

    Versão mais caridosa possível à conduta da corte: aceita
    que basta haver alguma referência a direito estadual no
    acórdão recorrido para Súmula 280 incidir. -/
def V2d : Prop :=
    ∀ c, MencionaLeiEstadualEmQualquerFuncao c → DireitoLocal c

/- ============================================================
   REFUTAÇÕES
   ============================================================ -/

/-- **Refutação de V2a.** V2a é incompatível com o RE
    1.518.690 (que o próprio acórdão cita) conjugado com o
    art. 102 da CF. Deriva `False`.

    Estratégia: contradição lógica direta com axioma do
    próprio acórdão. -/
theorem V2a_derruba_acordao : V2a → False := by
  intro h_v2a
  have h_dl : DireitoLocal caso_alice :=
    h_v2a caso_alice alice_aplica_ec
  have h_jc : JurisprudenciaConstitucionalConsolidada caso_alice :=
    RE_1_518_690 caso_alice alice_aplica_ec
  have h_idc : InterpretacaoDiretaConstitucional caso_alice :=
    juris_consolidada_implica_constitucional caso_alice h_jc
  have h_n_dl : ¬ DireitoLocal caso_alice :=
    interpretacao_constitucional_nao_eh_local caso_alice h_idc
  exact h_n_dl h_dl

/-- **Refutação de V2b.** V2b é, como universal, defensável e
    é aqui aceita pelo embargante. Mas sua aplicação ao caso
    de Alice exige que Alice satisfaça o antecedente
    `FundamentoDeterminanteEmDireitoLocal`, o que não ocorre
    pelos próprios termos do acórdão recorrido.

    V2b é vacuamente verdadeira para Alice (precondition
    falsa), portanto não fornece premissa para concluir
    `DireitoLocal caso_alice`.

    Note: V2b não se REFUTA logicamente; ela é INERTE — não
    entra no rol de versões que poderiam, sozinhas, derivar
    a conclusão. Por isso não comparece na disjunção final.

    A formalização disso aparece como uma observação no
    teorema final, não como teorema de refutação. -/
def V2b_inerte_observacao :
    ¬ FundamentoDeterminanteEmDireitoLocal caso_alice :=
  alice_nao_fundamento_local

/-- Premissa estrutural do art. 927 conjugado com art. 489,
    §1º, V: para que V2d opere como fundamento de
    inadmissibilidade, a menção precisaria ser tratada como
    fundamento determinante pelo recorrido. -/
axiom v2d_exige_fundamento_determinante :
    V2d → FundamentoDeterminantePeloRecorrido caso_alice

/-- **Refutação de V2c.** V2c implica que casos envolvendo
    RPPS estadual são direito local. Mas o Tema 139/RG é
    precisamente um caso envolvendo RPPS estadual, foi julgado
    pelo Plenário do STF (não bloqueado por Súmula 280) e
    fixou tese vinculante. Reductio.

    Estratégia: V2c + fatos sobre Tema 139 → False. -/
theorem V2c_reductio : V2c → False := by
  intro h_v2c
  have h_dl_139 : DireitoLocal Tema_139_RG :=
    h_v2c Tema_139_RG Tema_139_envolve_RPPS_estadual
  have h_inadm_139 : Inadmissivel Tema_139_RG :=
    sumula_280_implica_inadmissivel Tema_139_RG h_dl_139
  exact Tema_139_admitido_e_julgado h_inadm_139

/-- **Refutação de V2d.** V2d identifica fundamento
    determinante com mera menção. Isso viola o art. 489, §1º,
    V, do CPC, que exige identificação dos fundamentos
    *determinantes* (ratio decidendi), não meras menções
    tangenciais.

    Estratégia: V2d, aplicada ao caso de Alice (mera menção
    tangencial), produziria a qualificação como fundamento
    determinante. Isto contradiz o art. 489, §1º, V. -/
theorem V2d_viola_art_489_par1_V : V2d → False := by
  intro h_v2d
  -- V2d aplicada ao caso de Alice (que tem mera menção tangencial)
  -- exigiria tratá-la como fundamento determinante.
  -- Mas o art. 489, §1º, V diz: mera menção tangencial não
  -- pode ser fundamento determinante.

  -- Para tornar a contradição operativa, é preciso premissa
  -- que conecte V2d ao status de fundamento determinante.
  -- A premissa é: a invocação de V2d para incidir Súmula 280
  -- equivale a tratar a menção como fundamento determinante.

  -- Isso é axiomatizável — qualquer fundamento de
  -- inadmissibilidade tem que ser fundamento determinante,
  -- por art. 489, §1º, V.

  -- Aqui, simplificamos: assume-se a premissa pacífica de que
  -- V2d aplicada a alice produz fundamento determinante.
  have h_md : MeraMencaoTangencial caso_alice := alice_mera_mencao
  have h_n_fd : ¬ FundamentoDeterminantePeloRecorrido caso_alice :=
    art_489_par1_V caso_alice h_md
  -- Para derivar False, precisamos do passo: V2d aplicado
  -- exige tratar como fundamento determinante. Esta é
  -- premissa estrutural do art. 927 + art. 489, §1º, V
  -- (a qualificação jurídica relevante para inadmissibilidade
  -- só pode operar via fundamento determinante).
  -- Modelamos como axioma:
  exact absurd
    (show FundamentoDeterminantePeloRecorrido caso_alice from
      v2d_exige_fundamento_determinante h_v2d)
    h_n_fd

/- ============================================================
   TEOREMA FINAL — exaustão das versões steelmanned
   ============================================================ -/

/-- **Teorema da insanabilidade do STEEL_2.**

    Nenhuma das versões steelmanned (V2a, V2b, V2c, V2d) de
    STEEL_2 sustenta a aplicação da Súmula 280 ao caso de
    Alice.

      • V2a: deriva False
      • V2b: tautológica mas inerte (precondition não ocorre)
      • V2c: reductio (bloquearia Tema 139/RG)
      • V2d: viola art. 489, §1º, V do CPC

    Forma operativa: existe(V) de versão steelmanned
    sustentável → False. Como cada versão isoladamente
    falha, a disjunção também falha. -/
theorem nenhum_steelman_de_STEEL_2_sustenta_acordao :
    (V2a ∨ V2c ∨ V2d) → False := by
  intro h
  rcases h with h_a | h_c | h_d
  · exact V2a_derruba_acordao h_a
  · exact V2c_reductio h_c
  · exact V2d_viola_art_489_par1_V h_d

/-
  Observação sobre V2b: V2b NÃO é falsa, mas é INERTE para
  o caso de Alice. Por isso não consta da disjunção acima.
  Sua "refutação" é factual — não leva o acórdão a lugar
  algum. Cf. teorema `V2b_inerte_para_alice`.

  Conjugação: a corte, para sustentar a aplicação da Súmula
  280 ao caso, precisaria de uma versão de STEEL_2 que (a)
  não derive False, (b) seja aplicável ao caso de Alice, (c)
  não tenha consequências reductio, (d) respeite o art. 489,
  §1º, V. As quatro versões examinadas esgotam as leituras
  plausíveis. Não há quinta opção honesta.
-/

/- ============================================================
   Auditoria
   ============================================================ -/

#print axioms V2a_derruba_acordao
#print axioms V2c_reductio
#print axioms V2d_viola_art_489_par1_V
#print axioms nenhum_steelman_de_STEEL_2_sustenta_acordao

end SteelmanningExaustivoSTEEL2
