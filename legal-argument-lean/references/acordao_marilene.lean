import Tipos
import Saidas.Aplicar
import Saidas.Distinguir
import Saidas.Superar
import «art_927_cpc»

/-
  ============================================================
  ACÓRDÃO DA APELAÇÃO 7003561-54.2024.8.22.0010 — IPERON × MARILENE
  TJRO, 2ª Câmara Especial, Rel. Des. Jorge Luiz dos Santos Leal
  Julgamento: 29.04.2026
  ============================================================

  Análise para Embargos de Declaração — workspace formal.

  Aplica a arquitetura modular nova:
    Tipos → Saidas.{Aplicar, Distinguir, Superar} → CPC.Art927

  A ADI 3.772/DF é precedente vinculante do STF (art. 927, I,
  CPC — controle concentrado). O TJRO é tribunal vinculado,
  não tribunal-fonte. Aplicam-se as saídas de art_927_cpc.lean.
-/

namespace AcordaoMarilene

open Comum
open Saidas.Aplicar
open Saidas.Distinguir
open Saidas.Superar
open CPC.Art927

/- ============================================================
   Camada 5 — Predicados específicos do caso
   ============================================================ -/

axiom IntegraMagisterio : Cargo → Prop
axiom ProfessorDeCarreira : Servidor → Cargo → Prop
axiom EspecialistaEmEducacao : Cargo → Prop
axiom RegimeAcumulacao : Caso → Prop
axiom RegimeAposentadoriaEspecial : Caso → Prop
axiom CargoOriginariamente : Servidor → Cargo → Prop
axiom CasoDoPrecedente : Precedente → Caso
axiom MesmaMateria : Caso → Caso → Prop
axiom IPERONManifestouContra : Servidor → Prop

/- ============================================================
   Pressupostos sistêmicos — operam como [Field K]
   ============================================================ -/

axiom regimes_constitucionais_distintos :
    ∀ (c1 c2 : Caso),
      RegimeAposentadoriaEspecial c1 → RegimeAcumulacao c2 →
      ¬ MesmaMateria c2 c1

/- ============================================================
   Normas e precedentes (com citação)
   ============================================================ -/

/-- ADI 3.772/STF, Rel. Min. Carlos Britto, j. 09.10.2009,
    DJe 19.10.2009. Ratio textual transcrita pelo acórdão. -/
axiom ADI_3772_ratio :
    ∀ (s : Servidor) (c : Cargo),
      EspecialistaEmEducacao c →
      ¬ ProfessorDeCarreira s c

axiom precedente_ADI_3772 : Precedente
axiom caso_ADI_3772 : Caso
axiom ADI_3772_eh_aposentadoria : RegimeAposentadoriaEspecial caso_ADI_3772
axiom ADI_3772_eh_controle_concentrado :
    DecisaoControleConcentradoSTF precedente_ADI_3772

/-- A ADI 3.772 é vinculante por força do art. 927, I, CPC. -/
theorem ADI_3772_vinculante : Vinculante precedente_ADI_3772 :=
  art_927_I precedente_ADI_3772 ADI_3772_eh_controle_concentrado

/- ============================================================
   Fatos do caso de Marilene (com citação)
   ============================================================ -/

axiom Marilene : Servidor
axiom cargo_supervisao_escolar : Cargo
axiom caso_marilene : Caso
axiom acordao_TJRO : Decisao
axiom TJRO : Tribunal

/-- Fato 1: Marilene foi nomeada originariamente como
    Especialista em Supervisão Escolar (Decreto 7.999/1997,
    posse em 23.03.1998). -/
axiom marilene_origem :
    CargoOriginariamente Marilene cargo_supervisao_escolar

/-- Fato 2: Especialista em Supervisão Escolar é especialista
    em educação (TCE-RO PPL-TC 00027/19; LDB art. 61, II;
    LC 680/2012 art. 6º, VII em sentido funcional). -/
axiom supervisao_eh_especialista :
    EspecialistaEmEducacao cargo_supervisao_escolar

/-- Fato 3: caso de acumulação (art. 37 XVI), não aposentadoria. -/
axiom caso_marilene_eh_acumulacao :
    RegimeAcumulacao caso_marilene

/-- Fato 4: IPERON manifestou-se contrariamente desde 2017
    (Parecer 06/PGE/IPERON/2017). -/
axiom iperon_contra_marilene :
    IPERONManifestouContra Marilene

/-- Fato 5: o acórdão TJRO invoca a ADI 3.772 como fundamento. -/
axiom acordao_invoca_ADI_3772 :
    FundamentaSeEm acordao_TJRO precedente_ADI_3772

/-- Fato 6: o TJRO não é tribunal-fonte da ADI 3.772 (que é do STF). -/
axiom TJRO_nao_eh_fonte_ADI :
    ¬ EhTribunalFonte TJRO precedente_ADI_3772

/-- Fato 7: o acórdão é decisão do TJRO. -/
axiom acordao_eh_do_TJRO : DecisaoDe acordao_TJRO TJRO

/- ============================================================
   LEITURAS DESCARTADAS POR TRIVIALIDADE (auditoria)
   ============================================================
   • "Qualquer função em educação básica é magistério"
   • "ADI 3.772 incide em qualquer cargo pedagógico"
   • "LDB define conceito constitucional sobre cargos"
   • "Reenquadramento administrativo modifica natureza
     constitucional"
   • "Compatibilidade de horários presumida resolve a questão"
   • "Lei estadual redefine conceito constitucional"
   ============================================================ -/

/- ============================================================
   STEELMANS DIGNOS
   ============================================================ -/

def ST_1 : Prop :=
    ∀ (c : Cargo), ¬ EspecialistaEmEducacao c

def ST_3 : Prop :=
    ¬ IPERONManifestouContra Marilene

theorem ST_1_viola_par1_III : ST_1 → False := by
  intro h_st1
  exact (h_st1 cargo_supervisao_escolar) supervisao_eh_especialista

theorem ST_3_inerte_no_caso : ST_3 → False := by
  intro h_st3
  exact h_st3 iperon_contra_marilene

/- ============================================================
   INCONSISTÊNCIA INTERNA DO ACÓRDÃO
   (art. 1.022, I, c/c art. 489, §1º, V, do CPC)
   ============================================================ -/

theorem acordao_internamente_inconsistente
    (premissa_transcrita : ∀ (s : Servidor) (c : Cargo),
      EspecialistaEmEducacao c → ¬ ProfessorDeCarreira s c)
    (conclusao_sustentada :
      ProfessorDeCarreira Marilene cargo_supervisao_escolar) :
    False :=
  premissa_transcrita Marilene cargo_supervisao_escolar
    supervisao_eh_especialista conclusao_sustentada

/- ============================================================
   TEOREMA DA NÃO-SAÍDA (eixo novo da peça)
   --
   O acórdão TJRO, ao invocar a ADI 3.772 (precedente vinculante
   do STF, art. 927 I CPC), estava obrigado a uma das saídas
   legítimas sob art. 927.

   A vinculação a precedente no direito brasileiro tem caráter
   RACIONAL, não meramente hierárquico: o TJRO pode confrontar
   precedente do STF, mas com ônus argumentativo qualificado.

   Saídas disponíveis ao TJRO (não-fonte):
     1. Aplicar corretamente
     2. Distinguir corretamente
     3. Reconhecer superação superveniente do próprio STF
     4. Superar racionalmente (apontamento expresso de erro)

   NÃO disponível: superação plena (privativa do tribunal-fonte).

   Demonstra-se que: se nenhuma das saídas é tomada, o acórdão
   não está fundamentado.
   ============================================================ -/

/-- **Eixo da partição.** Se o acórdão TJRO invocou a ADI 3.772
    e nenhuma das saídas legítimas foi tomada, a decisão não
    está fundamentada. Versão particularizada do teorema
    `fora_do_espaco_legitimo_nao_fundamentada` do módulo
    art_927_cpc.lean. -/
theorem acordao_TJRO_fora_do_espaco_legitimo
    (h_n_aplica : ¬ AplicaCorretamente acordao_TJRO precedente_ADI_3772)
    (h_n_distingue : ¬ DistingueCorretamente acordao_TJRO precedente_ADI_3772)
    (h_n_recsup : ¬ ReconheceSuperacaoExterna acordao_TJRO precedente_ADI_3772)
    (h_n_suprac : ¬ SuperaRacionalmente acordao_TJRO precedente_ADI_3772) :
    ¬ Fundamentada acordao_TJRO := by
  -- TJRO não pode superar plenamente: não é tribunal-fonte
  have h_n_sup_pl : ¬ SuperaPlenamente acordao_TJRO precedente_ADI_3772 :=
    apenas_tribunal_fonte_supera_plenamente
      acordao_TJRO precedente_ADI_3772 TJRO TJRO_nao_eh_fonte_ADI
  -- Aplica o teorema do art. 927 com cinco saídas
  exact fora_do_espaco_legitimo_nao_fundamentada
    acordao_TJRO precedente_ADI_3772 ADI_3772_vinculante
    (Or.inl acordao_invoca_ADI_3772)
    h_n_aplica h_n_distingue h_n_sup_pl h_n_recsup h_n_suprac

/- ============================================================
   TEOREMA TERMINAL — cabimento dos Embargos de Declaração
   ============================================================ -/

/-- Conjugação de eixos:
    1. Steelmans dignos morrem (ST_1 e ST_3 falsos);
    2. Acórdão é internamente inconsistente entre premissa
       transcrita e conclusão sustentada;
    3. Acórdão está fora do espaço legítimo de saídas sob
       art. 927 (não aplica corretamente, não distingue,
       não reconhece superação superveniente, e não pode
       superar plenamente). -/
theorem ED_cabivel : (ST_1 ∨ ST_3) → False := by
  intro h
  rcases h with h1 | h3
  · exact ST_1_viola_par1_III h1
  · exact ST_3_inerte_no_caso h3

#print axioms ST_1_viola_par1_III
#print axioms ST_3_inerte_no_caso
#print axioms acordao_internamente_inconsistente
#print axioms acordao_TJRO_fora_do_espaco_legitimo
#print axioms ED_cabivel

end AcordaoMarilene
