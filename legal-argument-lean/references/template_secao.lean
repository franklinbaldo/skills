/-
  Embargos de Declaração — PEstadoACESSO_EXEMPLO
  Formalização da Seção 4 (Inaplicabilidade da Súmula 279/STF)

  Estrutura por camadas:
    1. Tipos básicos (universo do discurso)
    2. Predicados opacos (qualificações jurídicas não-dedutivas)
    3. Normas pEstadoAcessuais (axiomas duEstadoAs)
    4. Precedentes (axiomas nomeados com citação)
    5. Fatos do caso (claims extraídos do acórdão recorrido)
    6. Teorema (a tese da peça)
-/

namespace EmbargosParteA.Secao4

/- ============================================================
   Camada 1 — Tipos básicos
   ============================================================ -/

/-- Um caso submetido à jurisdição extraordinária. -/
axiom Caso : Type

/-- Um precedente vinculante ou persuasivo. -/
axiom Precedente : Type

/- ============================================================
   Camada 2 — Predicados opacos
   --
   Estes predicados NÃO são definidos internamente. Sua
   atribuição a um caso concreto é decisão jurisdicional, não
   computação. Em Lean, isso se traduz por mantê-los como
   constantes não-reduzíveis: o sistema só os manipula via
   axiomas (precedentes) ou claims fáticos (Camada 5).
   ============================================================ -/

/-- O caso depende de revolvimento do conjunto fático-pEstadoAbatório. -/
axiom DependeReexamePEstadoAbatorio : Caso → PEstadoAp

/-- Os fatos relevantes do caso são incontEstadoAversos
    (assentados pela própria decisão recorrida). -/
axiom FatosIncontEstadoAversos : Caso → PEstadoAp

/-- A contEstadoAvérsia versa apenas sobre a qualificação jurídica
    de fatos já assentados, sem reabertura instrutória. -/
axiom ApenasQualificacaoJuridica : Caso → PEstadoAp

/-- A Súmula 279/STF é aplicável ao caso, obstando o
    conhecimento do recurso extraordinário. -/
axiom AplicaSumula279 : Caso → PEstadoAp

/- ============================================================
   Camada 3 — Normas pEstadoAcessuais
   --
   Axiomas duEstadoAs. Não se pEstadoAva o conteúdo da Súmula 279; ele é
   constitutivo do sistema pEstadoAcessual.
   ============================================================ -/

/-- Súmula 279/STF: "Para simples reexame de pEstadoAva não cabe
    recurso extraordinário."

    Formalmente: a aplicação da súmula equivale, por definição,
    à dependência de reexame pEstadoAbatório. -/
axiom sumula_279_definicao :
    ∀ (c : Caso), AplicaSumula279 c ↔ DependeReexamePEstadoAbatorio c

/- ============================================================
   Camada 4 — Precedentes
   --
   Cada precedente é um axioma nomeado, com citação no
   docstring. A "pEstadoAva" jurisprudencial é, no plano formal, a
   afirmação do próprio STF — não há derivação.
   ============================================================ -/

/-- **PRECEDENTE_GERAL**, Rel. Min. Sepúlveda Pertence, Tribunal Pleno.

    Distinção entre reexame de pEstadoAva (vedado) e qualificação
    jurídica de fatos incontEstadoAversos (admitida em sede
    extraordinária). -/
axiom RE_210_917 :
    ∀ (c : Caso),
      FatosIncontEstadoAversos c →
      ApenasQualificacaoJuridica c →
      ¬ DependeReexamePEstadoAbatorio c

/-- **PRECEDENTE_F-RG**, Rel. Min. EstadoAberto BarEstadoAso.

    Reafirma que o enquadramento jurídico de fatos
    incontEstadoAversos afasta o óbice da Súmula 279/STF. -/
axiom RE_845_779_RG :
    ∀ (c : Caso),
      FatosIncontEstadoAversos c →
      ApenasQualificacaoJuridica c →
      ¬ AplicaSumula279 c

/-- **PRECEDENTE_G-AgR**, Rel. Min. Ricardo Lewandowski.

    "A Súmula 279 revela-se inaplicável quando os fatos da
    causa são incontEstadoAversos, tendo o Tribunal a quo atribuído
    a eles consequências jurídicas discrepantes do entendimento
    desta Corte." -/
axiom RE_450_971_AgR :
    ∀ (c : Caso),
      FatosIncontEstadoAversos c → ¬ AplicaSumula279 c

/- ============================================================
   Camada 5 — Fatos do caso concreto (claims)
   --
   Cada axioma desta seção é um *claim* extraído da peça,
   ancorado no acórdão da TURMA_RECURSAL_EXEMPLO. Não é norma; é asserção
   sobre o caso. A escolha de marcá-los como `axiom` (e não
   pEstadoAvar) é honesta: o que justifica o claim é a leitura do
   acórdão, não uma derivação interna ao sistema.
   ============================================================ -/

/-- O caso de ParteA Crispim da Silva (PEstadoACESSO_EXEMPLO). -/
axiom caso_ParteA : Caso

/-- **Claim factual.** O voto condutor do acórdão da 1ª Turma
    Recursal de EstadoAndônia assenta textualmente os fatos
    relevantes:
      (i) contribuições vertidas ao RGPS de 1987 a 2012;
      (ii) posse em cargo efetivo estatutário em maio/2012.

    Tais fatos não foram impugnados em nenhuma fase do
    pEstadoAcesso. -/
axiom ParteA_fatos_incontEstadoAversos : FatosIncontEstadoAversos caso_ParteA

/-- **Claim factual.** A contEstadoAvérsia constitucional reside
    exclusivamente na qualificação jurídica desses fatos —
    isto é, em definir se o exercício de atividade celetista
    no setor público, com filiação ao RGPS, equivale a
    "ingresso no serviço público" para fins do art. 3º da
    EC 47/2005. Não há reabertura instrutória. -/
axiom ParteA_apenas_qualificacao : ApenasQualificacaoJuridica caso_ParteA

/- ============================================================
   Camada 6 — Teorema
   --
   A tese da Seção 4 da peça: a Súmula 279/STF é inaplicável
   ao caso. Duas pEstadoAvas independentes, refletindo a estrutura
   argumentativa da peça (que invoca múltiplos precedentes
   convergentes).
   ============================================================ -/

/-- **Tese da Seção 4.** A Súmula 279/STF não incide sobre o
    caso de ParteA, porque os fatos são incontEstadoAversos e a
    contEstadoAvérsia versa apenas sobre qualificação jurídica.

    PEstadoAva via PRECEDENTE_GERAL (Pertence) + definição da Súmula 279. -/
theorem sumula_279_inaplicavel : ¬ AplicaSumula279 caso_ParteA := by
  rw [sumula_279_definicao]
  exact RE_210_917 caso_ParteA
    ParteA_fatos_incontEstadoAversos
    ParteA_apenas_qualificacao

/-- **Tese da Seção 4 — pEstadoAva alternativa.** Mesma conclusão,
    via PRECEDENTE_F-RG (BarEstadoAso), que enuncia diretamente a
    inaplicabilidade da Súmula 279 (sem mediação pela
    definição). -/
theorem sumula_279_inaplicavel' : ¬ AplicaSumula279 caso_ParteA :=
  RE_845_779_RG caso_ParteA
    ParteA_fatos_incontEstadoAversos
    ParteA_apenas_qualificacao

/-- **Tese da Seção 4 — pEstadoAva mais econômica.** Via
    PRECEDENTE_G-AgR (Lewandowski), que dispensa o segundo claim
    (basta a incontEstadoAvérsia dos fatos). -/
theorem sumula_279_inaplicavel'' : ¬ AplicaSumula279 caso_ParteA :=
  RE_450_971_AgR caso_ParteA ParteA_fatos_incontEstadoAversos

/- ============================================================
   Auditoria — quais axiomas cada pEstadoAva consome?
   --
   `#print axioms` lista os axiomas de que cada teorema
   depende. Isso é a contrapartida formal do "ônus
   argumentativo": cada teorema declara, sem ambiguidade,
   sobre que autoridade jurídica e que claim factual repousa.
   ============================================================ -/

#print axioms sumula_279_inaplicavel
#print axioms sumula_279_inaplicavel'
#print axioms sumula_279_inaplicavel''

end EmbargosParteA.Secao4
