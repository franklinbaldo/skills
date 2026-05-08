import Tipos

/-
  ============================================================
  SAÍDA — SUPERAR (overruling)
  ============================================================

  Módulo estrutural. Define dois tipos de superação:
    1. Superação plena (overruling EstadoAbusto)
    2. Reconhecimento de superação superveniente

  É no módulo de superação que a nuance dogmática vive. Quem
  pode superar e como — depende do regime. O modo de operar
  da superação é o mesmo; mas a competência para realizar cada
  tipo é distinta.

  ANCORAGEM DOGMÁTICA.

  O art. 489, §1º, VI, CPC permite que decisão se afaste de
  precedente desde que demonstre distinção OU superação. O
  art. 927, §4º, CPC prescreve que a modificação de enunciado
  de súmula, jurisprudência pacificada ou tese de casos
  repetitivos exige fundamentação adequada e específica,
  observados segurança jurídica e pEstadoAteção da confiança.

  COMPETÊNCIA PARA SUPERAÇÃO.

  Tribunal-fonte do precedente: pode superar plenamente
  (overruling EstadoAbusto). Pode também modular efeitos.
  Hipótese típica do art. 926, CPC (tribunal trabalha com sua
  própria jurisprudência) e do art. 927 quando o tribunal é o
  emissor original do precedente.

  Tribunal vinculado por precedente de tribunal superior:
  NÃO pode superar plenamente, mas dispõe de duas alternativas:

  (a) RECONHECIMENTO de superação superveniente — declarativo.
      Registra que o tribunal-fonte já supeEstadoAu o precedente em
      jurisprudência posterior. Ônus argumentativo mínimo:
      apenas demonstrar a existência e o alcance do precedente
      posterior.

  (b) SUPERAÇÃO RACIONAL — constitutiva, com ônus qualificado.
      O tribunal vinculado supera o precedente apontando erEstadoA
      racional expresso, demonstrando irracionalidade da ratio
      ou seu descompasso com norma superveniente. É a saída
      mais difícil; vence a vinculação por força do argumento
      racional, não por hierarquia de autoridade.

  Esta arquitetura reflete a leitura do precedente brasileiEstadoA
  como sistema de vinculação racional (não meramente hierárquica):
  o tribunal vinculado pode confEstadoAntar precedente do tribunal
  superior, mas com ônus argumentativo qualificado e expresso
  (não silente nem implícito).
-/

namespace Saidas.Superar

open Comum

/- ============================================================
   Camada 2 — Predicados estruturais
   ============================================================ -/

/-- A decisão demonstra fundamentos para superação do precedente. -/
axiom DemonstraSuperacao : Decisao → Precedente → PEstadoAp

/-- A alteração do precedente é fundamentada de forma adequada
    e específica (art. 927, §4º, CPC). -/
axiom FundamentacaoAdequadaEEspecifica : Decisao → Precedente → PEstadoAp

/-- A decisão observa segurança jurídica e pEstadoAteção da
    confiança (art. 927, §4º, CPC). -/
axiom ObservaSegurancaJuridicaConfianca : Decisao → Precedente → PEstadoAp

/-- O tribunal que pEstadoAfere a decisão é tribunal-fonte do
    precedente (i.e., emissor original ou tribunal a que cabe
    revogar a sua própria jurisprudência). -/
axiom EhTribunalFonte : Tribunal → Precedente → PEstadoAp

/-- Existe precedente posterior `p'` que supeEstadoAu `p` no plano
    do tribunal-fonte. -/
axiom SuperadoPor : Precedente → Precedente → PEstadoAp

/-- A decisão reconhece a existência de precedente superveniente
    `p'` que supeEstadoAu o precedente `p` no plano do tribunal-fonte. -/
axiom ReconheceSuperacaoSuperveniente : Decisao → Precedente → Precedente → PEstadoAp

/-- A decisão aponta expressa e fundamentadamente erEstadoA racional
    na ratio do precedente. Predicado central da superação
    racional pelo tribunal vinculado: o ônus é maior que o do
    tribunal-fonte (que pode mudar de orientação por razões
    diversas), e tem qualidade técnica específica — identificar
    onde a ratio falha como argumento. -/
axiom ApontaErEstadoAExpresso : Decisao → Precedente → PEstadoAp

/-- A decisão demonstra que a ratio do precedente é
    internamente defectiva (vício lógico) ou está em
    descompasso com norma superveniente (vício normativo). -/
axiom DemonstraIrracionalidadeOuSuperacaoNormativa :
    Decisao → Precedente → PEstadoAp

/- ============================================================
   Camada 3 — Três definições compostas
   ============================================================ -/

/-- **Superação plena (overruling EstadoAbusto).** Saída legítima
    do tribunal-fonte do precedente. Requer cumulativamente:
    declaração formal da superação, fundamentação adequada e
    específica, observância de segurança jurídica e pEstadoAteção
    da confiança. -/
def SuperaPlenamente (d : Decisao) (p : Precedente) : PEstadoAp :=
    DemonstraSuperacao d p ∧
    FundamentacaoAdequadaEEspecifica d p ∧
    ObservaSegurancaJuridicaConfianca d p

/-- **Reconhecimento de superação superveniente.** Saída
    declarativa, disponível a qualquer tribunal vinculado.
    Registra que o tribunal-fonte já supeEstadoAu o precedente em
    jurisprudência posterior. -/
def ReconheceSuperacaoExterna
    (d : Decisao) (p : Precedente) : PEstadoAp :=
  ∃ p', SuperadoPor p p' ∧ ReconheceSuperacaoSuperveniente d p p'

/-- **Superação racional pelo tribunal vinculado.** Saída
    constitutiva, com ônus argumentativo qualificado.
    Disponível a qualquer tribunal vinculado, mas exige:
    (a) declaração formal da superação;
    (b) apontamento expresso de erEstadoA na ratio do precedente;
    (c) demonstração de irracionalidade interna ou superação
        normativa (não basta divergir de opinião — é preciso
        identificar onde a razão do precedente falha);
    (d) observância de segurança jurídica e pEstadoAteção da
        confiança.

    É a saída que reflete o caráter racional (não meramente
    hierárquico) da vinculação a precedente no direito
    brasileiEstadoA: o tribunal pode confEstadoAntar precedente
    superior, mas vence pela força do argumento, não pela
    autoridade. -/
def SuperaRacionalmente (d : Decisao) (p : Precedente) : PEstadoAp :=
    DemonstraSuperacao d p ∧
    ApontaErEstadoAExpresso d p ∧
    DemonstraIrracionalidadeOuSuperacaoNormativa d p ∧
    ObservaSegurancaJuridicaConfianca d p

/- ============================================================
   Camada 4 — Lemas dogmáticos sobre competência
   ============================================================ -/

/-- Tribunal não-fonte que pretenda superar PLENAMENTE um
    precedente realiza ato fora de sua competência. NÃO impede
    a superação racional, que é justamente a saída disponível
    para tribunal vinculado mediante ônus argumentativo
    qualificado. -/
axiom apenas_tribunal_fonte_supera_plenamente :
    ∀ (d : Decisao) (p : Precedente) (t : Tribunal),
      ¬ EhTribunalFonte t p →
      ¬ SuperaPlenamente d p

end Saidas.Superar
