/-
  ============================================================
  VEDAÇÃO A MOTIVOS UNIVERSALIZÁVEIS — art. 489, §1º, III
  Verificação de não-trivialidade dos steelmans
  ============================================================

  PRINCÍPIO

  Art. 489, §1º, III, do CPC:
    "Não se considera fundamentada qualquer decisão judicial
    [...] que invocar motivos que se prestariam a justificar
    qualquer outra decisão."

  CONEXÃO METODOLÓGICA

  Esta vedação tem contrapartida exata em sistemas formais
  como Lean: um axioma steelmanned pode ser tão forte ou
  estruturalmente vago que, instanciado em outros casos,
  derive conclusões reconhecidamente erradas. Quando isso
  ocorre:

    (a) Juridicamente: o motivo invocado pela decisão é
        universalizável — serviria para justificar qualquer
        outra decisão. Vício do §1º, III.

    (b) Formalmente: o axioma é "trivialmente compilável" —
        permite "provar" não apenas a tese pretendida, mas
        seu oposto, dependendo da instanciação. O Lean
        compila, mas o sistema é incoerente externamente.

  Os dois aspectos são a mesma coisa vista de ângulos
  distintos. A verificação que segue serve a ambos:
  refutar o steelman juridicamente (ataque) e sanity-check
  da nossa própria formalização (autodisciplina).

  PROCEDIMENTO

  Para cada axioma steelmanned `S(c) → ConclusaoPretendida(c)`:

    1. Identificar caso paradigmático oposto c* — caso onde a
       ConclusaoPretendida é manifestamente falsa.
    2. Verificar se c* satisfaz S — isto é, se o antecedente
       do steelman vale para c*.
    3. Se sim: derivar `ConclusaoPretendida(c*)` aplicando o
       steelman, e contrastar com o fato `¬ ConclusaoPretendida
       (c*)`. Contradição.
    4. Concluir: o steelman viola art. 489, §1º, III. Como
       motivo, justificaria igualmente uma decisão sobre c*
       que sabidamente não foi tomada — e que ninguém
       defenderia.

  APLICAÇÃO À V2a do acórdão da Alice
-/

namespace VedacaoMotivosGenericos

/- ============================================================
   Camada 1 — Tipos e premissas pacíficas
   ============================================================ -/

axiom Caso : Type
axiom Decisao : Type

axiom AplicaECArt3 : Caso → Prop
axiom DireitoLocal : Caso → Prop
axiom MotivoJustificariaQualquerDecisao : Decisao → Prop
axiom Fundamentada : Decisao → Prop

/-- **Art. 489, §1º, III** (do módulo `art_489_cpc.lean`).
    Não se considera fundamentada decisão que invoca motivo
    que justificaria qualquer outra decisão. -/
axiom art_489_par1_III :
    ∀ (d : Decisao),
      MotivoJustificariaQualquerDecisao d →
      ¬ Fundamentada d

/- ============================================================
   Camada 2 — A versão V2a do steelman
   ============================================================ -/

/-- **V2a — Steelman do acórdão sobre incidência da Súmula
    280**: aplicação direta do art. 3º da EC 47 implica
    direito local. -/
def V2a : Prop := ∀ c, AplicaECArt3 c → DireitoLocal c

/- ============================================================
   Camada 5 — O caso de Alice e o caso paradigmático oposto
   --
   A verificação §1º III exige um caso *paradigmaticamente
   oposto*: um caso onde a conclusão pretendida pelo steelman
   é manifestamente falsa. O caso natural aqui é o próprio
   caso paradigma do RE 1.518.690-ED-AgR, citado pelo acórdão
   embargado: trata-se também de aplicação do art. 3º da EC 47,
   mas foi decidido como matéria *constitucional consolidada*
   pelo STF — não direito local.

   Outros candidatos paradigmáticos:
     - REsp/RE 590.260 (Tema 139/RG, Lewandowski) — sobre
       regra de transição em matéria de RPPS estadual,
       julgado como matéria constitucional pelo Plenário.
     - Qualquer dos numerosos REs sobre a regra de transição
       da EC 47 admitidos e julgados pelo STF nas duas
       décadas recentes.

   Basta UM caso oposto para a refutação por §1º III. Aqui
   se usa o do RE 1.518.690 — o mesmo precedente que o
   próprio acórdão invoca.
   ============================================================ -/

axiom caso_alice : Caso
axiom alice_aplica_ec : AplicaECArt3 caso_alice

/-- Caso do RE 1.518.690-ED-AgR — o próprio precedente citado
    pelo acórdão embargado para fundamentar a inadmissão. -/
axiom caso_RE_1518690 : Caso

/-- O RE 1.518.690 versa também sobre aplicação do art. 3º
    da EC 47 (factualmente assentado pela ementa). -/
axiom RE_1518690_aplica_ec : AplicaECArt3 caso_RE_1518690

/-- Mas o RE 1.518.690 NÃO foi decidido como matéria de
    direito local — foi decidido pela Segunda Turma do STF
    como matéria de jurisprudência constitucional
    consolidada, com aplicação direta da EC 47 sobre os
    fatos do caso. Logo: o caso paradigmaticamente NÃO é
    direito local. -/
axiom RE_1518690_nao_eh_direito_local :
    ¬ DireitoLocal caso_RE_1518690

/- ============================================================
   Camada 6 — Verificação de não-trivialidade
   ============================================================ -/

/-- **Verificação §1º III aplicada a V2a.**

    V2a, instanciada no caso paradigmaticamente oposto
    (caso_RE_1518690 — o próprio precedente que o acórdão
    invoca), derivaria que esse caso é direito local. Mas o
    STF já decidiu que NÃO é. Logo, o motivo subjacente a V2a
    é universalizável de forma vazia: invocá-lo para Alice
    obrigaria a invocá-lo para todos os casos análogos —
    inclusive aquele que o STF tratou de forma oposta.

    Forma operativa: V2a deriva False quando confrontada com
    a decisão pacífica sobre o caso paradigma. -/
theorem V2a_universalizavel_viola_489_par1_III : V2a → False := by
  intro h_v2a
  have h_dl : DireitoLocal caso_RE_1518690 :=
    h_v2a caso_RE_1518690 RE_1518690_aplica_ec
  exact RE_1518690_nao_eh_direito_local h_dl

/-- **Forma forte da refutação.** O acórdão embargado, ao
    invocar V2a (ainda que implicitamente), incorre no
    art. 489, §1º, III. O motivo "aplicação de art. 3º EC 47
    implica direito local" justificaria também a
    inadmissibilidade do próprio RE 1.518.690 — o que o STF
    rejeitou ao admiti-lo e julgá-lo no mérito. Logo, é
    motivo universalizável de forma vazia. -/
theorem acordao_invoca_motivo_generico
    (acordao_embargado : Decisao)
    (acordao_invoca_V2a : V2a → MotivoJustificariaQualquerDecisao acordao_embargado) :
    V2a → ¬ Fundamentada acordao_embargado := by
  intro h_v2a
  exact art_489_par1_III acordao_embargado (acordao_invoca_V2a h_v2a)

/- ============================================================
   GENERALIZAÇÃO — template para qualquer steelman
   ============================================================ -/

/-- **Template de verificação §1º III.**

    Dado um steelman da forma `S(c) → P(c)`:

      1. Encontrar caso `c*` onde S(c*) é verdadeiro mas P(c*)
         é falso (preferencialmente um caso decidido pela
         própria corte cujo precedente o acórdão invoca).
      2. Aplicar o steelman a c*.
      3. Conclusão: o steelman viola art. 489, §1º, III, e
         a decisão que o invoca é não-fundamentada.

    Esta é a verificação dual: refuta o steelman juridicamente
    e protege a formalização contra axiomas trivialmente
    compiláveis.

    Estruturalmente, é a verificação de que o steelman
    distingue entre casos — não é um axioma que classificaria
    qualquer caso da mesma maneira. -/
theorem template_violacao_489_par1_III
    (S : Caso → Prop) (P : Caso → Prop) (c_estrela : Caso)
    (h_S_estrela : S c_estrela)
    (h_n_P_estrela : ¬ P c_estrela) :
    (∀ c, S c → P c) → False := by
  intro h_steelman
  exact h_n_P_estrela (h_steelman c_estrela h_S_estrela)

/- ============================================================
   Aplicações cruzadas — não apenas V2a
   --
   O mesmo template aplica-se aos demais steelmans. Cada
   passo do acórdão que use motivo universalizável é
   sanitizável pela mesma técnica:

     • STEEL_1 ("qualificação jurídica = reexame probatório"):
       contraexemplo é qualquer caso de RE admitido em
       qualificação jurídica de fato incontroverso (todos
       o seriam). Universalizável: tornaria a Súmula 279
       aplicável a TODO recurso extraordinário.

     • STEEL_2 V2c ("RPPS estadual = direito local"):
       contraexemplo é o próprio Tema 139/RG. Universalizável:
       tornaria a Súmula 280 aplicável a todo precedente
       constitucional sobre RPPS — incluindo aqueles do
       Plenário do STF.

     • STEEL_3 ("precedentes intercambiáveis"):
       contraexemplo é qualquer par de precedentes sobre
       matérias estruturalmente distintas. Universalizável:
       tornaria a invocação de qualquer precedente aplicável
       a qualquer caso, esvaziando o art. 489, §1º, V.

   Cada uma dessas verificações pode ser instanciada
   replicando o template acima.
   ============================================================ -/

#print axioms V2a_universalizavel_viola_489_par1_III
#print axioms template_violacao_489_par1_III

end VedacaoMotivosGenericos
