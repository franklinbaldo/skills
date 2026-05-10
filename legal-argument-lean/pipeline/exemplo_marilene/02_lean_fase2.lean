import Tipos
import Saidas.Aplicar
import Saidas.Distinguir
import Saidas.Superar
import art_927_cpc

/-
  ============================================================
  EXEMPLO RETROATIVO — CASO M.B. (ANONIMIZADO)
  Apelação 7003XXX-XX.2024.8.22.0010
  IPERON × M.B., TJRO, 2ª Câmara Especial, 29/04/2026
  ============================================================

  Formalização Lean 4 dos cinco vícios identificados no acórdão.
  Cada teorema corresponde a um ataque da Fase 2 do pipeline.

  Compilar com:
    cd legal-argument-lean/pipeline/exemplo_marilene
    LEAN_PATH=../../references lean 02_lean_fase2.lean

  Os cinco #print axioms ao final produzem a auditoria para a
  Fase 3 (análise subjetiva).
-/

namespace ExemploMB

open Comum
open Saidas.Aplicar
open Saidas.Distinguir
open Saidas.Superar
open CPC.Art927

/- ============================================================
   Camada 1 — Tipos básicos do caso
   ============================================================ -/

axiom servidora_mb : Servidor
axiom cargo_supervisao_escolar : Cargo
axiom acordao_tjro : Decisao
axiom adi_3772 : Precedente
axiom tjro : Tribunal

/- ============================================================
   Camada 2 — Predicados opacos do caso
   ============================================================ -/

/-- Cargo se enquadra como "professor de carreira" para fins da ratio
    da ADI 3.772 (carreiras efetivamente docentes, não especialistas). -/
axiom ProfessorDeCarreira : Servidor → Cargo → Prop

/-- Cargo é, na origem, de "especialista em educação" — categoria
    expressamente excluída da ratio da ADI 3.772 pela sua ementa. -/
axiom EspecialistaEmEducacao : Servidor → Cargo → Prop

/-- O acórdão expressamente afirma uma proposição P (por transcrição
    ou declaração direta). -/
axiom AcordaoAfirma : Decisao → Prop → Prop

/-- O acórdão efetivamente nega P ao não aplicar consequência que P
    implicaria — operacionaliza a contradição implícita. -/
axiom AcordaoNega : Decisao → Prop → Prop

/-- A decisão enfrenta argumentativamente um fundamento adverso. -/
axiom EnfrentaArgumento : Decisao → Prop → Prop

/- ============================================================
   Camada 3 — Pressupostos sistêmicos
   ============================================================ -/

/-- A ADI 3.772 é precedente de controle concentrado do STF,
    vinculante nos termos do art. 927, I, CPC. -/
axiom adi_3772_controle_concentrado :
    DecisaoControleConcentradoSTF adi_3772

/-- O TJRO não é tribunal-fonte do precedente ADI 3.772 (cujo
    tribunal-fonte é o STF). -/
axiom tjro_nao_fonte_adi_3772 : ¬ EhTribunalFonte tjro adi_3772

/- ============================================================
   Camada 4 — Normas e precedentes
   ============================================================ -/

/-- **ADI 3.772/STF — ratio completa** (Tribunal Pleno, rel. Min.
    Carlos Britto). A acumulação de cargo de professor com outro
    cargo técnico ou científico é lícita apenas quando AMBOS OS
    CARGOS SÃO DE PROFESSOR DE CARREIRA. Especialistas em educação
    estão expressamente excluídos da autorização. -/
axiom ADI_3772_ratio :
    ∀ (s : Servidor) (c : Cargo),
      EspecialistaEmEducacao s c →
      ¬ ProfessorDeCarreira s c

/-- **Contradição por afirmação e negação simultâneas.** Axioma
    estrutural: decisão que afirma e nega a mesma proposição é
    internamente contraditória (art. 1.022, I, CPC). -/
axiom contradicao_afirmacao_negacao :
    ∀ (d : Decisao) (P : Prop),
      AcordaoAfirma d P → AcordaoNega d P → False

/- ============================================================
   Camada 5 — Fatos do caso
   ============================================================ -/

/-- M.B. foi nomeada originariamente como Especialista em Supervisão
    Escolar pelo Decreto 7.999/1997 (posse em 23.03.1998). O cargo
    é de especialista em educação nos termos da ementa da ADI 3.772.
    A LC 680/2012 reenquadrou o cargo para Professora Classe C, mas
    não alterou a natureza originária da nomeação. -/
axiom mb_eh_especialista :
    EspecialistaEmEducacao servidora_mb cargo_supervisao_escolar

/-- O voto transcreve a ementa da ADI 3.772 em sua integralidade —
    incluindo a ressalva "excluídos os especialistas em educação" —
    como premissa reconhecida. -/
axiom acordao_transcreve_ressalva :
    AcordaoAfirma acordao_tjro
      (EspecialistaEmEducacao servidora_mb cargo_supervisao_escolar →
       ¬ ProfessorDeCarreira servidora_mb cargo_supervisao_escolar)

/-- O voto, na sequência da transcrição, aplica a ratio ao caso de
    M.B. reconhecendo a acumulação como lícita, sem ressalva sobre
    o fato de ela ter sido nomeada como especialista em educação —
    negando assim, na prática, a proposição que acabou de afirmar. -/
axiom acordao_aplica_sem_ressalva :
    AcordaoNega acordao_tjro
      (EspecialistaEmEducacao servidora_mb cargo_supervisao_escolar →
       ¬ ProfessorDeCarreira servidora_mb cargo_supervisao_escolar)

/-- O TJRO invocou a ADI 3.772 como fundamento de sua decisão. -/
axiom tjro_fundamenta_em_adi : FundamentaSeEm acordao_tjro adi_3772

/-- O TJRO não aplicou corretamente o precedente: não identificou os
    fundamentos determinantes da ADI 3.772 nem demonstrou o ajuste
    do caso concreto a esses fundamentos (art. 489, §1º, V, CPC). -/
axiom tjro_nao_aplica_corretamente :
    ¬ AplicaCorretamente acordao_tjro adi_3772

/-- O TJRO não realizou distinção: não identificou diferença
    substantiva entre o caso e o precedente que justificasse
    afastamento (art. 489, §1º, VI, CPC). -/
axiom tjro_nao_distingue :
    ¬ DistingueCorretamente acordao_tjro adi_3772

/-- O TJRO não reconheceu superação superveniente do precedente
    pelo STF. -/
axiom tjro_nao_reconhece_superacao :
    ¬ ReconheceSuperacaoExterna acordao_tjro adi_3772

/-- O TJRO não realizou superação racional com ônus argumentativo
    qualificado (não apontou erro expresso na ratio da ADI 3.772,
    não demonstrou irracionalidade interna). -/
axiom tjro_nao_supera_racionalmente :
    ¬ SuperaRacionalmente acordao_tjro adi_3772

/-- Os regimes constitucionais do art. 37, XVI, CF (acumulação) e
    do art. 40, §5º, CF (aposentadoria de professor) são materialmente
    autônomos — proposição constitucional relevante para o caso. -/
axiom regimes_constitucionais_distintos : Prop

/-- O acórdão não enfrentou a questão da autonomia dos regimes
    constitucionais, embora o IPERON a tenha suscitado. -/
axiom acordao_omite_autonomia_regimes :
    ¬ EnfrentaArgumento acordao_tjro regimes_constitucionais_distintos

/-- O IPERON invocou o Parecer Prévio TCE-RO PPL-TC 00027/19 como
    fundamento contrário à acumulação — proposição deduzida nos autos. -/
axiom iperon_invocou_parecer_tce : Prop

/-- O acórdão não menciona e não enfrenta o Parecer PPL-TC 00027/19. -/
axiom acordao_omite_parecer_tce :
    ¬ EnfrentaArgumento acordao_tjro iperon_invocou_parecer_tce

/- ============================================================
   Camada 6 — Teoremas (um por ataque da Fase 2)
   ============================================================ -/

/-- **ATAQUE 1 — Omissão da ressalva expressa da ADI 3.772.**

    A ratio da ADI 3.772, em sua versão completa (Warrant completo da
    Fase 1), exclui expressamente especialistas em educação. M.B. foi
    nomeada como Especialista em Supervisão Escolar. Logo, a ratio não
    ampara a acumulação: M.B. não é "professor de carreira" para os fins
    em que a ADI 3.772 define a licitude.

    O acórdão omitiu pronunciamento sobre o ponto capaz de infirmar:
    que a ressalva, transcrita em sua ementa integral, alcança o caso
    concreto. -/
theorem ataque_1_ressalva_da_ADI :
    ¬ ProfessorDeCarreira servidora_mb cargo_supervisao_escolar :=
  ADI_3772_ratio servidora_mb cargo_supervisao_escolar mb_eh_especialista

/-- **ATAQUE 2 — Contradição interna entre premissa transcrita e
    conclusão sustentada.**

    O acórdão afirma (via transcrição integral da ementa) que
    especialistas em educação não são professores de carreira para fins
    da ADI 3.772 e, simultaneamente, aplica a ratio ao caso de M.B.
    sem ressalva, negando esse mesmo enunciado. A contradição interna
    é literal: `AcordaoAfirma d P ∧ AcordaoNega d P → False`. -/
theorem ataque_2_contradicao_interna : False :=
  contradicao_afirmacao_negacao acordao_tjro
    (EspecialistaEmEducacao servidora_mb cargo_supervisao_escolar →
     ¬ ProfessorDeCarreira servidora_mb cargo_supervisao_escolar)
    acordao_transcreve_ressalva
    acordao_aplica_sem_ressalva

/-- **ATAQUE 3 — Aplicação seletiva de precedente vinculante.**

    O TJRO invocou a ADI 3.772 (precedente vinculante de controle
    concentrado, art. 927, I, CPC) sem realizar nenhuma das cinco
    saídas legítimas disponíveis a tribunal vinculado: não aplicou
    corretamente, não distinguiu, não pode superar plenamente (não é
    tribunal-fonte), não reconheceu superação superveniente, não superou
    racionalmente. Portanto, a decisão não está fundamentada. -/
theorem ataque_3_aplicacao_seletiva :
    ¬ Fundamentada acordao_tjro :=
  fora_do_espaco_legitimo_nao_fundamentada
    acordao_tjro adi_3772
    (art_927_I adi_3772 adi_3772_controle_concentrado)
    (Or.inl tjro_fundamenta_em_adi)
    tjro_nao_aplica_corretamente
    tjro_nao_distingue
    (apenas_tribunal_fonte_supera_plenamente tjro_nao_fonte_adi_3772)
    tjro_nao_reconhece_superacao
    tjro_nao_supera_racionalmente

/-- **ATAQUE 4 — Omissão sobre autonomia dos regimes constitucionais.**

    O acórdão não enfrentou a questão da distinção entre o regime do
    art. 37, XVI, CF (acumulação de cargos) e o regime do art. 40, §5º,
    CF (aposentadoria de professor), embora o IPERON a tenha suscitado
    como fundamento autônomo contrário à acumulação. A omissão recai
    sobre ponto capaz de infirmar a conclusão. -/
theorem ataque_4_autonomia_regimes :
    ¬ EnfrentaArgumento acordao_tjro regimes_constitucionais_distintos :=
  acordao_omite_autonomia_regimes

/-- **ATAQUE 5 — Omissão sobre o Parecer Prévio TCE-RO.**

    O acórdão não enfrentou o Parecer Prévio PPL-TC 00027/19 do
    TCE-RO, invocado pelo IPERON como fundamento contrário autônomo
    à acumulação. Fundamento deduzido pela parte e capaz de infirmar
    a conclusão não enfrentado configura omissão (art. 1.022, I, c/c
    art. 489, §1º, IV, CPC). -/
theorem ataque_5_omissao_TCE :
    ¬ EnfrentaArgumento acordao_tjro iperon_invocou_parecer_tce :=
  acordao_omite_parecer_tce

/- ============================================================
   Auditoria de axiomas — insumo para a Fase 3
   ============================================================ -/

#print axioms ataque_1_ressalva_da_ADI
#print axioms ataque_2_contradicao_interna
#print axioms ataque_3_aplicacao_seletiva
#print axioms ataque_4_autonomia_regimes
#print axioms ataque_5_omissao_TCE

end ExemploMB
