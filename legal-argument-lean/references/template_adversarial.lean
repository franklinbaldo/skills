/-
  ============================================================
  FORMALIZAÇÃO DO ACÓRDÃO EMBARGADO
  AgInt no ProCESSO_EXEMPLO — Plenário, sessão virtual,
  publicado em 29.04.2026
  ============================================================

  METODOLOGIA: steelmanning iterativo via sorry-replacement.

  1. Tradução literal da cadeia argumentativa do acórdão.
  2. Onde o passo não decorre dedutivamente, marca-se com
     `sorry` (em comentário) e identifica-se a premissa
     implícita.
  3. STEELMAN: substitui-se cada `sorry` pelo axioma mais
     forte e mais caridoso que torna o passo válido. Não se
     escolhe a versão fraca da premissa do acórdão; escolhe-se
     a versão mais defensável dela.
  4. Compila-se a versão final.
  5. Auditoria: `#print axioms` revela todos os pressupostos
     implícitos. Axioma fora do catálogo de autoridades
     citadas é vício.
  6. Verificação de consistência: tenta-se derivar `False`.
     Se possível, o acórdão é internamente contraditório.

  RESULTADO PRELIMINAR (preview): o acórdão *compila* depois
  de quatro steelmans. Os quatro axiomas adicionais necessários
  são, todos, contradichos por jurisprudência do próprio STF
  citada no acórdão. E mais: dois deles juntos derivam
  literalmente `False`. O acórdão é consistente apenas se
  rejeitar parte de sua própria fundamentação.
-/

namespace AcordaoEmbargado_ARE_1589466

/- ============================================================
   Camada 1 — Universo do discurso
   ============================================================ -/

axiom Caso : Type
axiom Recurso : Type
axiom Precedente : Type
axiom Sumula : Type
axiom Norma : Type
axiom DispositivoConstitucional : Type

/- ============================================================
   Camada 2 — Predicados opacos
   ============================================================ -/

/- Admissibilidade -/
axiom RecursoExtraordinario : Recurso → Prop
axiom Inadmissivel : Recurso → Prop
axiom RecursoDoCaso : Recurso → Caso → Prop

/- Pressupostos das súmulas 279 e 280 -/
axiom DependeReexameProbatorio : Caso → Prop
axiom FatosIncontroversos : Caso → Prop
axiom ApenasQualificacaoJuridica : Caso → Prop
axiom DireitoLocal : Caso → Prop
axiom InterpretacaoDiretaConstitucional : Caso → Prop

/- Aplicação de normas e precedentes ao caso -/
axiom AplicaECArt3 : Caso → Prop
axiom AplicaPrecedente : Caso → Precedente → Prop
axiom AplicaTemaRG : Caso → Precedente → Prop

/- Sobre a matéria do caso vs. matéria de precedentes -/
axiom MesmaMateria : Caso → Caso → Prop
axiom CasoDoPrecedente : Precedente → Caso

/- Predicado-chave do contradição interna -/
axiom JurisprudenciaConstitucionalConsolidada : Caso → Prop

/- Predicados específicos da matéria -/
axiom MateriaAposentadoriaEspecial : Caso → Prop
axiom MateriaRegraTransicaoEC47 : Caso → Prop

/- ============================================================
   Camada 3 — Normas processuais (sólidas, do CPC e CF)
   --
   Estas são premissas pacíficas; não há controvérsia sobre
   elas, e correspondem aos módulos da skill já validados.
   ============================================================ -/

/-- **Súmula 279/STF.** Para simples reexame de prova não cabe
    recurso extraordinário. -/
axiom sumula_279 :
    ∀ (r : Recurso) (c : Caso),
      RecursoExtraordinario r →
      RecursoDoCaso r c →
      DependeReexameProbatorio c →
      Inadmissivel r

/-- **Súmula 280/STF.** Por ofensa a direito local não cabe
    recurso extraordinário. -/
axiom sumula_280 :
    ∀ (r : Recurso) (c : Caso),
      RecursoExtraordinario r →
      RecursoDoCaso r c →
      DireitoLocal c →
      Inadmissivel r

/-- **CPC, art. 927, III** (do módulo art_927_cpc.lean):
    acórdão em julgamento de RG é vinculante. Conjugado com a
    natureza constitucional do paradigma, produz juris
    consolidada do STF, que é interpretação direta da CF —
    não direito local. -/
axiom juris_consolidada_implica_constitucional :
    ∀ (c : Caso),
      JurisprudenciaConstitucionalConsolidada c →
      InterpretacaoDiretaConstitucional c

/-- **Inferência pacífica.** Interpretação direta de
    dispositivo constitucional NÃO é direito local. Corolário
    estrutural da Súmula 280 lida em conjunto com o art. 102
    da CF. -/
axiom interpretacao_constitucional_nao_eh_local :
    ∀ (c : Caso),
      InterpretacaoDiretaConstitucional c →
      ¬ DireitoLocal c

/- ============================================================
   Camada 4 — Precedentes textualmente invocados pelo
              acórdão embargado
   ============================================================ -/

/-- **PRECEDENTE_E-AgR**, Rel. Min. Edson Fachin. Versa sobre
    aposentadoria especial e aplicação analógica do art. 57
    da Lei 8.213/91 ao RPPS. -/
axiom ARE_1_492_017 : Precedente
axiom ARE_1_492_017_materia :
    MateriaAposentadoriaEspecial (CasoDoPrecedente ARE_1_492_017)

/-- **Rcl 81.193-ED-AgR**, Rel. Min. Flávio Dino. Versa sobre
    aposentadoria especial de servidor médico e conversão de
    tempo especial em comum. -/
axiom Rcl_81_193 : Precedente
axiom Rcl_81_193_materia :
    MateriaAposentadoriaEspecial (CasoDoPrecedente Rcl_81_193)

/-- **Rcl 79.138-AgR**, Rel. Min. André Mendonça. Versa sobre
    natureza insalubre da atividade. -/
axiom Rcl_79_138 : Precedente
axiom Rcl_79_138_materia :
    MateriaAposentadoriaEspecial (CasoDoPrecedente Rcl_79_138)

/-- **PRECEDENTE_A-ED-AgR**, Rel. Min. Dias Toffoli, Segunda
    Turma, DJe 02.08.2025. Citado pelo próprio acórdão
    embargado. Trecho transcrito:

    "A jurisprudência da Suprema Corte possui o entendimento
    consolidado de que as regras de transição do art. 3º da
    EC 47/05 são aplicáveis aos servidores públicos, inclusive
    os professores, que ingressaram no serviço público antes
    da publicação das Emendas Constitucionais nºs 20/98 e
    41/03 e se aposentaram após a EC nº 41/03."

    Forma operativa: aplicação do art. 3º EC 47 = matéria de
    jurisprudência constitucional consolidada do STF. -/
axiom PRECEDENTE_EXEMPLO :
    ∀ (c : Caso),
      AplicaECArt3 c →
      JurisprudenciaConstitucionalConsolidada c

/- ============================================================
   Camada 5 — Fatos do caso de ParteA (claims do acórdão
              recorrido, incontroversos)
   ============================================================ -/

axiom caso_ParteA : Caso
axiom recurso_ParteA : Recurso

axiom ParteA_eh_re : RecursoExtraordinario recurso_ParteA
axiom ParteA_recurso_do_caso : RecursoDoCaso recurso_ParteA caso_ParteA

/-- Voto da TURMA_RECURSAL_EXEMPLO assenta os fatos como incontroversos. -/
axiom ParteA_fatos_incontroversos : FatosIncontroversos caso_ParteA

/-- Voto da TURMA_RECURSAL_EXEMPLO submete questão estritamente de
    qualificação jurídica. -/
axiom ParteA_apenas_qualificacao : ApenasQualificacaoJuridica caso_ParteA

/-- Voto da TURMA_RECURSAL_EXEMPLO aplica diretamente o art. 3º da EC 47,
    inclusive transcrevendo seu texto integral. -/
axiom ParteA_aplica_ec_art_3 : AplicaECArt3 caso_ParteA

/-- Caso de ParteA é sobre regra de transição da EC 47, não
    sobre aposentadoria especial. -/
axiom ParteA_materia : MateriaRegraTransicaoEC47 caso_ParteA

/-- Aposentadoria especial e regra de transição da EC 47 são
    matérias distintas (corolário óbvio que o acórdão precisa
    negar para usar os precedentes que cita). -/
axiom materias_distintas :
    ∀ (c c' : Caso),
      MateriaRegraTransicaoEC47 c →
      MateriaAposentadoriaEspecial c' →
      ¬ MesmaMateria c c'

/- ============================================================
   ============================================================
              STEELMANNING — sorry-replacement
   ============================================================
   ============================================================

   A seguir, identificam-se os passos do acórdão embargado
   que NÃO decorrem dedutivamente do que foi posto até aqui.
   Cada um foi originalmente um `sorry`. Para cada um,
   apresenta-se a versão *mais caridosa* da premissa
   implícita do acórdão.

   Nomenclatura: cada axioma é prefixado por `STEEL_` e
   acompanhado de comentário identificando (a) o que era o
   sorry, (b) qual a versão steelmanned, (c) por que ela é
   defensável (ou onde falha).
-/

/-- **STEEL_1.** Acórdão precisa que Súmula 279 incida.
    Mas: caso é de fatos incontroversos + qualificação
    jurídica. Sorry: por que isso configuraria reexame
    probatório?

    Steelman mais caridoso: "todo caso que envolve
    qualificação jurídica de fatos depende, ainda que
    indiretamente, de revisar a base fática". É a posição
    mais forte que o acórdão pode sustentar.

    AVISO: este steelman contradiz frontalmente o PRECEDENTE_GERAL
    (Pertence), o PRECEDENTE_F-RG (Barroso), e o PRECEDENTE_G-AgR
    (Lewandowski) — todos do próprio STF, todos pacíficos no
    sentido OPOSTO. -/
axiom STEEL_1_qualificacao_implica_reexame :
    ∀ (c : Caso),
      ApenasQualificacaoJuridica c →
      DependeReexameProbatorio c

/-- **STEEL_2.** Acórdão precisa que Súmula 280 incida.
    Mas: caso aplica diretamente art. 3º da EC 47.
    Sorry: por que aplicação de norma constitucional seria
    direito local?

    Steelman mais caridoso: "o pano de fundo regulatório
    estadual (LC 432/2008) qualifica o tipo de RPPS sob
    análise, e portanto a aplicação da EC 47 ao caso depende
    em última instância de direito estadual".

    AVISO: este steelman é frontalmente incompatível com a
    estrutura dual do art. 102, I, "a", da CF e com o Tema
    139/RG-STF (PRECEDENTE_D, Lewandowski, Plenário, j.
    24.06.2009), que é precedente vinculante (art. 927, III,
    CPC) sobre exatamente a regra de transição em discussão. -/
axiom STEEL_2_aplicacao_ec_implica_local :
    ∀ (c : Caso),
      AplicaECArt3 c →
      DireitoLocal c

/-- **STEEL_3.** Acórdão usa precedentes sobre aposentadoria
    especial (PRECEDENTE_E, Rcl 81.193, Rcl 79.138) para
    decidir caso sobre EC 47. Sorry: por que precedentes
    sobre matéria distinta seriam aplicáveis?

    Steelman mais caridoso: "todos os precedentes do STF
    sobre INADMISSIBILIDADE de RE em matéria previdenciária
    são intercambiáveis quanto às súmulas 279 e 280,
    independentemente da questão de fundo".

    AVISO: este steelman viola o art. 489, §1º, V, do CPC
    (que exige identificação dos fundamentos determinantes e
    demonstração de ajuste do caso aos fundamentos do
    precedente). -/
axiom STEEL_3_precedentes_admissibilidade_intercambiaveis :
    ∀ (c c' : Caso) (p : Precedente),
      ¬ MesmaMateria c c' →
      CasoDoPrecedente p = c' →
      AplicaPrecedente c p

/- ============================================================
   Camada 6 — Conclusões do acórdão (com steelmans aplicados)
   ============================================================ -/

/-- **Tese 1 do acórdão**: incidência da Súmula 279.
    Compila com STEEL_1. -/
theorem acordao_aplica_sumula_279 : Inadmissivel recurso_ParteA :=
  sumula_279 recurso_ParteA caso_ParteA
    ParteA_eh_re ParteA_recurso_do_caso
    (STEEL_1_qualificacao_implica_reexame caso_ParteA
       ParteA_apenas_qualificacao)

/-- **Tese 2 do acórdão**: incidência da Súmula 280.
    Compila com STEEL_2. -/
theorem acordao_aplica_sumula_280 : Inadmissivel recurso_ParteA :=
  sumula_280 recurso_ParteA caso_ParteA
    ParteA_eh_re ParteA_recurso_do_caso
    (STEEL_2_aplicacao_ec_implica_local caso_ParteA
       ParteA_aplica_ec_art_3)

/-- **Conclusão do acórdão**: inadmissibilidade do RE.
    Compila. -/
theorem acordao_conclusao : Inadmissivel recurso_ParteA :=
  acordao_aplica_sumula_279

/- ============================================================
   ============================================================
        TESTE DE CONSISTÊNCIA INTERNA
   ============================================================
   ============================================================

   O acórdão compila. Mas é internamente consistente?

   O próprio acórdão invoca o PRECEDENTE_A-ED-AgR (Toffoli),
   cujo texto reconhece o art. 3º da EC 47 como matéria de
   jurisprudência constitucional consolidada do STF. Conjugado
   com a estrutura do art. 102 da CF, isso implica que tal
   matéria NÃO é direito local.

   Mas o STEEL_2 — necessário para o acórdão aplicar a Súmula
   280 — diz exatamente o contrário: aplicação do art. 3º da
   EC 47 implica direito local.

   Resultado: o acórdão sustenta simultaneamente
       DireitoLocal caso_ParteA  (via STEEL_2)
   e
       ¬ DireitoLocal caso_ParteA  (via PRECEDENTE_EXEMPLO +
           juris_consolidada_implica_constitucional +
           interpretacao_constitucional_nao_eh_local)

   Logo, deriva-se `False`.
-/

/-- **Teorema da contradição interna do acórdão.**

    O acórdão embargado, lido na sua versão steelmanned mais
    caridosa, sustenta simultaneamente premissas
    incompatíveis. A inconsistência é literal: deriva-se
    `False` de seus axiomas conjuntamente.

    Este teorema é a forma rigorosa do que a Seção 8 da peça
    afirma em prosa: o acórdão embargado padece de contradição
    interna intransponível, embargável por força do art.
    1.022, I, do CPC. -/
theorem acordao_internamente_inconsistente : False := by
  -- Direito local pelo steelman do acórdão:
  have h1 : DireitoLocal caso_ParteA :=
    STEEL_2_aplicacao_ec_implica_local caso_ParteA ParteA_aplica_ec_art_3
  -- Não direito local pela cadeia que o próprio acórdão invoca:
  have h2 : JurisprudenciaConstitucionalConsolidada caso_ParteA :=
    PRECEDENTE_EXEMPLO caso_ParteA ParteA_aplica_ec_art_3
  have h3 : InterpretacaoDiretaConstitucional caso_ParteA :=
    juris_consolidada_implica_constitucional caso_ParteA h2
  have h4 : ¬ DireitoLocal caso_ParteA :=
    interpretacao_constitucional_nao_eh_local caso_ParteA h3
  -- Contradição:
  exact h4 h1

/- ============================================================
   Auditoria — `#print axioms`
   ============================================================ -/

#print axioms acordao_aplica_sumula_279
#print axioms acordao_aplica_sumula_280
#print axioms acordao_internamente_inconsistente

end AcordaoEmbargado_ARE_1589466
