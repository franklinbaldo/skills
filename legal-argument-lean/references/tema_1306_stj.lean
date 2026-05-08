/-
  Axiomas padrão — Tema 1306/STJ
  Fundamentação por Referência (per relationem)

  Recurso Repetitivo — Tema 1306/STJ
  REsp 2.148.059/MA, REsp 2.148.580/MA, REsp 2.150.218/MA
  Rel. Min. Luis Felipe Salomão
  Corte Especial, julgamento em 20.08.2025
  ED da FEBRABAN rejeitados; teses mantidas sem alteração.

  Este módulo formaliza não apenas as duas teses fixadas,
  mas o INTEIRO TEOR das razões de decidir, incluindo:

    • Distinção doutrinária pura vs. integrativa
    • Apoio em Tema 339 da Repercussão Geral (STF)
    • Interpretação conjunta art. 1.021, §3º + art. 489, §1º, IV
    • Esclarecimento dos ED da FEBRABAN sobre o alcance de "novo"
    • Aplicação ao caso paradigma (transcrição ipsis litteris da
      sentença sem rebater elementos fáticos)

  Compõe-se naturalmente com `art_489_cpc.lean`. As declarações
  de tipo (Decisao, Argumento) e os predicados centrais
  (Fundamentada, Nula) são compatíveis em nome — em uso
  conjunto, basta declará-los uma vez.
-/

namespace STJ.Tema1306

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

axiom Decisao : Type
axiom DecisaoAnterior : Type
axiom Argumento : Type
axiom Documento : Type
axiom Parecer : Type

/- ============================================================
   Camada 2 — Predicados opacos
   ============================================================ -/

axiom Fundamentada : Decisao → Prop
axiom Nula : Decisao → Prop

/-- A decisão usa fundamentação por referência (per relationem
    ou por remissão), reproduzindo motivações de uma decisão
    anterior, documento ou parecer. -/
axiom UsaPerRelationem : Decisao → DecisaoAnterior → Prop

/-- A decisão enfrenta — ainda que sucintamente — as novas
    questões relevantes para o julgamento. Predicado central
    da Tese 1: é a *condição* da validade da per relationem. -/
axiom EnfrentaQuestoesNovasRelevantes : Decisao → Prop

/-- A decisão analisa pormenorizadamente cada alegação ou
    prova. A Tese 1 expressamente DISPENSA esta exigência. -/
axiom AnalisaPormenorizadamente : Decisao → Prop

/-- O argumento é novo e relevante em relação à decisão
    anterior encampada pelo julgador. -/
axiom ApresentaArgumentoNovoRelevante : Argumento → Decisao → Prop

/-- O argumento foi sopesado pela decisão anterior. -/
axiom SopesadoAnteriormente : Argumento → DecisaoAnterior → Prop

/-- A decisão é um agravo interno (art. 1.021 CPC). -/
axiom IsAgravoInterno : Decisao → Prop

/- Distinção doutrinária recepcionada na ratio decidendi -/

/-- Per relationem PURA ou EXCLUSIVA: mera reprodução de
    decisão anterior sem análise dos fundamentos do recurso.
    Doutrinariamente inválida. -/
axiom PerRelationemPura : Decisao → Prop

/-- Per relationem INTEGRATIVA ou MODERADA: transcrição
    acompanhada de efetivo exame dos argumentos recursais.
    Doutrinariamente válida. -/
axiom PerRelationemIntegrativa : Decisao → Prop

/- ============================================================
   Camada 4 — Tema 1306/STJ
   --
   Teses fixadas + razões de decidir do inteiro teor.
   ============================================================ -/

/-- **Tese 1 do Tema 1306/STJ.** A técnica da fundamentação
    por referência (per relationem) é permitida desde que o
    julgador, ao reproduzir trechos de decisão anterior
    (documentos e/ou pareceres) como razões de decidir,
    enfrente, ainda que de forma sucinta, as novas questões
    relevantes para o julgamento do processo, dispensada a
    análise pormenorizada de cada uma das alegações ou provas.

    Forma bidirecional: per relationem é fundamentada SE E
    SOMENTE SE enfrenta questões novas relevantes. -/
axiom tema_1306_tese_1 :
    ∀ (d : Decisao) (anterior : DecisaoAnterior),
      UsaPerRelationem d anterior →
      (Fundamentada d ↔ EnfrentaQuestoesNovasRelevantes d)

/-- **Tese 2 do Tema 1306/STJ.** O § 3º do art. 1.021 do CPC
    não impede a reprodução dos fundamentos da decisão
    agravada como razões de decidir pela negativa de
    provimento de agravo interno quando a parte deixa de
    apresentar argumento novo para ser apreciado pelo
    colegiado.

    Interpretação conjunta com art. 489, §1º, IV: se não há
    argumento novo, não há "argumento deduzido capaz de
    infirmar a conclusão" não enfrentado. -/
axiom tema_1306_tese_2 :
    ∀ (d : Decisao) (anterior : DecisaoAnterior),
      IsAgravoInterno d →
      UsaPerRelationem d anterior →
      (∀ a : Argumento, ¬ ApresentaArgumentoNovoRelevante a d) →
      Fundamentada d

/- ============================================================
   Razões de decidir — inteiro teor
   ============================================================ -/

/-- **Distinção doutrinária acolhida (razão de decidir).**
    A per relationem PURA é, por si só, inválida.
    Voto condutor: "a fundamentação 'por cópia', sem qualquer
    diálogo com as razões recursais, não satisfaz [o direito da
    parte] e torna a decisão nula". -/
axiom tema_1306_per_relationem_pura_invalida :
    ∀ (d : Decisao), PerRelationemPura d → ¬ Fundamentada d

/-- **Distinção doutrinária acolhida (razão de decidir).**
    A per relationem INTEGRATIVA — transcrição acompanhada de
    efetivo exame dos argumentos — é válida desde que enfrente
    as questões novas relevantes. -/
axiom tema_1306_per_relationem_integrativa_valida :
    ∀ (d : Decisao),
      PerRelationemIntegrativa d →
      EnfrentaQuestoesNovasRelevantes d →
      Fundamentada d

/-- **Apoio jurisprudencial expresso no acórdão.**
    A validade da per relationem é reconhecida pelo STF no
    Tema 339 da Repercussão Geral (AI 791.292 QO-RG/PE,
    Rel. Min. Gilmar Mendes, Tribunal Pleno, j. 23.06.2010,
    DJe 13.08.2010), reafirmado pelo Plenário em RE 1.397.056
    ED-AgR/MA (Rel. Min. Rosa Weber, Tribunal Pleno,
    j. 13.03.2023, DJe 28.03.2023).

    Núcleo: validade quando há "compatibilidade entre o que
    alegado e o entendimento fixado pelo órgão julgador",
    dispensado o exame pormenorizado. -/
axiom tema_339_rg_stf :
    ∀ (d : Decisao) (anterior : DecisaoAnterior),
      UsaPerRelationem d anterior →
      EnfrentaQuestoesNovasRelevantes d →
      Fundamentada d

/-- **Esclarecimento dos ED da FEBRABAN (razão de decidir).**
    O alcance do termo "novo" nas teses fixadas NÃO afasta o
    dever geral de motivação. Quando a parte apresenta
    argumento RELEVANTE não sopesado pela decisão anterior
    encampada pelo julgador, a validade da per relationem
    condiciona-se a justificação específica adicional, por
    força do art. 489, §1º, IV, do CPC.

    Em forma de implicação: se há argumento novo relevante não
    previamente sopesado, a fundamentação só é válida se este
    argumento for efetivamente enfrentado. -/
axiom tema_1306_ed_febraban_alcance_novo :
    ∀ (d : Decisao) (anterior : DecisaoAnterior) (a : Argumento),
      UsaPerRelationem d anterior →
      ApresentaArgumentoNovoRelevante a d →
      ¬ SopesadoAnteriormente a anterior →
      (Fundamentada d → EnfrentaQuestoesNovasRelevantes d)

/-- **Aplicação ao caso paradigma (REsp 2.148.059/MA).**
    O TJMA limitou-se a transcrever ipsis litteris a sentença
    de improcedência sem rebater elementos fáticos suscitados
    pela autora — indícios concretos de fraude (endereço
    diverso do contrato, crédito em conta de terceiro,
    assinatura desconhecida). Apesar de instado por agravo
    interno e embargos de declaração, o Tribunal manteve-se
    silente. Resultado: negativa de prestação jurisdicional →
    nulidade do acórdão estadual; cassação e retorno para
    rejulgamento; afastamento da multa do § 2º do art. 1.026
    do CPC.

    Generalização: per relationem pura, mantida silente após
    agravo interno e ED, configura negativa de prestação
    jurisdicional → nulidade. -/
axiom tema_1306_caso_paradigma :
    ∀ (d : Decisao),
      PerRelationemPura d →
      (∃ a : Argumento, ApresentaArgumentoNovoRelevante a d ∧
                        ¬ EnfrentaQuestoesNovasRelevantes d) →
      Nula d

/- ============================================================
   Lemas derivados (úteis em peças)
   ============================================================ -/

/-- Per relationem que NÃO enfrenta questões novas relevantes
    é não-fundamentada. Decorre diretamente da Tese 1 (lado
    necessário do bicondicional). -/
theorem nao_fundamentada_se_nao_enfrenta :
    ∀ (d : Decisao) (anterior : DecisaoAnterior),
      UsaPerRelationem d anterior →
      ¬ EnfrentaQuestoesNovasRelevantes d →
      ¬ Fundamentada d := by
  intros d anterior h_per h_nao_enfrenta h_fund
  have h_iff := tema_1306_tese_1 d anterior h_per
  exact h_nao_enfrenta (h_iff.mp h_fund)

/-- Reductio ao caso paradigma: per relationem pura com
    argumento novo relevante não enfrentado é caso típico de
    nulidade conforme o REsp 2.148.059/MA. -/
theorem nulidade_per_relationem_pura :
    ∀ (d : Decisao) (a : Argumento),
      PerRelationemPura d →
      ApresentaArgumentoNovoRelevante a d →
      ¬ EnfrentaQuestoesNovasRelevantes d →
      Nula d := by
  intros d a h_pura h_novo h_nao_enfrenta
  exact tema_1306_caso_paradigma d h_pura ⟨a, h_novo, h_nao_enfrenta⟩

end STJ.Tema1306
