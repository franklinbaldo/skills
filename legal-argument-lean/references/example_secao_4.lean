/-
  Embargos de Declaração — ARE 1.589.466/RO
  Formalização da Seção 4 (Inaplicabilidade da Súmula 279/STF)

  Estrutura por camadas:
    1. Tipos básicos (universo do discurso)
    2. Predicados opacos (qualificações jurídicas não-dedutivas)
    3. Normas processuais (axiomas duros)
    4. Precedentes (axiomas nomeados com citação)
    5. Fatos do caso (claims extraídos do acórdão recorrido)
    6. Teorema (a tese da peça)
-/

namespace EmbargosAlice.Secao4

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

/-- O caso depende de revolvimento do conjunto fático-probatório. -/
axiom DependeReexameProbatorio : Caso → Prop

/-- Os fatos relevantes do caso são incontroversos
    (assentados pela própria decisão recorrida). -/
axiom FatosIncontroversos : Caso → Prop

/-- A controvérsia versa apenas sobre a qualificação jurídica
    de fatos já assentados, sem reabertura instrutória. -/
axiom ApenasQualificacaoJuridica : Caso → Prop

/-- A Súmula 279/STF é aplicável ao caso, obstando o
    conhecimento do recurso extraordinário. -/
axiom AplicaSumula279 : Caso → Prop

/- ============================================================
   Camada 3 — Normas processuais
   --
   Axiomas duros. Não se prova o conteúdo da Súmula 279; ele é
   constitutivo do sistema processual.
   ============================================================ -/

/-- Súmula 279/STF: "Para simples reexame de prova não cabe
    recurso extraordinário."

    Formalmente: a aplicação da súmula equivale, por definição,
    à dependência de reexame probatório. -/
axiom sumula_279_definicao :
    ∀ (c : Caso), AplicaSumula279 c ↔ DependeReexameProbatorio c

/- ============================================================
   Camada 4 — Precedentes
   --
   Cada precedente é um axioma nomeado, com citação no
   docstring. A "prova" jurisprudencial é, no plano formal, a
   afirmação do próprio STF — não há derivação.
   ============================================================ -/

/-- **RE 210.917**, Rel. Min. Sepúlveda Pertence, Tribunal Pleno.

    Distinção entre reexame de prova (vedado) e qualificação
    jurídica de fatos incontroversos (admitida em sede
    extraordinária). -/
axiom RE_210_917 :
    ∀ (c : Caso),
      FatosIncontroversos c →
      ApenasQualificacaoJuridica c →
      ¬ DependeReexameProbatorio c

/-- **RE 845.779-RG**, Rel. Min. Roberto Barroso.

    Reafirma que o enquadramento jurídico de fatos
    incontroversos afasta o óbice da Súmula 279/STF. -/
axiom RE_845_779_RG :
    ∀ (c : Caso),
      FatosIncontroversos c →
      ApenasQualificacaoJuridica c →
      ¬ AplicaSumula279 c

/-- **RE 450.971-AgR**, Rel. Min. Ricardo Lewandowski.

    "A Súmula 279 revela-se inaplicável quando os fatos da
    causa são incontroversos, tendo o Tribunal a quo atribuído
    a eles consequências jurídicas discrepantes do entendimento
    desta Corte." -/
axiom RE_450_971_AgR :
    ∀ (c : Caso),
      FatosIncontroversos c → ¬ AplicaSumula279 c

/- ============================================================
   Camada 5 — Fatos do caso concreto (claims)
   --
   Cada axioma desta seção é um *claim* extraído da peça,
   ancorado no acórdão da 1ª TR-RO. Não é norma; é asserção
   sobre o caso. A escolha de marcá-los como `axiom` (e não
   provar) é honesta: o que justifica o claim é a leitura do
   acórdão, não uma derivação interna ao sistema.
   ============================================================ -/

/-- O caso de Alice Crispim da Silva (ARE 1.589.466/RO). -/
axiom caso_alice : Caso

/-- **Claim factual.** O voto condutor do acórdão da 1ª Turma
    Recursal de Rondônia assenta textualmente os fatos
    relevantes:
      (i) contribuições vertidas ao RGPS de 1987 a 2012;
      (ii) posse em cargo efetivo estatutário em maio/2012.

    Tais fatos não foram impugnados em nenhuma fase do
    processo. -/
axiom alice_fatos_incontroversos : FatosIncontroversos caso_alice

/-- **Claim factual.** A controvérsia constitucional reside
    exclusivamente na qualificação jurídica desses fatos —
    isto é, em definir se o exercício de atividade celetista
    no setor público, com filiação ao RGPS, equivale a
    "ingresso no serviço público" para fins do art. 3º da
    EC 47/2005. Não há reabertura instrutória. -/
axiom alice_apenas_qualificacao : ApenasQualificacaoJuridica caso_alice

/- ============================================================
   Camada 6 — Teorema
   --
   A tese da Seção 4 da peça: a Súmula 279/STF é inaplicável
   ao caso. Duas provas independentes, refletindo a estrutura
   argumentativa da peça (que invoca múltiplos precedentes
   convergentes).
   ============================================================ -/

/-- **Tese da Seção 4.** A Súmula 279/STF não incide sobre o
    caso de Alice, porque os fatos são incontroversos e a
    controvérsia versa apenas sobre qualificação jurídica.

    Prova via RE 210.917 (Pertence) + definição da Súmula 279. -/
theorem sumula_279_inaplicavel : ¬ AplicaSumula279 caso_alice := by
  rw [sumula_279_definicao]
  exact RE_210_917 caso_alice
    alice_fatos_incontroversos
    alice_apenas_qualificacao

/-- **Tese da Seção 4 — prova alternativa.** Mesma conclusão,
    via RE 845.779-RG (Barroso), que enuncia diretamente a
    inaplicabilidade da Súmula 279 (sem mediação pela
    definição). -/
theorem sumula_279_inaplicavel' : ¬ AplicaSumula279 caso_alice :=
  RE_845_779_RG caso_alice
    alice_fatos_incontroversos
    alice_apenas_qualificacao

/-- **Tese da Seção 4 — prova mais econômica.** Via
    RE 450.971-AgR (Lewandowski), que dispensa o segundo claim
    (basta a incontrovérsia dos fatos). -/
theorem sumula_279_inaplicavel'' : ¬ AplicaSumula279 caso_alice :=
  RE_450_971_AgR caso_alice alice_fatos_incontroversos

/- ============================================================
   Auditoria — quais axiomas cada prova consome?
   --
   `#print axioms` lista os axiomas de que cada teorema
   depende. Isso é a contrapartida formal do "ônus
   argumentativo": cada teorema declara, sem ambiguidade,
   sobre que autoridade jurídica e que claim factual repousa.
   ============================================================ -/

#print axioms sumula_279_inaplicavel
#print axioms sumula_279_inaplicavel'
#print axioms sumula_279_inaplicavel''

end EmbargosAlice.Secao4
