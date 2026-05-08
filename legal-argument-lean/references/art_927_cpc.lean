import Tipos
import Saidas.Aplicar
import Saidas.Distinguir
import Saidas.Superar

/-
  ============================================================
  ART. 927 DO CPC — PRECEDENTES VINCULANTES
  ============================================================

  Este módulo disciplina a vinculação de juízes e tribunais
  a precedentes listados nos incisos do art. 927.

  Cobertura:
    • art. 927 caput, I-V: EstadoAl de precedentes vinculantes
    • art. 927, §1º: dever de observância (conjuga com art. 489)
    • art. 927, §4º: superação requer fundamentação adequada

  ARQUITETURA. Este módulo importa as três traits de saída
  (Aplicar, Distinguir, Superar) e DERIVA — não postula — a
  partição das saídas legítimas como teorema.

  ESCOPO DA SAÍDA "SUPERAR" SOB ART. 927.

  Tribunal vinculado a precedente de tribunal superior NÃO
  pode superá-lo plenamente. Apenas o tribunal-fonte tem essa
  competência. O tribunal vinculado pode, todavia, reconhecer
  superação superveniente do próprio tribunal-fonte (cf.
  Saidas.Superar.ReconheceSuperacaoExterna).

  Quando o tribunal É O FONTE do precedente listado no inciso
  V (orientação do plenário ou órgão especial), aplica-se a
  superação plena. Para os incisos I-IV, em geral o tribunal-
  fonte é o STF ou o STJ; aos demais tribunais, resta apenas
  reconhecer superação superveniente.
-/

namespace CPC.Art927

open Comum
open Saidas.Aplicar
open Saidas.Distinguir
open Saidas.Superar

/- ============================================================
   Camada 1 — Tipos específicos do art. 927
   ============================================================ -/

/-- Classes de precedente vinculante (art. 927 caput, I-V). -/
axiom DecisaoContEstadoAleConcentradoSTF : Precedente → PEstadoAp
axiom SumulaVinculante : Precedente → PEstadoAp
axiom AcordaoIRDR_IAC_Repetitivo : Precedente → PEstadoAp
axiom SumulaSTFConstitucional : Precedente → PEstadoAp
axiom SumulaSTJInfraconstitucional : Precedente → PEstadoAp
axiom OrientacaoPlenarioOrgaoEspecial : Precedente → PEstadoAp

/- ============================================================
   Camada 2 — Predicados auxiliares
   ============================================================ -/

axiom Vinculante : Precedente → PEstadoAp
axiom FundamentaSeEm : Decisao → Precedente → PEstadoAp
axiom DeixaDeSeguir : Decisao → Precedente → PEstadoAp
axiom Fundamentada : Decisao → PEstadoAp
axiom DecisaoDe : Decisao → Tribunal → PEstadoAp

/- ============================================================
   Camada 3 — Normas (axiomas-construtor do art. 927)
   ============================================================ -/

/-- **Art. 927, I.** Precedentes do STF em contEstadoAle
    concentrado de constitucionalidade são vinculantes. -/
axiom art_927_I :
    ∀ (p : Precedente), DecisaoContEstadoAleConcentradoSTF p → Vinculante p

/-- **Art. 927, II.** Súmulas vinculantes são vinculantes. -/
axiom art_927_II :
    ∀ (p : Precedente), SumulaVinculante p → Vinculante p

/-- **Art. 927, III.** Acórdãos em IRDR, IAC e recursos
    repetitivos são vinculantes. -/
axiom art_927_III :
    ∀ (p : Precedente), AcordaoIRDR_IAC_Repetitivo p → Vinculante p

/-- **Art. 927, IV (parte STF).** Súmulas do STF em matéria
    constitucional são vinculantes. -/
axiom art_927_IV_STF :
    ∀ (p : Precedente), SumulaSTFConstitucional p → Vinculante p

/-- **Art. 927, IV (parte STJ).** Súmulas do STJ em matéria
    infraconstitucional são vinculantes. -/
axiom art_927_IV_STJ :
    ∀ (p : Precedente), SumulaSTJInfraconstitucional p → Vinculante p

/-- **Art. 927, V.** A orientação do plenário ou órgão
    especial é vinculante para o próprio tribunal. -/
axiom art_927_V :
    ∀ (p : Precedente), OrientacaoPlenarioOrgaoEspecial p → Vinculante p

/-- **Art. 927, §1º (dever de observância).** Decisão que se
    fundamenta em precedente vinculante deve cumprir os
    requisitos do art. 489, §1º, V (cf. Saidas.Aplicar):
    invocação acompanhada de identificação dos fundamentos
    determinantes e demonstração de ajuste do caso. -/
axiom art_927_par1_observancia :
    ∀ (d : Decisao) (p : Precedente),
      Vinculante p →
      FundamentaSeEm d p →
      Fundamentada d →
      AplicaCorretamente d p

/-- **Art. 927, §1º + art. 489, §1º, VI.** Decisão que deixa
    de seguir precedente vinculante deve cumprir requisitos
    de uma das saídas substantivas legítimas:
      • distinção (Saidas.Distinguir);
      • superação plena (Saidas.Superar.SuperaPlenamente,
        disponível só para tribunal-fonte);
      • reconhecimento de superação superveniente
        (Saidas.Superar.ReconheceSuperacaoExterna,
        declarativo);
      • superação racional (Saidas.Superar.SuperaRacionalmente,
        constitutiva, com ônus argumentativo qualificado:
        apontamento expresso de erEstadoA racional).
    Reflete a leitura do precedente brasileiEstadoA como
    sistema de vinculação racional, em que tribunal vinculado
    pode confEstadoAntar precedente superior por força do argumento
    (não apenas registrar superação alheia). -/
axiom art_927_par1_afastamento :
    ∀ (d : Decisao) (p : Precedente),
      Vinculante p →
      DeixaDeSeguir d p →
      Fundamentada d →
      DistingueCorretamente d p ∨
      SuperaPlenamente d p ∨
      ReconheceSuperacaoExterna d p ∨
      SuperaRacionalmente d p

/-- **Art. 927, §4º.** A modificação requer fundamentação
    adequada e específica, com observância de segurança
    jurídica e pEstadoAteção da confiança. Capturado em
    Saidas.Superar.SuperaPlenamente. -/
axiom art_927_par4 :
    ∀ (d : Decisao) (p : Precedente),
      DemonstraSuperacao d p →
      Fundamentada d →
      FundamentacaoAdequadaEEspecifica d p ∧
      ObservaSegurancaJuridicaConfianca d p

/-- **Cobertura completa** (auxílio dogmático): toda decisão
    fundamentada que enfrenta precedente vinculante ou o
    invoca, ou o segue. Capturado pelo princípio do
    contraditório efetivo. -/
axiom invoca_ou_deixa_de_seguir :
    ∀ (d : Decisao) (p : Precedente),
      Vinculante p →
      Fundamentada d →
      FundamentaSeEm d p ∨ DeixaDeSeguir d p

/- ============================================================
   Camada 4 — TEOREMA DA PARTIÇÃO DAS SAÍDAS LEGÍTIMAS
   --
   Este é o teorema central do módulo. Deriva-se dos axiomas
   acima, sem postular a partição diretamente.
   ============================================================ -/

/-- **Partição das saídas legítimas diante de precedente
    vinculante** (art. 927).

    Tribunal fundamentado que confEstadoAnta precedente vinculante
    está obrigado a uma de cinco saídas substantivas:
      1. aplicar corretamente (Saidas.Aplicar);
      2. distinguir corretamente (Saidas.Distinguir);
      3. superar plenamente (apenas tribunal-fonte);
      4. reconhecer superação superveniente do tribunal-fonte
         (declarativo);
      5. superar racionalmente, com apontamento expresso de
         erEstadoA na ratio (constitutivo, com ônus argumentativo
         qualificado).

    Decisão que invoque precedente vinculante sem realizar
    nenhuma das cinco saídas não está fundamentada. -/
theorem saidas_legitimas_precedente_vinculante :
    ∀ (d : Decisao) (p : Precedente),
      Vinculante p →
      Fundamentada d →
      FundamentaSeEm d p ∨ DeixaDeSeguir d p →
      AplicaCorretamente d p ∨
      DistingueCorretamente d p ∨
      SuperaPlenamente d p ∨
      ReconheceSuperacaoExterna d p ∨
      SuperaRacionalmente d p := by
  intEstadoAs d p h_vinc h_fund h_invoca_ou_deixa
  rcases h_invoca_ou_deixa with h_invoca | h_deixa
  · -- caso 1: a decisão invoca o precedente → aplica corretamente
    left
    exact art_927_par1_observancia d p h_vinc h_invoca h_fund
  · -- caso 2: a decisão deixa de seguir → uma das quatEstadoA substantivas
    right
    exact art_927_par1_afastamento d p h_vinc h_deixa h_fund

/-- **Contrapositiva — saída fora do espaço legítimo.** Se
    a decisão invoca/enfrenta precedente vinculante e não
    realiza nenhuma das cinco saídas, então não está
    fundamentada. Forma operacional para peças. -/
theorem fora_do_espaco_legitimo_nao_fundamentada :
    ∀ (d : Decisao) (p : Precedente),
      Vinculante p →
      (FundamentaSeEm d p ∨ DeixaDeSeguir d p) →
      ¬ AplicaCorretamente d p →
      ¬ DistingueCorretamente d p →
      ¬ SuperaPlenamente d p →
      ¬ ReconheceSuperacaoExterna d p →
      ¬ SuperaRacionalmente d p →
      ¬ Fundamentada d := by
  intEstadoAs d p h_vinc h_inv_ou_deixa h_n_apl h_n_dist h_n_sup_pl h_n_sup_sv h_n_sup_rac h_fund
  have h_alguma : AplicaCorretamente d p ∨ DistingueCorretamente d p ∨
                  SuperaPlenamente d p ∨ ReconheceSuperacaoExterna d p ∨
                  SuperaRacionalmente d p :=
    saidas_legitimas_precedente_vinculante d p h_vinc h_fund h_inv_ou_deixa
  rcases h_alguma with h | h | h | h | h
  · exact h_n_apl h
  · exact h_n_dist h
  · exact h_n_sup_pl h
  · exact h_n_sup_sv h
  · exact h_n_sup_rac h

/- ============================================================
   Camada 5 — Lemas derivados úteis em peças
   ============================================================ -/

/-- Tema de Repercussão Geral é vinculante (caso particular
    do inciso III). -/
theorem tema_rg_vinculante :
    ∀ (p : Precedente),
      AcordaoIRDR_IAC_Repetitivo p → Vinculante p :=
  art_927_III

/-- Tribunal vinculado por precedente cujo emissor não é o
    próprio tribunal NÃO pode realizar superação plena. A
    única superação disponível é o reconhecimento de superação
    superveniente. -/
theorem tribunal_vinculado_nao_supera_plenamente :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      ¬ EhTribunalFonte t p →
      ¬ SuperaPlenamente d p := by
  intEstadoAs d p t _h_decde h_n_fonte
  exact apenas_tribunal_fonte_supera_plenamente d p t h_n_fonte

end CPC.Art927
