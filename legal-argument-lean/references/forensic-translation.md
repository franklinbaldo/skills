# From workspace to forensic peça

> Companion reference for the `legal-argument-lean` skill. Read this file
> in full before translating any Lean formalization into a peça forense
> (Fase 5 of the pipeline, or the final step of the direct workflow).

The Lean exercise is **workspace**, not **product**. It maps the
argumentative space; the peça delivers the conclusion. Translation
between the two is a real step — not a copy operation. The peça
should describe **the case**, not the reasoning that led to the
conclusion about the case.

This is invisible if you skip it. The peça compiles fine in the
sense that it states correct claims with correct citations. But the
voice betrays the workspace: the prose talks about "leituras dignas
de exame", "pressupostos sistêmicos", "universalização vazia",
"steelmans". The reader senses the machinery. Worse, dignifying
absurd readings as "leituras a refutar" implies, falsely, that the
court might sustain them — which insults the court and weakens the
attack.

## Translation rules

**Open with the processual verb, not the analytical setup.**

- Workspace voice: "cumpre examinar sob qual leitura defensável dessa
  premissa o enunciado se sustenta"
- Forensic voice: "o acórdão embargado aplicou a Súmula 280 sem
  indicar qual norma de direito local teria sido interpretada"

The first describes how the brief proceeds; the second describes
what the court did. Only the second is a peça opening.

**Vocabulary translation.** Workspace terms must not appear in the
peça. The forensic concepts they map to:

| Workspace (Lean / methodology)     | Peça (forensic)                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------ |
| steelman, V_n_a/b/c                | (subsumed in prose; leituras não são nomeadas)                                 |
| universalização vazia              | motivos genéricos do art. 489 §1º III; fundamento incapaz de distinguir o caso |
| leituras dignas de exame           | (silently absent — só as leituras dignas aparecem)                             |
| pressupostos sistêmicos            | competência constitucional desta Casa; existência do Tema X/RG                 |
| filtro de trivialidade             | (silently absent — leituras triviais não aparecem)                             |
| §1º III check                      | argumento direto pelo art. 489 §1º III                                         |
| caso de [Nome]                     | hipótese dos autos; caso concreto; decisão recorrida                           |
| compila / não compila              | a tese sustenta-se / não se sustenta                                           |
| ratio decidendi                    | (uso técnico OK, com parcimônia)                                               |
| saída legítima, espaço de saídas   | postura legítima; modo de uso do precedente                                    |
| não-saída, fora do espaço legítimo | uso impróprio de precedente; aplicação seletiva                                |
| partição (das saídas)              | (silently absent — a estrutura aparece como enumeração no corpo, sem nome)     |
| trait, módulo de saída             | (silently absent — categoria estrutural do Lean)                               |

**Cuidado com construções internas do Lean.** Termos inventados
*dentro* do exercício formal para descrever sua estrutura — partição,
trait, saída, espaço legítimo, não-saída — são workspace por
construção, ainda que pareçam neutros ou descritivos. Por familiaridade
ao longo do trabalho, esses termos tendem a migrar inadvertidamente
para a peça, onde causam estranhamento ao leitor versado (que reconhece
o vocabulário processual brasileiro reconhecido, e percebe ruído quando
algo escapa dele).

Regra operacional: **qualquer expressão criada dentro do Lean fica
dentro do Lean**. A peça usa apenas vocabulário que existe *fora* do
exercício formal — dispositivos legais nominados, doutrina reconhecida,
jurisprudência citada, fórmulas dogmáticas consagradas. O teste é
simples: se o termo não está em um manual de processo civil ou em
ementa de acórdão, não está pronto para a peça.

Exemplo concreto: o teorema `acordao_TJRO_fora_do_espaco_legitimo`
captura o vício de "uso impróprio de precedente vinculante por
aplicação seletiva de sua ratio". O nome do teorema serve à
arquitetura do Lean; a peça nomeia o vício pela fórmula dogmática.

**Show conclusions, not the discovery process.** If three readings
were examined and only one survived, the peça presents only the one
that survived (positively, as "a leitura correta é X") and the one
worth attacking (as "a leitura adotada pelo acórdão é defectiva").
Trivial leituras dispensa-se silentemente — não comparecem ao texto.

**Institutional, not professoral.** Avoid first-person plural
explanations of the argument's structure ("examinemos", "passemos",
"resta-nos"). Avoid phrases that frame the peça as an analysis
("quatro leituras se apresentam", "esgotadas as alternativas"). The
peça is a request, not a treatise.

**The forensic test.** Read each parágrafo and ask: *isto descreve o
caso ou descreve como cheguei à conclusão sobre o caso?* If it
describes the path, rewrite it to describe the conclusion. The Lean
file is where the path lives.

## What the workspace gets you (despite remaining hidden)

The strict separation does not waste workspace work:

- **Confidence.** You know the argument is correct because you
  formalized it. The peça's claims have been audited.
- **Robustness.** When the court replies "but I meant X", you have
  X formalized somewhere and refuted. The peça can address it
  briefly because the work is done.
- **Concision.** Knowing which leituras are trivial lets you skip
  them entirely instead of refuting weakly.
- **Anchor selection.** The §1º III audit identifies which
  precedents the court itself cannot deny — those become the
  citations in the peça.

The peça should read as if the lawyer simply *saw* the vício and
named it. The reader should never know how much work it took.
