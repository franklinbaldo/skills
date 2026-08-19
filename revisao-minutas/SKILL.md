---
name: revisao-minutas
description: >-
  Triagem de risco de minutas JUDICIAIS elaboradas pela assessoria de
  Franklin (contestações, recursos, embargos, contrarrazões, agravos,
  manifestações), para decidir se estão aptas a peticionamento. Use SEMPRE
  que Franklin colar ou anexar uma minuta que ele não redigiu e pedir
  qualquer forma de avaliação — "revisa isso", "vê se pode protocolar",
  "avalia essa minuta", "confere essa peça", "a assessoria mandou isso",
  "posso assinar?" — mesmo sem a palavra "risco". O produto é um veredito
  de triagem (🟢/🟡/🔴) com relatório em markdown OKF, e NÃO uma reescrita:
  o texto original fica intocado por padrão. NÃO use quando Franklin está
  redigindo a peça do zero com Claude (aí é redação normal, com esqueleto
  e aprovação por seção), nem para pareceres e documentos administrativos.
---

## Filosofia: triagem, não coautoria

O gargalo de Franklin é volume. A assessoria produz minutas; a função desta
skill é decidir **se a peça pode ser protocolada**, não escrevê-la de novo.
Duas regras de ouro:

1. **O texto original fica intocado por padrão.** Toda intervenção precisa
   se justificar por risco concreto — nunca por preferência estilística.
   "Eu escreveria diferente" é proibido como fundamento de edit. Se a frase
   é feia mas juridicamente inócua, ela passa.
2. **Edits são cirúrgicos e prontos para colar.** Quando um ajuste é
   necessário, entregue no formato *trecho original → trecho substituto*,
   delimitado com precisão suficiente para localizar-e-substituir no
   editor. Nunca reescreva a seção inteira para corrigir uma frase.

A postura é a de um revisor adversarial com pressa: a minuta é a tese, e o
trabalho de Claude é tentar derrubá-la **antes** que o juízo, a parte
contrária ou o órgão de correição o façam. Se a minuta sobrevive ao ataque,
ela vai.

## Fluxo

**O primeiro produto é sempre o arquivo do relatório OKF.** Em todo uso
desta skill, o relatório de triagem sai como arquivo antes de esqueleto,
reescrita, edits em prosa ou qualquer outro produto — e sem esperar ser
pedido. Achado superveniente (resposta do NotebookLM, decisão de
Franklin, revisão dele sobre a própria triagem) atualiza o arquivo ou
gera v2: **a conversa comenta, o relatório registra.** Em mais de uma
minuta, um relatório por minuta e um veredito por minuta — nunca um
parecer agregado que obrigue Franklin a desembaraçar qual risco pertence
a qual peça.

1. **Identificar a peça e o contexto mínimo**: tipo de peça, processo (CNJ),
   fase, prazo, quem é a parte representada (Estado, IPERON), qual decisão
   ou ato ela responde. Se algo disso não estiver claro, perguntar antes de
   avaliar — errar o contexto invalida a triagem inteira.
2. **Rodar a taxonomia de risco** (abaixo), em ordem de letalidade. Parar
   cedo se encontrar risco fatal: não vale a pena polir uma peça inapta.
3. **Verificar ancoragem fática.** Toda afirmação da minuta sobre os autos
   (datas, IDs, o que a decisão disse, o que a parte alegou) é hipótese até
   prova em contrário. O que Claude não puder verificar pelo contexto vira
   pergunta para o NotebookLM (ver seção própria).
4. **Emitir o veredito e o relatório OKF** — este passo não é adiável nem
   condicionado a pedido: é o que a skill entrega.
5. Se 🟡: entregar os edits cirúrgicos junto com o relatório, prontos para
   aplicar e protocolar. A redação de todo trecho substituto segue a skill
   `redacao-pecas` — o edit que corrige um risco não pode introduzir outro.

## Veredito em três faixas

Sempre no topo do relatório, sem hedging:

- 🟢 **Apta** — protocolar como está. Imperfeições toleráveis podem ser
  anotadas em uma linha cada, sem edit.
- 🟡 **Apta com ajustes cirúrgicos** — lista fechada e curta de edits no
  formato original → substituto. Aplicou, protocolou.
- 🔴 **Inapta** — risco fatal ou exposição grave. Dizer exatamente qual, e
  o que precisa acontecer antes (devolver à assessoria com instrução X,
  verificar Y nos autos, decisão estratégica de Franklin sobre Z).

Um veredito 🟡 com mais de ~6 edits provavelmente é um 🔴 disfarçado —
nesse caso, ser honesto e devolver, em vez de reescrever a peça por
gotejamento. A contagem é só de **edits de risco** (camadas 1 a 8): os
edits de clareza da camada 9 saem em relatório de estilo e não inflam o
veredito.

## Taxonomia de risco (ordem de letalidade)

### 1. Fatais — qualquer um torna a peça inapta

- **Tempestividade**: prazo do ato, termo inicial correto (intimação, DJe,
  ciência pessoal da Fazenda), contagem em dobro quando aplicável, feriados
  locais. Fonte autoritativa: a **aba Expedientes do PJe**, conferida por
  Franklin — o PDF dos autos geralmente não traz o expediente correto
  (especialmente em processos do IPERON), então nem o contexto nem o
  NotebookLM resolvem esse ponto. Tempestividade entra **sempre** no
  checklist de protocolo; nunca presumir.
- **Cabimento**: a peça é a via correta para atacar aquele ato? Recurso
  cabível, hipótese legal dos embargos efetivamente presente (omissão,
  contradição, obscuridade, erro material — e não mero inconformismo),
  interesse recursal.
- **Legitimidade e representação**: a peça fala pelo ente certo (Estado vs.
  IPERON), no polo certo.
- **Endereçamento e rito**: juízo/órgão correto, competência, requisitos
  formais com sanção de inadmissibilidade (dialeticidade nas razões
  recursais, impugnação específica).
- **Preclusão consumada**: a tese central da peça já foi decidida e não
  atacada no momento próprio.
- **Pedido**: compatível com o rito e com a fundamentação; não pede o
  juridicamente impossível nem menos do que a fundamentação sustenta.

### 2. Omissões por tipo de peça

A revisão adversarial tem viés natural para atacar o que está escrito;
esta camada olha o que **falta**. Omissão de matéria obrigatória pode ser
tão letal quanto erro no texto — e é invisível para quem só lê a minuta.

- **Contestação**: prescrição/decadência arguíveis e não arguidas;
  preliminares cabíveis (ilegitimidade, incompetência, inépcia,
  litispendência/coisa julgada); impugnação específica de **cada**
  pedido e de **cada** fato relevante (art. 341 do CPC — fato não
  impugnado presume-se verdadeiro).
- **Recursos (apelação, RI, agravos)**: capítulo da decisão não
  impugnado (preclui); prequestionamento das matérias que podem subir —
  em especial nas séries em que a estratégia é esgotar dois embargos
  sucessivos com os Temas 1306/STJ e 339/STF antes de REsp/RE.
- **Contrarrazões**: preliminares de inadmissibilidade do recurso
  adverso (tempestividade dele, preparo, dialeticidade). Omissão aqui é
  oportunidade queimada, não só risco.
- **Embargos de declaração**: o vício efetivamente indicado com precisão
  (qual omissão, onde a matéria foi suscitada e não enfrentada) —
  embargos que não apontam o vício são inadmissíveis e expõem à multa.

Omissão detectada classifica no mínimo 🟡; se for preclusiva e
irreversível após o protocolo (capítulo não impugnado, prescrição não
arguida em contestação), é 🔴.

### 3. Exposição institucional

- **Admissão de fato prejudicial**: a minuta reconhece, ainda que de
  passagem, fato ou tese que compromete o Estado/IPERON neste ou em outros
  processos. É o risco mais traiçoeiro porque costuma estar em frases
  acessórias ("embora de fato o servidor tenha...").
- **Contradição com posição já sustentada**: pela PGE no mesmo processo, em
  processos-irmãos da mesma carteira, ou em tese institucional. Uma minuta
  não pode queimar uma estratégia em curso sem Franklin perceber.
- **Precedente vinculante ignorado**: a peça sustenta tese contrária a tema
  repetitivo, repercussão geral ou súmula vinculante **sem** fazer
  distinguishing. Sustentar contra precedente é legítimo; fingir que ele
  não existe é exposição.
- **Precedente ruim para a carteira**: o argumento, se acolhido, cria
  fundamento que se volta contra o Estado/IPERON em casos futuros da mesma
  série.

### 4. Coerência lógica do argumento

Categoria distinta de fato errado ou citação ruim: a estrutura do
raciocínio jurídico pode estar **invertida ou incoerente** mesmo quando
cada fato individual está certo. É o risco mais fácil de a triagem
deixar passar, porque não se detecta perguntando "isso é verdade?" — se
detecta perguntando "isso segue logicamente do que foi dito antes?".

- **Sujeito ativo/passivo trocado**: a peça atribui a uma parte o papel
  processual da outra — por exemplo, tratar o titular de um direito como
  se fosse o obrigado a satisfazê-lo, quando na verdade é o obrigado
  quem deveria ocupar essa posição. Comum em minutas que reaproveitam
  parágrafos de outro caso com estrutura de partes diferente.
- **Relações jurídicas distintas tratadas como uma só**: quando os fatos
  envolvem mais de um vínculo (ex.: um vínculo originário entre o Estado
  e a parte A, e um vínculo posterior entre a parte A e a parte B), a
  minuta que resolve tudo com um único argumento genérico tende a
  confundir qual relação está em discussão em cada trecho. Separar as
  relações explicitamente costuma ser o próprio conserto.
- **Premissa não verificada tratada como conclusão**: a peça afirma
  como decorrência lógica algo que na verdade é só afirmação repetida
  com palavras diferentes (petição de princípio).
- **Sinal de alerta**: se ao ler um parágrafo em voz alta o argumento
  parece "óbvio demais" ou reaproveitado — desconfiar. Frases
  herdadas de outra peça com fato-padrão diferente são o veículo mais
  comum desse risco, porque a lógica valia para o caso original e não
  foi reconferida contra os fatos deste.
- Conserto é sempre reescrita do parágrafo, nunca cosmético: a frase
  errada geralmente não tem trecho "quase certo" para editar — precisa
  reconstruir o raciocínio com os fatos corretos do caso em mãos.

### 5. Ancoragem fática

Afirmações sobre os autos que podem estar simplesmente erradas: datas,
números de ID/página, o teor do que a decisão embargada/recorrida
efetivamente disse, o que a parte contrária efetivamente alegou, valores,
rubricas. Assessoria trabalhando em volume comete exatamente esse tipo de
erro — e é o tipo que o NotebookLM verifica melhor que qualquer um.

Ferramentas de verificação além do NotebookLM — usar a fonte primária,
nunca confiar no agregador de onde a assessoria colou:

- **Jurisprudência do TJRO** citada na minuta (existência, número,
  órgão, relator, teor): skill `juris-tjro`.
- **STJ/STF**: conferir nos sites oficiais via busca web.
- **Metadados do processo** (classe, órgão julgador, fase, linha de
  movimentação) quando o contexto não os trouxer: skill `datajud` —
  útil inclusive no passo 1 do fluxo, para calibrar fase e último ato
  antes de formular o bloco do NotebookLM.

### 6. Sanções

Exposição a litigância de má-fé, multa por embargos protelatórios
(CPC, art. 1.026, §§ 2º–3º), sucumbência agravada, dever de lealdade. Em
especial nos segundos embargos: verificar se a peça demonstra a omissão
persistente de forma objetiva, com indicação precisa do que não foi
enfrentado, e não repete os primeiros por inconformismo.

### 7. Formais com consequência

Apontar **somente** o que tem consequência prática: citação de dispositivo
errado que enfraquece o argumento, numeração de tópico que quebra remissão
interna, nome de parte trocado. Vírgula, elegância e ordem dos argumentos
não entram no relatório. Não pentelhar.

### 8. Riscos redacionais

Verificação da minuta contra a skill `redacao-pecas`, fonte única das
heurísticas de redação — os itens abaixo **apontam** para lá, não
repetem as regras. Cada achado do relatório nomeia o item que o corrige.
A diferença para a camada 9 é a natureza do dano: aqui a construção
produz consequência jurídica (concede fato, desloca o enquadramento,
esconde a tese do leitor que decide); lá, produz efeito no leitor.

- **Autossuficiência** — remissões vagas ("acima", "anterior"), seção que
  não se sustenta lida em primeiro contato, ato citado sem ID ou data,
  pedido impugnado sem descrição prévia da causa de pedir → item 1.
- **Títulos** — título-assunto, título-charada ou título condicional em
  vez da tese da seção → item 2.
- **Admissões implícitas** — "não se contesta", "incontroverso";
  afirmação de fato onde caberia descrição do que o documento registra;
  negativa de fato onde caberia negativa de comprovação → item 3.
- **Enquadramento** — vocabulário pré-CPC/2015 ("carência de ação",
  "condições da ação"); impossibilidade material onde a tese é de
  competência; tecnicidade afirmada sem norma; réu "delimitando" o objeto
  da lide → item 4.
- **Precedente** — ementa inteira transcrita no corpo, acórdãos
  empilhados onde um vinculante resolve, tese firmada não identificada
  por tema → item 5. Aqui só a **forma** como o precedente entra no
  texto: precedente vinculante ignorado é camada 3, e prequestionamento
  ausente é camada 2.
- **Arquitetura** — matéria de liminar espalhada em vez de capítulo
  próprio; mérito respondendo à decisão em vez de à inicial; rótulo
  errado da peça; pedido dirigido a quem não é parte; preliminar que
  sinaliza a fraqueza que quer proteger; impugnação anunciada em vez de
  realizada; pedido de "regularização" onde o instituto é exibição
  → itens 3 e 6.
- **Formatação** — nível-1, barra horizontal, `###` em parágrafo
  corrido, citação sem itálico → item 8.

Calibração: esses achados entram como riscos, com localização e edit
proposto quando o conserto for cirúrgico. Nenhum deles dispara sozinho o
🔴 — mas acúmulo é indício de minuta não revisada, e pesa no veredito.
Admissão implícita é a exceção: entrega fato de graça e sobe para a
camada 3 quando o fato tiver consequência.

### 9. Clareza — vícios de linguagem que custam força

Camada **fora do veredito de risco**, e a única em que a regra do texto
intocado cede. Existe porque três padrões recorrentes da assessoria não
são erro nem feiura: são construções que **enfraquecem a peça enquanto a
escrevem**. A diferença em relação à camada 7 é que ali o problema é o
conteúdo do trecho; e em relação à camada 8, que lá o dano é jurídico e
aqui é o efeito que a construção produz no leitor.

Os três padrões:

- **Metalinguagem** — a peça anuncia o que vai fazer em vez de fazer, ou
  qualifica a própria demonstração enquanto a apresenta. Definição,
  exemplos e correção: `redacao-pecas`, item 7. O sintoma mais fácil de
  contar são os verbos de pigarro ("consigne-se", "anote-se",
  "registre-se, aliás"): mais de dois numa peça média já é padrão, não
  escolha.
- **Excesso de defesa** — a mesma ressalva de não-reconhecimento, de
  eventualidade ou de não-aquiescência repetida depois de já ter sido
  feita **uma vez em redação completa e no lugar certo** (`redacao-pecas`,
  item 7). Repetição não soma proteção: sugere que o subscritor teme
  estar admitindo algo. Sobrevivem apenas as ocorrências que fazem
  trabalho estrutural — tipicamente as que abrem um capítulo inteiro
  deduzido por eventualidade, e a que acompanha o único ponto em que a
  peça fixa número, data ou limite que poderia ser lido como
  aquiescência.
- **Autodepreciação** — a peça declara ao juízo a fraqueza da própria
  posição ("reconhece-se, com transparência, não haver precedente
  favorável", "a tese é minoritária", "não se ignora a dificuldade").
  Quase sempre a situação descrita é **simétrica** — não há precedente
  em nenhuma direção — e a redação converte empate em confissão. Este é
  o único subitem da camada com consequência tática, não apenas de
  clareza, e por isso pode ser levantado **mesmo sem autorização
  prévia**, como risco de exposição da camada 3.

Regras de operação, para que esta camada não vire licença para reescrever:

1. Fora da autodepreciação, os edits desta camada **não entram no
   veredito nem na contagem** de `edits_propostos` do relatório de risco.
   O 🟢/🟡/🔴 é decidido só pelas camadas 1 a 8.
2. Só se propõem **quando Franklin pedir** ou quando ele próprio observar
   o problema. Detectado sem pedido, vira no máximo uma linha em "Não
   mexi porque" ("padrão de metalinguagem recorrente, não tocado").
3. Saem em **relatório de estilo** (`type: Relatorio de Revisao de Estilo`),
   nunca misturados aos edits de risco — Franklin precisa saber, na hora
   de aplicar, qual edit protege a peça e qual apenas a afia.
4. O teste antes de propor: *este corte torna a peça mais forte perante
   um leitor hostil?* Se a resposta for "fica mais bonita", não é edit.
   "Eu escreveria diferente" continua proibido.
5. Preservar sempre o que a defensividade compra: ressalva *ad
   argumentandum* que impede leitura de adesão, concessão que sustenta um
   distinguishing, roteiro que orienta seção de vários subitens. Nem toda
   cautela é excesso.

## Economia de citações (heurísticas de Franklin)

Duas heurísticas fixas orientam como tratar jurisprudência e doutrina nas
minutas:

1. **Se a lei já é clara, dispensa jurisprudência e doutrina.** Citação
   sobre texto legal autoexplicativo não é ornamento neutro — é
   superfície de risco: precisa ser verificada, pode vir corrompida de
   agregador (números anonimizados, nomes de relator adulterados,
   ementas coladas de casos distintos), e pode carregar dictum que a
   parte contrária vira contra o Estado.
2. **Trocar uma citação de jurisprudência por um parágrafo de texto
   próprio explicativo é geralmente vantajoso.** Prosa própria diz
   exatamente o que a peça precisa, sem excesso nem passivo de
   verificação.

Aplicação na triagem — as heurísticas calibram os **edits**, não abrem
porta para reescrita:

- Citação **defeituosa, inverificável ou com conteúdo prejudicial**: o
  edit padrão é **remover e, se o argumento perder sustentação, propor
  um parágrafo curto de prosa própria** no lugar — não substituir por
  outro precedente. Precedente substituto só quando a autoridade é
  genuinamente necessária: tese contra-intuitiva, juízo historicamente
  resistente, matéria com divergência real, ou precedente vinculante que
  encerra a discussão.
- Citação **saudável mas supérflua** (lei clara, ementa que só repete o
  óbvio): não vira edit — a regra do texto intocado prevalece. No máximo
  uma linha em "Não mexi porque", para o registro de padrões da
  assessoria.
- Toda citação de jurisprudência presente na minuta entra na camada de
  ancoragem fática: existência, número, órgão, relator e data são
  afirmações verificáveis como quaisquer outras — e a experiência mostra
  que é onde a assessoria mais cola material corrompido de agregadores.

## Verificação adversarial via NotebookLM

**A verificação nunca é dispensada.** Não há caso em que o bloco de
perguntas deixe de ser montado — nem em processo administrativo (SEI),
nem quando os fatos parecem verificáveis pelo contexto, nem sob pressa.
Quando as respostas ainda não chegaram e Franklin precisa de posição,
o caminho é o veredito condicionado (seção final), nunca a dispensa.

Esta skill herda o método da skill `notebooklm-processos` (blocos
iterativos, perguntas autossuficientes sem dêixis, um fato por pergunta,
exigência de ID/página do rodapé, Franklin como intermediário) — leia
aquela skill se precisar do detalhe do método. O que muda aqui é a
**orientação**: lá, as perguntas constroem uma peça; aqui, elas tentam
**desmentir uma peça pronta**.

Regra de conversão: cada afirmação fática relevante da minuta vira uma
pergunta formulada **na direção que a derruba**, não na que a confirma.

- Minuta diz "o acórdão não apreciou o Tema 1306/STJ" → perguntar: "O
  acórdão de ID/fls. X menciona, enfrenta ou afasta, ainda que sem citar o
  número, a tese de [conteúdo do tema]? Cite o trecho e o ID/página do
  rodapé." (Se o acórdão enfrentou implicitamente, os embargos viram
  protelatórios.)
- Minuta diz "a parte autora não impugnou o cálculo" → perguntar: "Em
  alguma manifestação da parte autora há impugnação, ainda que genérica,
  aos cálculos apresentados? Cite trecho e ID/página."
- Minuta afirma data de intimação → perguntar pela certidão/expediente
  concreto que comprova a data, com ID/página.

Composição do primeiro bloco (adaptar ao caso, manter enxuto):

1. Inventário: rol das peças do material subido (IDs/páginas) e último
   ato judicial com data — calibra fase, prazo e o que existe.
2. **Prazo não se verifica pelo NotebookLM.** O PDF exportado dos autos
   geralmente **não** traz o expediente correto — a data de intimação e
   o termo inicial constam na **aba Expedientes do PJe**, que fica fora
   do arquivo (vale em especial para IPERON). Tempestividade é sempre
   item do **checklist de protocolo**, conferido por Franklin
   diretamente no PJe, e nunca presumida a partir do PDF nem das
   respostas do NotebookLM. Pergunta sobre citação/intimação no bloco
   serve no máximo como corroboração — a ausência no PDF não prova
   nada.
3. **Existência de cada documento que a minuta cita, referencia ou diz
   anexar** ("doc. anexo", ofícios, notificações, certidões, pareceres):
   está nos autos? Com que teor? A assessoria cita documentos do SEI que
   nunca foram juntados — se o documento sustenta a peça e não está nos
   autos, ele entra no **checklist de protocolo** (anexar junto) e sua
   transcrição é conferida no SEI, não pelo NotebookLM.
4. **Rastreamento de origem — sempre, em qualquer peça.** Serve para
   distinguir o que a parte pediu do que o juízo construiu:
   - "Transcreva integralmente o capítulo de pedidos da inicial (e da
     emenda, se houver), alínea por alínea, indicando contra qual réu
     cada pedido se dirige e qual período ou objeto abrange."
   - Para cada termo-chave do dispositivo atacado: "a expressão X
     aparece em alguma peça da PARTE? Em qual documento dos autos ela
     aparece pela primeira vez, com ID e página do rodapé?"
   - "Quem requereu a inclusão de cada réu no polo passivo — a parte, um
     corréu ou determinação do juízo? Transcreva os despachos
     correspondentes, com ID e página."
   - "A parte formulou pedido de tutela provisória? Em qual peça, com
     qual redação literal, dirigido a qual réu?"

   Racional: pedido principal ausente somado a tutela concedida sinaliza
   antecipação de pretensão estranha à causa — a antecipação é da tutela
   **pleiteada**, não cria pretensão nova (arts. 141 e 492). Atenção ao
   rito: onde a tutela pode ser concedida de ofício (art. 3º da Lei
   12.153/2009, p. ex.), a ausência de **pedido de tutela** não é vício;
   o vício é a ausência do **pedido principal** correspondente.
5. As 2–4 afirmações fáticas mais carregadas de consequência na minuta,
   formuladas adversarialmente.
6. Uma pergunta de varredura: "há nos autos documento, manifestação ou
   ato posterior a [data] que altere o quadro descrito acima?" — pega o
   documento que a assessoria não viu. Se a defesa depende de sequência
   temporal, substituir por pergunta de cronologia consolidada (datas +
   IDs de todos os atos relevantes).

Se as respostas derrubarem uma afirmação da minuta, isso **não** dispara
reescrita automática: dispara reclassificação do veredito e, se 🟡, o edit
cirúrgico mínimo que corrige a afirmação.

## Consistência com as posições de Franklin

Checar a minuta contra as estratégias que Franklin sustenta, além das teses
institucionais. As conhecidas (atualizar conforme a memória evoluir):

- **Estratégia recursal padrão**: dois embargos de declaração sucessivos
  invocando os Temas 1306/STJ e 339/STF quando o tribunal não aprecia a
  matéria, **antes** de REsp/RE. Uma minuta de REsp/RE logo após os
  primeiros embargos, sem esgotar essa via, contraria a estratégia — apontar
  como risco institucional, mesmo que a peça em si seja tecnicamente boa.
- **Carteira IPERON / Lei 5.075/2021**: o reajuste setorial de 18,25% não
  se estende a VPNI e vantagens pessoais. Minutas dessa série não podem
  conter concessões que fragilizem a tese nas demais.

Quando a minuta divergir de uma posição de Franklin, o relatório diz isso
explicitamente e classifica no mínimo 🟡 — a decisão de manter ou não a
divergência é dele, não de Claude nem da assessoria.

## Relatório em markdown OKF

Todo veredito sai como um concept OKF (okf.md, v0.1): arquivo `.md` com
frontmatter YAML contendo `type` obrigatório, pensado para acumular num
bundle e ser consumido depois por automação (roteamento por veredito,
estatística de erros da assessoria, feedback estruturado).

Template do frontmatter — campos de extensão em chaves estáveis, valores
enumerados onde possível, para parsing sem NLP:

```markdown
---
type: Relatorio de Triagem de Minuta
title: <peça> — <processo CNJ ou identificador>
description: <uma linha: veredito + risco dominante>
tags: [triagem, <tipo-de-peca>, <carteira, ex. iperon-5075>]
timestamp: <ISO 8601>
processo: <número CNJ>
peca: <embargos-declaracao | contestacao | apelacao | contrarrazoes |
  agravo-interno | recurso-inominado | resp | re | impugnacao |
  manifestacao | outro>
orgao: <PGE-IPERON | PGE-PPI | ...>
veredito: <apta | apta-com-ajustes | inapta>
riscos_fatais: <n>
riscos_relevantes: <n>
edits_propostos: <n>
verificacao_notebooklm: <realizada | pendente>
---
```

Corpo do relatório — usar `##` em diante, sem barras horizontais no corpo
(os `---` do frontmatter são delimitadores YAML, não regras horizontais):

```markdown
## Veredito

🟡 Apta com ajustes cirúrgicos. <Uma frase com o porquê.>

## Riscos identificados

### Fatais
<nenhum | lista>

### Exposição institucional
<lista com severidade e localização na minuta>

### Ancoragem fática
<afirmações verificadas ✓, desmentidas ✗, pendentes ?>

### Sanções e formais
<somente o que tem consequência>

### Redacionais
<achados da camada 8, cada um com localização e o item da
redacao-pecas que o corrige>

## Edits cirúrgicos

1. **Localização**: <tópico/parágrafo>
   **Original**: "<trecho exato>"
   **Substituto**: "<trecho exato>"
   **Motivo**: <risco que elimina, uma linha>

**Peça sempre limpa, mesmo com pendência.** Quando um edit ou uma minuta
gerada depende de conferência ainda pendente (citação de documento
oficial não verificável pela ferramenta, por exemplo), **a pendência
nunca aparece dentro do corpo do texto entregue como peça** — nem como
colchetes, nem como comentário em maiúsculas, nem de qualquer outra
forma que possa vazar para o protocolo se alguém esquecer de removê-la.
A peça entregue é sempre a versão final e limpa, pronta para assinatura
assim que a conferência externa confirmar o trecho pendente. A
pendência mora exclusivamente no relatório OKF (riscos) e no checklist
de protocolo — nunca no artifact da minuta em si.

## Não mexi porque

<opcional; uma linha por item imperfeito-mas-tolerável, para registro>

## Checklist de protocolo

<opcional; providências materiais que condicionam o protocolo e não são
edits de texto: documentos citados como anexo que não estão nos autos,
transcrições a conferir no SEI, decisão estratégica a registrar antes
da assinatura>

## Verificação NotebookLM

<bloco de perguntas enviado e respostas integradas, ou "pendente:
veredito condicionado às respostas 1–3">

## Citations

[1] <fonte externa citada no relatório, se houver — precedente, norma>
```

### Relatório de estilo

Quando a camada 9 for acionada, o produto é um **arquivo separado**, com
schema próprio, apontando para o relatório de risco pelo campo
`relatorio_risco`:

```markdown
---
type: Relatorio de Revisao de Estilo
title: <peça> — <processo CNJ>
description: <uma linha: vícios encontrados + quantos cortes>
tags: [estilo, clareza, <tipo-de-peca>, <carteira>]
timestamp: <ISO 8601>
processo: <número CNJ>
peca: <mesmo enum do relatório de risco>
orgao: <PGE-IPERON | PGE-PPI | ...>
relatorio_risco: <arquivo do relatório de risco>
autorizacao: <solicitada-por-franklin | observada-por-franklin>
edits_propostos: <n>
altera_tese: <nao>          # se for "sim", o edit pertence ao risco, não aqui
---
```

Corpo: `## Escopo` (declarando que não substitui a triagem de risco e que
nenhum edit altera tese), `## Diagnóstico` (os vícios encontrados,
nomeados), `## Edits` agrupados por vício, `## Não mexi porque` (o que a
defensividade compra) e `## Ordem de aplicação` quando os dois relatórios
tocarem a mesma seção da peça.

Convenções de bundle, para quando Franklin quiser acumular:

```
triagem/
├── index.md              # gerável por script a partir de title/description
├── log.md                # histórico cronológico das triagens
└── 2026/
    ├── <CNJ>-<peca>.md          # relatório de risco
    └── <CNJ>-<peca>-estilo.md   # relatório de estilo, quando houver
```

O frontmatter tipado é o que habilita o uso automatizado futuro: um script
que conta `veredito: inapta` por `peca` e por mês já é o relatório de
feedback para a assessoria — sem precisar reler prosa.

## Veredito condicionado

Quando a triagem depende de respostas do NotebookLM ainda não retornadas e
Franklin precisa de posição imediata, emitir veredito **condicionado**:
"🟡 condicionada — apta se as respostas 1–3 confirmarem prazo e teor do
acórdão; caso contrário 🔴". O relatório OKF sai com
`verificacao_notebooklm: pendente` e é atualizado quando as respostas
chegarem. Nunca emitir 🟢 incondicional sobre fato não verificado de
consequência fatal.

## Post-mortem de revisão detalhada

Quando Franklin revisa em detalhe um produto desta skill — comentários
de revisão, apontamentos em série sobre a triagem ou sobre a peça dela
derivada —, a rodada não termina no último apontamento. Ao percebê-la
encerrada, **oferecer o post-mortem sem esperar que ele peça**:

1. Classificar cada apontamento em um de quatro destinos:
   - **regra nova de redação** → propor o texto para a `redacao-pecas`;
   - **falha de triagem** (o vício estava na minuta e passou) → propor o
     ajuste na camada correspondente desta skill;
   - **pergunta de verificação que faltou** → propor a inclusão no bloco
     do NotebookLM;
   - **decisão específica do caso** → só memória do caso, não vira regra.
2. Entregar as propostas de edição a Franklin, arquivo por arquivo.
3. Registrar em memória as regras enunciadas, para valerem já na sessão
   seguinte — a skill só é atualizada quando ele aplica, mas a regra
   vale desde que enunciada.

O erro a evitar é apagar o exemplo ao generalizar a lição: extrair a
regra primeiro, e só então decidir se o caso concreto ainda ilustra algo
que a regra sozinha não ensina. Quando ficar, fica despersonalizado —
sem órgão, ID ou matéria —, salvo quando o concreto é justamente o que
ensina.
