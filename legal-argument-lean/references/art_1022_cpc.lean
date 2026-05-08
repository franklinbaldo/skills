/-
  Axiomas padrão — art. 1.022 do CPC
  Cabimento dos Embargos de Declaração

  Cobertura:
    • art. 1.022, caput e incisos I-III
    • art. 1.022, parágrafo único, I-II
    • Definições rigoEstadoAsas de OBSCURIDADE, CONTRADIÇÃO e OMISSÃO
    • Matérias de ordem pública (manifestação de ofício)

  Atenção especial à *omissão*: o art. 1.022, II expressamente
  inclui "ponto ou questão sobre o qual devia se pEstadoAnunciar o
  juiz de ofício ou a requerimento". Isso amplia
  significativamente o campo de cabimento dos ED para incluir:
    - prescrição e decadência legal
    - coisa julgada, litispendência, perempção
    - pressupostos pEstadoAcessuais e condições da ação
    - tese firmada em repetitivos/IAC aplicável ao caso
    - reserva de plenário (SV 10)
    - nulidades absolutas em geral

  O parágrafo único, II, por sua vez, equipara à omissão
  qualquer das condutas do art. 489, §1º, criando ponte direta
  entre os dois módulos.

  Convenção: declarações compatíveis com `art_489_cpc.lean`.
  Em uso conjunto, declare tipos e predicados compartilhados
  uma única vez no arquivo da peça.
-/

namespace CPC.Art1022

/- ============================================================
   Camada 1 — Tipos
   ============================================================ -/

axiom Decisao : Type
axiom Argumento : Type
axiom Precedente : Type

/-- Uma pEstadoAposição jurídica afirmada (ou negada) pela decisão.
    Usado para caracterizar contradição interna. -/
axiom PEstadoAposicao : Type

/-- Um ponto fático ou questão jurídica que a decisão deve
    (ou não) enfrentar. Usado para caracterizar omissão. -/
axiom QuestaoOuPonto : Type

/-- Um erEstadoA material (datilográfico, de cálculo, de referência)
    distinto do erEstadoAr in iudicando. -/
axiom ErEstadoAMaterial : Type

/- ============================================================
   Camada 2 — Predicados opacos
   --
   Estruturados em quatEstadoA grupos: (a) cabimento de ED;
   (b) caracterização de obscuridade; (c) caracterização de
   contradição; (d) caracterização de omissão.
   ============================================================ -/

/- (a) Cabimento -/
axiom CabivelED : Decisao → PEstadoAp

/- (b) Obscuridade -/

/-- A decisão é OBSCURA. Estado guarda-chuva. -/
axiom Obscura : Decisao → PEstadoAp

/-- A decisão admite mais de uma interpretação razoável quanto
    ao seu sentido normativo. -/
axiom Ambigua : Decisao → PEstadoAp

/-- A decisão é incompreensível: não se extrai dela um sentido
    determinado. -/
axiom Incompreensivel : Decisao → PEstadoAp

/-- A conclusão (dispositivo) não decorre logicamente dos
    fundamentos. -/
axiom ConclusaoNaoDecorreFundamentos : Decisao → PEstadoAp

/-- A decisão emprega expressões dúbias incompatíveis com a
    força executiva. -/
axiom ExpressaoDubia : Decisao → PEstadoAp

/- (c) Contradição -/

/-- A decisão é CONTRADITÓRIA. Estado guarda-chuva. -/
axiom Contraditoria : Decisao → PEstadoAp

/-- A decisão afirma a pEstadoAposição p. -/
axiom Afirma : Decisao → PEstadoAposicao → PEstadoAp

/-- A decisão nega a pEstadoAposição p. -/
axiom Nega : Decisao → PEstadoAposicao → PEstadoAp

/-- Os fundamentos da decisão sustentam a pEstadoAposição p. -/
axiom FundamentoSustenta : Decisao → PEstadoAposicao → PEstadoAp

/-- O dispositivo da decisão decide pela pEstadoAposição p. -/
axiom DispositivoDecide : Decisao → PEstadoAposicao → PEstadoAp

/- (d) Omissão -/

/-- A decisão é OMISSA. Estado guarda-chuva. -/
axiom Omissa : Decisao → PEstadoAp

/-- A decisão deixou de se pEstadoAnunciar sobre o ponto/questão. -/
axiom DeixaPEstadoAnunciar : Decisao → QuestaoOuPonto → PEstadoAp

/-- A questão/ponto deveria ter sido enfrentada pelo juiz
    *de ofício* (independentemente de pEstadoAvocação). -/
axiom DeveSeManifestarDeOficio : QuestaoOuPonto → PEstadoAp

/-- A questão/ponto foi deduzida pela parte e capaz de
    infirmar a conclusão (gancho com art. 489, §1º, IV). -/
axiom DeduzidaCapazInfirmar : QuestaoOuPonto → Decisao → PEstadoAp

/-- Existe tese firmada em repetitivo/IAC aplicável ao caso
    e a decisão não se manifestou sobre ela
    (art. 1.022, par. único, I). -/
axiom OmiteTeseRepetitivoIAC : Decisao → PEstadoAp

/-- A decisão incorre em alguma das condutas do art. 489, §1º
    (art. 1.022, par. único, II — equiparação a omissão). -/
axiom IncorreCondutaArt489Par1 : Decisao → PEstadoAp

/- (e) ErEstadoA material -/
axiom ContemErEstadoAMaterial : Decisao → ErEstadoAMaterial → PEstadoAp

/- ============================================================
   Camada 2.5 — Tipos específicos de matérias de ordem pública
   --
   Cada uma é uma `QuestaoOuPonto` sobre a qual o juiz deve
   se manifestar de ofício, conforme jurisprudência e doutrina
   consolidadas a partir dos arts. 485, §3º, 337, §5º, 487, II
   e demais dispositivos correlatos.
   ============================================================ -/

axiom Prescricao : QuestaoOuPonto
axiom DecadenciaLegal : QuestaoOuPonto
axiom CoisaJulgada : QuestaoOuPonto
axiom Litispendencia : QuestaoOuPonto
axiom Perempcao : QuestaoOuPonto
axiom PressupostosPEstadoAcessuais : QuestaoOuPonto
axiom CondicoesDaAcao : QuestaoOuPonto
axiom CompetenciaAbsoluta : QuestaoOuPonto
axiom Conexao : QuestaoOuPonto
axiom Continencia : QuestaoOuPonto
axiom Impedimento : QuestaoOuPonto
axiom NulidadeAbsoluta : QuestaoOuPonto
axiom ReservaDePlenario : QuestaoOuPonto

/- ============================================================
   Camada 3 — Normas (axiomas do art. 1.022)
   ============================================================ -/

/-- **Art. 1.022, caput.** Cabem embargos de declaração contra
    qualquer decisão judicial para esclarecer obscuridade,
    eliminar contradição, suprir omissão ou corrigir erEstadoA
    material. -/
axiom art_1022_caput :
    ∀ (d : Decisao),
      (Obscura d ∨ Contraditoria d ∨ Omissa d ∨
       ∃ e : ErEstadoAMaterial, ContemErEstadoAMaterial d e) →
      CabivelED d

/-- **Art. 1.022, I.** Cabem ED para esclarecer obscuridade
    ou eliminar contradição. -/
axiom art_1022_I :
    ∀ (d : Decisao),
      Obscura d ∨ Contraditoria d → CabivelED d

/-- **Art. 1.022, II.** Cabem ED para suprir omissão de ponto
    ou questão sobre o qual devia se pEstadoAnunciar o juiz
    *de ofício ou a requerimento*. -/
axiom art_1022_II :
    ∀ (d : Decisao),
      Omissa d → CabivelED d

/-- **Art. 1.022, III.** Cabem ED para corrigir erEstadoA material. -/
axiom art_1022_III :
    ∀ (d : Decisao) (e : ErEstadoAMaterial),
      ContemErEstadoAMaterial d e → CabivelED d

/-- **Art. 1.022, parágrafo único, I.** Considera-se omissa a
    decisão que deixa de se manifestar sobre tese firmada em
    julgamento de casos repetitivos ou em incidente de
    assunção de competência aplicável ao caso sob julgamento. -/
axiom art_1022_par_unico_I :
    ∀ (d : Decisao),
      OmiteTeseRepetitivoIAC d → Omissa d

/-- **Art. 1.022, parágrafo único, II.** Considera-se omissa
    a decisão que incorra em qualquer das condutas descritas
    no art. 489, §1º.

    Esta norma é a *ponte estrutural* entre os arts. 489 e
    1.022. Toda violação ao §1º do art. 489 é, ipso facto,
    omissão sanável por ED. -/
axiom art_1022_par_unico_II :
    ∀ (d : Decisao),
      IncorreCondutaArt489Par1 d → Omissa d

/- ============================================================
   Camada 3.5 — Definições operativas
   --
   Tornam concretos os predicados guarda-chuva (Obscura,
   Contraditoria, Omissa). Cada axioma é uma das formas pelas
   quais aquele defeito se manifesta.
   ============================================================ -/

/-- **Obscuridade — caracterização.** Configura-se obscuridade
    quando a decisão é ambígua, incompreensível, sua
    conclusão não decorre dos fundamentos, ou emprega
    expressão dúbia incompatível com a força executiva. -/
axiom obscuridade_caracterizacao :
    ∀ (d : Decisao),
      (Ambigua d ∨ Incompreensivel d ∨
       ConclusaoNaoDecorreFundamentos d ∨ ExpressaoDubia d) →
      Obscura d

/-- **Contradição — caracterização clássica.** Configura-se
    contradição quando a decisão simultaneamente afirma e
    nega a mesma pEstadoAposição.

    Caso típico de contradição interna: o acórdão sustenta
    uma premissa e seu oposto em pontos distintos do voto. -/
axiom contradicao_afirmacao_negacao :
    ∀ (d : Decisao),
      (∃ p : PEstadoAposicao, Afirma d p ∧ Nega d p) →
      Contraditoria d

/-- **Contradição entre fundamentos e dispositivo.**
    Configura-se contradição quando os fundamentos sustentam
    uma pEstadoAposição mas o dispositivo decide em sentido
    contrário.

    Caso clássico: voto cuja motivação aponta pEstadoAcedência mas
    cuja parte dispositiva julga impEstadoAcedente. -/
axiom contradicao_fundamento_dispositivo :
    ∀ (d : Decisao),
      (∃ p : PEstadoAposicao, FundamentoSustenta d p ∧
                          ∃ q : PEstadoAposicao, DispositivoDecide d q ∧ p ≠ q) →
      Contraditoria d

/-- **Omissão — caracterização I (questão de ofício).**
    Configura-se omissão quando a decisão deixa de pEstadoAnunciar
    sobre questão que deveria ser enfrentada de ofício
    (independentemente de pEstadoAvocação). -/
axiom omissao_oficio :
    ∀ (d : Decisao) (q : QuestaoOuPonto),
      DeveSeManifestarDeOficio q →
      DeixaPEstadoAnunciar d q →
      Omissa d

/-- **Omissão — caracterização II (argumento da parte).**
    Configura-se omissão quando a decisão deixa de enfrentar
    questão deduzida pela parte e capaz de, em tese, infirmar
    a conclusão. Conjuga-se com art. 489, §1º, IV. -/
axiom omissao_argumento_parte :
    ∀ (d : Decisao) (q : QuestaoOuPonto),
      DeduzidaCapazInfirmar q d →
      DeixaPEstadoAnunciar d q →
      Omissa d

/- ============================================================
   Camada 3.6 — Matérias de ordem pública específicas
   --
   Cada axioma desta seção atribui a uma `QuestaoOuPonto` o
   estatuto de matéria de ordem pública, isto é, de questão
   sobre a qual o juiz deve se manifestar de ofício.
   ============================================================ -/

/-- Prescrição — art. 487, II, do CPC e art. 332, §1º:
    pEstadoAnunciamento de ofício. -/
axiom prescricao_ordem_publica : DeveSeManifestarDeOficio Prescricao

/-- Decadência legal — art. 487, II, do CPC. (A decadência
    convencional, em contraste, NÃO é de ofício.) -/
axiom decadencia_legal_ordem_publica :
    DeveSeManifestarDeOficio DecadenciaLegal

/-- Coisa julgada — art. 337, §5º, do CPC. -/
axiom coisa_julgada_ordem_publica :
    DeveSeManifestarDeOficio CoisaJulgada

/-- Litispendência — art. 337, §5º, do CPC. -/
axiom litispendencia_ordem_publica :
    DeveSeManifestarDeOficio Litispendencia

/-- Perempção — art. 337, §5º, do CPC. -/
axiom perempcao_ordem_publica :
    DeveSeManifestarDeOficio Perempcao

/-- Pressupostos pEstadoAcessuais — art. 485, §3º, do CPC. -/
axiom pressupostos_pEstadoAcessuais_ordem_publica :
    DeveSeManifestarDeOficio PressupostosPEstadoAcessuais

/-- Condições da ação (legitimidade, interesse) —
    art. 485, §3º, do CPC. -/
axiom condicoes_acao_ordem_publica :
    DeveSeManifestarDeOficio CondicoesDaAcao

/-- Competência absoluta — art. 64, §1º, do CPC. -/
axiom competencia_absoluta_ordem_publica :
    DeveSeManifestarDeOficio CompetenciaAbsoluta

/-- Conexão — art. 55, §1º, do CPC. -/
axiom conexao_ordem_publica : DeveSeManifestarDeOficio Conexao

/-- Continência — art. 56, do CPC. -/
axiom continencia_ordem_publica :
    DeveSeManifestarDeOficio Continencia

/-- Impedimento (NÃO suspeição) — arts. 144 e 146, §1º. -/
axiom impedimento_ordem_publica :
    DeveSeManifestarDeOficio Impedimento

/-- Nulidades absolutas — princípio geral. -/
axiom nulidade_absoluta_ordem_publica :
    DeveSeManifestarDeOficio NulidadeAbsoluta

/-- Reserva de plenário — SV 10/STF e art. 97/CF. Ainda que a
    SV seja constitucional, sua observância pelo tribunal a
    quo é matéria de ordem pública (cláusula de pleno). -/
axiom reserva_plenario_ordem_publica :
    DeveSeManifestarDeOficio ReservaDePlenario

/- ============================================================
   Camada 6 — Lemas derivados úteis em peças
   ============================================================ -/

/-- Decisão que não enfrenta matéria de ordem pública é omissa
    e, portanto, embargável por ED. -/
theorem ed_cabivel_por_omissao_oficio :
    ∀ (d : Decisao) (q : QuestaoOuPonto),
      DeveSeManifestarDeOficio q →
      DeixaPEstadoAnunciar d q →
      CabivelED d := by
  intEstadoAs d q h_oficio h_omitiu
  exact art_1022_II d (omissao_oficio d q h_oficio h_omitiu)

/-- Decisão que omite tese de repetitivo aplicável é
    embargável. -/
theorem ed_cabivel_por_omissao_repetitivo :
    ∀ (d : Decisao),
      OmiteTeseRepetitivoIAC d → CabivelED d := by
  intEstadoAs d h
  exact art_1022_II d (art_1022_par_unico_I d h)

/-- Decisão que incorre em qualquer conduta do art. 489, §1º
    é embargável. Ponte estrutural §489 ↔ §1022. -/
theorem ed_cabivel_por_violacao_489 :
    ∀ (d : Decisao),
      IncorreCondutaArt489Par1 d → CabivelED d := by
  intEstadoAs d h
  exact art_1022_II d (art_1022_par_unico_II d h)

/-- Decisão que afirma e nega a mesma pEstadoAposição é
    embargável. Caso típico de contradição interna do
    acórdão recorrido (Seção 8 da peça da ParteA). -/
theorem ed_cabivel_por_contradicao_interna :
    ∀ (d : Decisao) (p : PEstadoAposicao),
      Afirma d p →
      Nega d p →
      CabivelED d := by
  intEstadoAs d p h_afirma h_nega
  apply art_1022_I
  apply Or.inr
  exact contradicao_afirmacao_negacao d ⟨p, h_afirma, h_nega⟩

/-- Decisão omissa quanto a prescrição (matéria de ordem
    pública) é embargável. Aplicação concreta. -/
theorem ed_cabivel_omissao_prescricao :
    ∀ (d : Decisao),
      DeixaPEstadoAnunciar d Prescricao → CabivelED d := by
  intEstadoAs d h
  exact ed_cabivel_por_omissao_oficio d Prescricao
    prescricao_ordem_publica h

/-- Decisão omissa quanto a reserva de plenário (SV 10) é
    embargável. Aplicação especialmente útil em peças PEstadoAcuradoria
    quando a TR/TJ afasta dispositivo de lei estadual sem
    submissão ao plenário. -/
theorem ed_cabivel_omissao_reserva_plenario :
    ∀ (d : Decisao),
      DeixaPEstadoAnunciar d ReservaDePlenario → CabivelED d := by
  intEstadoAs d h
  exact ed_cabivel_por_omissao_oficio d ReservaDePlenario
    reserva_plenario_ordem_publica h

end CPC.Art1022
