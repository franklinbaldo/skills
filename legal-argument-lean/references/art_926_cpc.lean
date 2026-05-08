import Tipos
import Saidas.Aplicar
import Saidas.Distinguir
import Saidas.Superar

/-
  ============================================================
  ART. 926 DO CPC — UNIFORMIZAÇÃO DA JURISPRUDÊNCIA
  ============================================================

  Disciplina o dever do tribunal de manter coerência de sua
  PRÓPRIA jurisprudência: estabilidade, integridade, coerência
  entre decisões.

  Cobertura:
    • art. 926 caput: dever de uniformização e três princípios
    • art. 926, §1º: edição de súmulas
    • art. 926, §2º: súmulas devem ater-se às circunstâncias

  ARQUITETURA. Importa as três traits de saída (Aplicar,
  Distinguir, Superar) e DERIVA — não postula — a partição
  das saídas legítimas como teorema.

  ESCOPO DA SAÍDA "SUPERAR" SOB ART. 926.

  Sob art. 926, o tribunal trabalha com sua própria
  jurisprudência. É portanto tribunal-fonte de toda decisão
  que confronta. A saída "superar" disponível é a SUPERAÇÃO
  PLENA (overruling robusto), com fundamentação adequada e
  específica e observância de segurança jurídica e proteção
  da confiança (art. 927, §4º, aplicável por analogia).

  Não há, sob art. 926, espaço autônomo para
  `SuperaRacionalmente` (saída específica do tribunal vinculado
  sob art. 927): quando o tribunal-fonte supera com argumento
  racional, está realizando overruling pleno por definição. As
  duas figuras coincidem extensionalmente nesse regime.

  Tampouco há espaço para `ReconheceSuperacaoExterna`: o
  tribunal-fonte não reconhece superação alheia da própria
  jurisprudência — supera-a diretamente.

  ATENÇÃO — escopo material do art. 926.

  O art. 926 NÃO disciplina:
    (a) precedente de tribunal superior — incidência do
        art. 927, CPC;
    (b) contradição intra-decisão (um único acórdão sustentando
        proposições incompatíveis) — incidência do art. 1.022,
        I, CPC, conjugado com art. 489, §1º, V, CPC.

  Não invocar o art. 926 nessas duas hipóteses evita exposição
  de flanco argumentativo na peça (resposta possível: "o art.
  926 trata de jurisprudência do próprio tribunal, não dessa
  hipótese").
-/

namespace CPC.Art926

open Comum
open Saidas.Aplicar
open Saidas.Distinguir
open Saidas.Superar

/- ============================================================
   Camada 1 — Tipos específicos do art. 926
   ============================================================ -/

axiom Jurisprudencia : Type
axiom Sumula : Type

/- ============================================================
   Camada 2 — Predicados auxiliares
   ============================================================ -/

axiom Estavel : Jurisprudencia → Prop
axiom Integra : Jurisprudencia → Prop
axiom Coerente : Jurisprudencia → Prop
axiom JurisprudenciaDe : Tribunal → Jurisprudencia → Prop
axiom DecisaoDe : Decisao → Tribunal → Prop
axiom IntegraJurisprudencia : Decisao → Jurisprudencia → Prop
axiom JurisprudenciaDoTribunal : Precedente → Tribunal → Prop
axiom MateriaAnaloga : Decisao → Decisao → Prop
axiom SustentaTese : Decisao → Prop → Prop
axiom Fundamentada : Decisao → Prop
axiom InvocaJurisprudenciaPropria : Decisao → Precedente → Prop
axiom AtemSeCircunstanciasFaticas : Sumula → Prop

/- ============================================================
   Camada 3 — Normas (axiomas do art. 926)
   ============================================================ -/

/-- **Art. 926, caput.** Os tribunais devem uniformizar sua
    jurisprudência e mantê-la estável, íntegra e coerente. -/
axiom art_926_caput :
    ∀ (t : Tribunal) (j : Jurisprudencia),
      JurisprudenciaDe t j →
      Estavel j ∧ Integra j ∧ Coerente j

/-- **Art. 926, §2º.** Ao editar enunciados de súmula, os
    tribunais devem ater-se às circunstâncias fáticas dos
    precedentes que motivaram sua criação. -/
axiom art_926_par2 :
    ∀ (s : Sumula), AtemSeCircunstanciasFaticas s

/-- **Coerência entre decisões.** Tribunal cuja jurisprudência
    inclua decisões com teses incompatíveis sobre matéria
    análoga viola o dever de coerência. -/
axiom violacao_coerencia_jurisprudencial :
    ∀ (t : Tribunal) (j : Jurisprudencia)
      (d1 d2 : Decisao) (te1 te2 : Prop),
      JurisprudenciaDe t j →
      DecisaoDe d1 t →
      DecisaoDe d2 t →
      IntegraJurisprudencia d1 j →
      IntegraJurisprudencia d2 j →
      MateriaAnaloga d1 d2 →
      SustentaTese d1 te1 →
      SustentaTese d2 te2 →
      te1 ≠ te2 →
      ¬ Coerente j

/-- **Vinculação à própria jurisprudência.** Decisão fundamentada
    que invoca precedente próprio do tribunal está obrigada a
    cumprir os requisitos de aplicação correta (Saidas.Aplicar). -/
axiom art_926_aplicacao_propria :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      JurisprudenciaDoTribunal p t →
      InvocaJurisprudenciaPropria d p →
      Fundamentada d →
      AplicaCorretamente d p

/-- **Afastamento da própria jurisprudência.** Decisão
    fundamentada que se afasta de jurisprudência própria do
    tribunal está obrigada a distinguir corretamente OU
    superar plenamente (saída plena disponível porque o
    tribunal é tribunal-fonte). -/
axiom art_926_afastamento_proprio :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      JurisprudenciaDoTribunal p t →
      ¬ InvocaJurisprudenciaPropria d p →
      Fundamentada d →
      DistingueCorretamente d p ∨ SuperaPlenamente d p

/-- **Cobertura.** Toda decisão fundamentada que enfrente
    precedente próprio do tribunal ou o invoca, ou se afasta
    dele. -/
axiom invoca_ou_afasta_propria :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      JurisprudenciaDoTribunal p t →
      Fundamentada d →
      InvocaJurisprudenciaPropria d p ∨ ¬ InvocaJurisprudenciaPropria d p

/- ============================================================
   Camada 4 — TEOREMA DA PARTIÇÃO DAS SAÍDAS LEGÍTIMAS
   --
   Análogo ao teorema do art. 927, mas com saída "superar"
   plena (não há ReconheceSuperacaoExterna porque tribunal
   próprio NÃO reconhece superação externa de sua própria
   jurisprudência — ele a supera diretamente).
   ============================================================ -/

/-- **Partição das saídas legítimas diante de jurisprudência
    do próprio tribunal** (art. 926).

    Tribunal fundamentado que confronta sua própria
    jurisprudência está obrigado a uma de três saídas:
      1. aplicar corretamente;
      2. distinguir corretamente;
      3. superar plenamente (overruling robusto).

    NÃO há saída "reconhece superação externa" sob art. 926
    porque o tribunal é tribunal-fonte; superação superveniente
    é figura típica de regime de vinculação a tribunal superior
    (cf. art. 927). -/
theorem saidas_legitimas_jurisprudencia_propria :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      JurisprudenciaDoTribunal p t →
      Fundamentada d →
      AplicaCorretamente d p ∨
      DistingueCorretamente d p ∨
      SuperaPlenamente d p := by
  intros d p t h_decde h_jur h_fund
  have h_inv_ou_n :
      InvocaJurisprudenciaPropria d p ∨ ¬ InvocaJurisprudenciaPropria d p :=
    invoca_ou_afasta_propria d p t h_decde h_jur h_fund
  rcases h_inv_ou_n with h_inv | h_n_inv
  · -- caso 1: invoca → aplica
    left
    exact art_926_aplicacao_propria d p t h_decde h_jur h_inv h_fund
  · -- caso 2: não invoca → distingue ou supera plenamente
    right
    exact art_926_afastamento_proprio d p t h_decde h_jur h_n_inv h_fund

/-- **Contrapositiva — saída fora do espaço legítimo.** -/
theorem fora_do_espaco_legitimo_proprio_nao_fundamentada :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      DecisaoDe d t →
      JurisprudenciaDoTribunal p t →
      ¬ AplicaCorretamente d p →
      ¬ DistingueCorretamente d p →
      ¬ SuperaPlenamente d p →
      ¬ Fundamentada d := by
  intros d p t h_decde h_jur h_n_apl h_n_dist h_n_sup h_fund
  have h_alguma : AplicaCorretamente d p ∨ DistingueCorretamente d p ∨
                  SuperaPlenamente d p :=
    saidas_legitimas_jurisprudencia_propria d p t h_decde h_jur h_fund
  rcases h_alguma with h | h | h
  · exact h_n_apl h
  · exact h_n_dist h
  · exact h_n_sup h

end CPC.Art926
