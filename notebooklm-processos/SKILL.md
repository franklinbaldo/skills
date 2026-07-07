---
name: notebooklm-processos
description: >-
  Quando Franklin trabalha sobre um processo ESPECÍFICO — faz perguntas sobre
  os autos, pede ajuda para redigir documento ligado a um processo
  (contestação, ofício, parecer, memoriais, embargos, quesitos, recurso), ou
  se refere a "este caso", "este processo", "os autos", a um número CNJ, a uma
  ADPF/ADI/RE específica — e os documentos são volumosos ou estão apenas
  parcialmente no contexto, SUGIRA proativamente que ele os coloque no
  NotebookLM para fazermos perguntas direcionadas, com Franklin como
  intermediário (Claude não acessa o NotebookLM). As perguntas vão em blocos
  iterativos: um bloco por vez, variado entre frentes diferentes, esperando as
  respostas antes do próximo. Use SEMPRE que o trabalho for ancorado num
  processo concreto e a fundamentação puder se beneficiar de Q&A nas fontes,
  MESMO que Franklin não mencione o NotebookLM. NÃO use para perguntas
  jurídicas genéricas sem processo específico, nem quando os documentos já
  estão integralmente no contexto e são curtos.
---

## Por que esta skill existe

Franklin tem o NotebookLM e o usa para fazer perguntas ancoradas (grounded)
sobre conjuntos de documentos — autos processuais, ofícios, acórdãos,
manifestações, laudos periciais. Claude não tem acesso ao NotebookLM. Mas
Claude pode ser quem **formula** as perguntas certas, e Franklin é quem as
**executa** lá e traz as respostas de volta. A dupla é forte: Claude sabe o
que precisa saber para fundamentar a peça; o NotebookLM ancora as respostas
nas fontes e cita trechos, reduzindo o risco de Claude alucinar conteúdo de
um documento que só viu pela metade.

O ponto central da skill: Claude deve **lembrar dessa possibilidade sozinho**.
Não esperar Franklin pedir. Quando o trabalho gira em torno de um processo
concreto, oferecer o caminho NotebookLM faz parte do serviço.

## Antes de tudo: questionar qual é a tarefa de Franklin

Antes de aceitar o enquadramento do trabalho — e antes de redigir qualquer
coisa — desconfie da premissa sobre o que Franklin efetivamente deve executar.
É fácil, tanto para Claude quanto para o próprio Franklin, assumir que a tarefa
é "redigir a peça principal do processo" quando o encargo real é mais estreito,
diferente, ou nem sequer dele. Esse erro custa caro: produz-se um documento
robusto que resolve o problema errado.

A chave costuma estar em **por que e como aquele documento chegou até
Franklin**. Os autos quase sempre contêm um despacho, ofício ou ato de
encaminhamento interno que redirecionou o processo à unidade em que Franklin
atua — e é nesse ato, não na petição inicial nem no ofício do tribunal, que
mora a definição concreta da tarefa.

Atenção a um ponto que arruína perguntas boas: **o NotebookLM não conhece
Franklin nem o nosso contexto**. Ele só lê o PDF. Uma pergunta como "qual ato
encaminhou o processo à unidade de Franklin?" não tem referente para ele —
"unidade de Franklin", "minha unidade", "este caso", "nós" são dêixis que só
fazem sentido entre Claude e Franklin. Antes de mandar qualquer pergunta,
**traduza toda referência pessoal ou contextual para o termo concreto que
aparece nos autos**: o nome do órgão em que Franklin atua naquele processo
(por exemplo, PGE-PPI ou PGE-IPERON, conforme o caso), o número do documento,
o nome da parte. A pergunta tem de ser autossuficiente — compreensível para
quem só tem o PDF e nenhuma memória da nossa conversa.

Perguntas a fazer (já com o nome do órgão concreto no lugar da referência
pessoal):

- Qual despacho ou ato encaminhou este processo à [nome do órgão, ex.: PGE-PPI],
  e o que ele pede exatamente? (minutar peça de mérito? dar parecer pontual?
  revisar minuta alheia? opinar sobre aspecto específico? só triar?)
- A [nome do órgão] é indicada como responsável pela manifestação, ou o
  encaminhamento sugere recorte mais estreito (um interesse específico desse
  órgão, e não a defesa global)?
- Há prazo fixado, e ele é atribuído à [nome do órgão] ou a outra unidade?
- O processo foi encaminhado à [nome do órgão] para manifestação, ou apenas
  para ciência ou redistribuição?

Sinais de alerta de que a tarefa presumida pode estar errada: a matéria foge à
especialização de Franklin; outra unidade ou procurador já estava conduzindo o
feito; o documento parece ter "sobrado"; o encaminhamento é genérico. Em
qualquer desses casos, o **primeiro bloco de perguntas ao NotebookLM** deve
mirar o ato de encaminhamento e o papel de Franklin — *antes* de perguntar o
que a inicial alega ou de esboçar fundamentação. Defina a tarefa, depois
execute-a; não o contrário.

## Quando oferecer (proativamente)

Ofereça quando as duas condições se somam:

1. O trabalho está ancorado num **processo específico** — perguntas sobre os
   autos, ou redação de qualquer peça/documento ligado a um caso concreto
   (número CNJ, ADPF/ADI/RE, processo administrativo, PAD).
2. A fundamentação se beneficiaria de **fatos ancorados nas fontes** que Claude
   não tem integralmente no contexto: autos extensos, múltiplos documentos,
   ofícios e manifestações de vários órgãos, laudos, acórdãos longos.

O gatilho mais comum é Franklin colar um resumo dos autos (como fez na ADPF
1.322) ou descrever um caso e pedir uma peça. Nesses momentos, antes ou logo
depois de começar, vale dizer: *"esses autos parecem bons candidatos a entrar
no NotebookLM — se você subir os documentos, eu formulo perguntas para você
rodar lá e ancorar a peça nas fontes."*

## Quando NÃO oferecer

- Pergunta jurídica genérica, sem processo concreto ("como funciona embargos de
  declaração com efeitos infringentes?").
- Os documentos relevantes já estão **inteiros** no contexto e são curtos —
  nesse caso Claude já tem o que precisa, oferecer NotebookLM é fricção inútil.
- Tarefas não-processuais (blog, paper, Suno, código, genealogia).
- Franklin já indicou que não quer usar o NotebookLM neste caso. Não insista.

## O fluxo de trabalho

Claude não acessa o NotebookLM; Franklin é o intermediário. O ciclo:

1. **Claude formula perguntas** — específicas, uma ideia por pergunta,
   redigidas para o NotebookLM responder com citação às fontes — e as
   entrega **num artifact** (ver seção "Blocos em artifacts" abaixo).
2. **Franklin roda no NotebookLM** e cola as respostas de volta.
3. **Claude integra** as respostas na análise ou na peça, tratando-as como
   conteúdo dos autos (e não como conhecimento próprio).

Trabalhe **um bloco por vez**, não tudo de uma vez. Mande um bloco de
perguntas, espere as respostas, e só então formule o próximo. O motivo é
substantivo, não de cortesia: o que as fontes respondem no primeiro bloco
muda quais perguntas valem a pena no segundo. Despejar todas as perguntas de
uma vez trava o trabalho num único enquadramento do problema antes de Claude
ver o que os autos efetivamente dizem — e foi exatamente isso que Franklin
pediu para evitar. Cada bloco é uma rodada de reconhecimento que recalibra a
seguinte.

Dentro de um bloco, **varie os temas e as abordagens**. Não concentre as
perguntas todas num único assunto nem numa única hipótese de solução. Um bloco
monotemático aposta tudo numa leitura do caso; um bloco variado abre frentes —
um pouco do que a inicial alega, um pouco do que as manifestações dizem, um
pouco dos fatos quantitativos, um pouco de eventuais lacunas. Assim as
respostas iluminam o problema por ângulos diferentes e Claude não se fecha
cedo demais numa tese. Mantenha o bloco enxuto (até cerca de dez perguntas
numeradas, conforme a necessidade da rodada) para Franklin rodar e devolver
sem fadiga.

## Blocos em artifacts (payload limpo de colar)

Todo bloco de perguntas vai num **artifact markdown** — um arquivo
apresentado a Franklin, separado da conversa. O motivo é operacional:
Franklin copia o bloco inteiro para o NotebookLM, muitas vezes do celular,
e o artifact dá um payload limpo com botão de copiar, sem que ele precise
garimpar as perguntas no meio da prosa de Claude.

Regras do artifact:

- **Estrutura fixa: cabeçalho de instruções + perguntas numeradas, nada
  mais.** O cabeçalho fala **com o NotebookLM** (é prompt, não comentário);
  as perguntas vêm em seguida. Nenhuma prosa dirigida a Franklin entra no
  artifact — todo o raciocínio (o que este bloco quer descobrir, qual
  pergunta é a falsificadora, o que decide o próximo passo) fica **na
  conversa**. O artifact é payload; a conversa é o pensamento.
- **O cabeçalho instrui o NotebookLM sobre como proceder e como
  referenciar.** Modelo-base, a adaptar conforme o bloco:

  > **Instruções:** Responda às perguntas numeradas abaixo, uma a uma,
  > exclusivamente com base nos documentos carregados neste notebook.
  > Para cada resposta: (1) transcreva entre aspas o trecho literal que a
  > fundamenta; (2) identifique o documento de origem por tipo e
  > autor/órgão (ex.: "manifestação da SEPAT", "acórdão da 1ª Câmara
  > Especial") e informe a localização que consta no **rodapé do PDF** —
  > número do ID para documentos do SEI, página/ID dos autos para
  > documentos do PJe; (3) se as fontes não cobrirem o ponto, responda
  > "as fontes não informam" — não deduza nem complete com conhecimento
  > externo; (4) se houver documentos divergentes sobre o mesmo ponto,
  > aponte todos. Não faça análise jurídica nem emita opinião: limite-se
  > ao que os documentos dizem.

  Adaptar por necessidade do bloco: um bloco sobre prazos acrescenta
  "transcreva datas e certidões literalmente, com dia, mês e ano"; um
  bloco de verificação de minuta (skill `revisao-minutas`) acrescenta
  "responda inclusive quando a resposta for parcial ou implícita,
  indicando o grau de correspondência"; um bloco sobre valores pede
  transcrição numérica exata. O cabeçalho é curto — instruções que valem
  para toda pergunta; o que vale para uma pergunta só vai na própria
  pergunta.
- **Um artifact por bloco**, nomeado de forma rastreável:
  `bloco-1-<identificador do processo>.md`, `bloco-2-...`. Bloco novo é
  artifact novo — não editar o anterior, para preservar o histórico da
  investigação na conversa.
- **Autossuficiência vale dobrado aqui**: como o artifact será colado
  inteiro numa ferramenta que não conhece o contexto, cada pergunta segue
  as regras da seção "Como formular boas perguntas" sem depender de nada
  fora do próprio bloco — nem mesmo de outra pergunta do bloco.
- Perguntas redirecionadas para pesquisa externa (web, juris-tjro,
  ChatGPT) **não entram** no artifact do NotebookLM. Se houver queries
  externas para Franklin rodar, elas vão num artifact próprio e separado,
  identificado como tal e com cabeçalho adequado à ferramenta de destino
  (ex.: exigência de número da ação, órgão julgador, data e situação para
  resultados de jurisprudência).

## O NotebookLM só sabe o que está nos autos

Limite estrito de escopo, sem exceção. O NotebookLM responde a partir dos
documentos que Franklin subiu — o PDF dos autos, as peças, os ofícios, as
manifestações, os laudos. Ele **não** é uma ferramenta de pesquisa jurídica
externa e tem acesso pobre a informação fora das fontes carregadas. Portanto,
**toda pergunta deve ser sobre o conteúdo dos documentos do processo**: o que
um documento diz, onde diz, qual o teor de uma manifestação, qual o pedido,
qual a localização (ID/página) de uma passagem.

Nunca pergunte ao NotebookLM sobre o que está **fora** dos autos: o conteúdo de
uma lei não juntada, teses doutrinárias, jurisprudência, precedentes do STF,
o que a Constituição "impõe", como tribunais vêm decidindo, qual a melhor
interpretação de um dispositivo. Esse tipo de pesquisa — lei, doutrina,
jurisprudência, tese — é feito com **outras ferramentas** (web search, a skill
juris-tjro para o TJRO, ou o ChatGPT, conforme o caso), nunca com o NotebookLM.
Se uma pergunta que Claude pensou em fazer não pode ser respondida apenas
lendo os documentos do processo, ela está no lugar errado: tire-a do bloco e
encaminhe-a para a ferramenta adequada.

Há um segundo limite, temporal: **o PDF dos autos é um retrato da data de
exportação**. Ato praticado depois da exportação não aparece nem para o
NotebookLM — a varredura "há algo posterior a [data]?" só alcança o que
está no arquivo. Quando a data de exportação for incerta, antiga, ou a
peça depender da fase atual do processo, conferir a **linha de
movimentação corrente pela skill `datajud`** (API pública do CNJ, por
número CNJ) antes de fechar o trabalho: é ela que pega a decisão
publicada ontem que o PDF não tem. O datajud traz metadados e
movimentação, não teor — se a movimentação revelar ato novo relevante,
o teor entra pelo PJe via Franklin.

Vale para as perguntas falsificadoras também: elas devem testar a tese de
Claude **contra o que está nos autos** (a inicial antecipou meu argumento? a
manifestação tem uma ressalva que eu ignorei? há nos autos indício que
contraria minha premissa de fato?), e não contra o estado da arte jurídico
externo.

## Quando a pergunta é externa, Claude mesmo pesquisa

Tirar uma pergunta do bloco do NotebookLM não é abandoná-la — é redirecioná-la.
Quando o trabalho revela uma questão que só se resolve fora dos autos (o
alcance de um dispositivo constitucional, como o STF ou o STJ vêm decidindo
uma tese, o estado da doutrina sobre um instituto, o texto de uma norma não
juntada), Claude deve **dizer isso a Franklin e oferecer-se para pesquisar com
as próprias ferramentas** — `web_search`/`web_fetch` para jurisprudência,
doutrina e legislação em geral, a skill `juris-tjro` para precedentes do
TJRO, e a skill `datajud` para metadados e linha de movimentação de
qualquer processo (inclusive os conexos que a peça cita e cujos autos não
estão no notebook). Não há motivo para devolver a pergunta a Franklin como
tarefa dele se Claude pode executá-la.

Quando uma peça ou subsídio fica pronto e deixa em aberto um ponto de mérito
que dependerá de pesquisa externa (tipicamente, o que a unidade seguinte terá
de desenvolver), Claude deve **antecipar e já entregar as queries de busca
prontas**, em vez de só apontar que a pesquisa será necessária. O mesmo
princípio das perguntas ao NotebookLM se aplica aqui, adaptado: queries
específicas e variadas, e ao menos uma voltada a **falsificar** a tese que
Claude pretende sustentar — buscar o precedente ou a doutrina *contrária*, não
só a favorável, para que Claude conheça o adversário antes de escrever.

Sobre quem executa: há uma economia a respeitar. Rodar muitas buscas consome
tokens de Claude; **conferir um retorno é mais barato que pesquisar do zero**.
Por isso, quando a pesquisa externa for ampla ou exploratória, o padrão é
Claude **entregar as queries prontas** para Franklin rodá-las na ferramenta de
sua preferência (ChatGPT, em geral) e trazer o retorno, cabendo a Claude então
**conferir, criticar e integrar** — checando números de precedente, datas,
relator e trânsito em julgado, do mesmo modo como se exige ID/página do
NotebookLM. Claude roda a busca com as próprias ferramentas quando isso for
mais eficiente (uma ou duas consultas pontuais, verificação rápida de um fato),
mas não varre a web por atacado quando Franklin pode fazê-lo a custo menor. Em
qualquer caso, Claude entrega as queries de modo que possam ser executadas tal
como estão, e orienta Franklin a exigir da ferramenta as âncoras verificáveis
(número da ação, órgão julgador, data, situação) sem as quais o resultado não
é confiável.

## Inclua perguntas que tentem falsificar suas próprias teses

Esta é uma regra de método, não opcional. Sempre que Claude já tem uma tese, um
argumento ou um enquadramento em construção, **todo bloco deve conter ao menos
uma pergunta desenhada para derrubá-lo**, não para confirmá-lo. Perguntar só o
que confirma a tese transforma o NotebookLM numa máquina de coletar munição a
favor — viés de confirmação puro. A investigação séria pergunta contra o
próprio alvo.

Concretamente, para cada tese que Claude esteja sustentando, formule a pergunta
na direção que mais a ameaça:

- Se a tese é "a lei tem salvaguarda contra X", pergunte se há nos autos algo
  que mostre a salvaguarda **falhando, sendo insuficiente ou contornada** — não
  apenas se a salvaguarda existe.
- Se a tese é "não há lesão porque a lei não foi aplicada", pergunte se há
  **qualquer** indício de aplicação, efeito indireto, ato preparatório ou
  expectativa de aplicação que contrarie a não-lesividade.
- Se a tese é "o argumento da parte adversa se ancora no dispositivo Y, que é
  fraco", pergunte se a parte adversa **também** se ancora num dispositivo Z
  mais forte que Claude esteja subestimando.
- Se Claude pretende afastar um vício por um fundamento, pergunte se as fontes
  apontam um **fundamento autônomo** do mesmo vício que o argumento de Claude
  não alcança.

O objetivo é que Claude descubra os pontos fracos da própria tese **pelas
fontes**, antes que a parte adversa ou o julgador os descubram. Uma resposta
que enfraquece a tese de Claude não é um fracasso do bloco — é o resultado mais
valioso que ele pode produzir, porque chega a tempo de corrigir o rumo. Se uma
rodada confirma tudo o que Claude já pensava, desconfie de que as perguntas
foram frouxas e endurece o próximo bloco.

Caso especial: quando o objeto do trabalho é uma **minuta pronta da
assessoria** (triagem para peticionamento), o método inverte por inteiro — a
minuta é a tese e todas as perguntas miram derrubá-la. Esse modo tem skill
própria, `revisao-minutas`, que herda daqui o formato dos blocos (incluindo
a entrega em artifacts) e muda a orientação.

## Como formular boas perguntas para o NotebookLM

O NotebookLM responde melhor a perguntas factuais e ancoráveis. Calibrar
assim:

- **Específica e singular.** Uma pergunta = um fato. Em vez de "o que dizem as
  manifestações?", pergunte "a SEDAM afirmou que a área X tem auto de infração
  ambiental ativo? Em qual documento?".
- **Peça a fonte com a localização do rodapé.** "Cite o documento e o trecho"
  — força ancoragem e dá a Claude o material para citar com precisão na peça.
  Para documentos do **SEI**, peça expressamente o **número do ID** do
  documento; para documentos do **PJe**, peça o **número da página / ID dos
  autos**. Essas referências costumam constar no **rodapé do PDF** a que o
  NotebookLM tem acesso, e permitem citar a localização exata na peça (por
  exemplo, "conforme manifestação da SEPAT, ID nº ..."), em vez de um genérico
  "consta nos autos". Formule sempre algo como: "cite o trecho e informe o ID
  (SEI) ou a página/ID dos autos (PJe) que aparece no rodapé do documento".
- **Mire o que falta.** Pergunte o que Claude **não** consegue deduzir do que
  já tem: datas, números de protocolo, nomes, valores, teor exato de um
  dispositivo, o que cada órgão concretamente manifestou, se um documento
  existe nos autos.
- **Evite perguntas de opinião jurídica.** O NotebookLM é para extrair o que
  está nas fontes; a análise jurídica é trabalho de Claude. Pergunte fatos,
  não teses.
- **Varie dentro do bloco.** Não enfileire seis perguntas sobre o mesmo
  documento ou a mesma tese. Distribua entre frentes diferentes — alegações da
  inicial, teor das manifestações, dados de fato, lacunas — para que a rodada
  abra o leque em vez de aprofundar um só ponto.
- **Autossuficiente, sem dêixis.** O NotebookLM não conhece Franklin nem a
  nossa conversa. Nunca escreva "minha unidade", "unidade de Franklin", "este
  caso" ou "nós"; substitua pelo termo concreto dos autos — o nome do órgão
  (PGE-PPI, PGE-IPERON, conforme o processo), o número do documento, o nome da
  parte. A pergunta deve ser compreensível para quem só tem o PDF.
- **Inclua a pergunta que te derruba.** Ao menos uma por bloco deve mirar o que
  enfraquece a tese de Claude, não o que a confirma (ver seção acima).
- **Abra o bloco 1 com uma pergunta de inventário.** Antes de qualquer
  mérito, pergunte o rol das peças que compõem o material subido (com
  IDs/páginas) e o último ato judicial ou administrativo com data. Custa
  uma pergunta e calibra todas as outras: revela a fase do processo, o
  que existe e o que falta — e os PDFs de autos costumam trazer índice
  nas primeiras páginas, que o NotebookLM sabe usar.
- **Quando a tese depende de sequência temporal, peça a cronologia
  consolidada.** Uma pergunta do tipo "liste em ordem cronológica os
  atos [negociais/administrativos/processuais] relevantes, com data,
  documento de origem e ID/página" rende mais que reconstituir a linha
  do tempo por fragmentos de respostas — e é na cronologia que moram
  fatos supervenientes, caducidades e preclusões.
- **Numere as perguntas** para Franklin colar as respostas na ordem.

Exemplo de **primeiro bloco** bem formulado (caso ADPF 1.322) — note como
abre questionando a própria tarefa de Franklin e só depois toca a matéria,
variando as frentes em vez de esgotar uma só, e deixando as respostas guiarem
o próximo bloco:

> 1. Qual despacho ou ato de encaminhamento determinou a manifestação da
>    PGE-PPI (Procuradoria de Patrimônio Imobiliário) neste processo, e o que
>    ele pede exatamente — minutar peça, dar parecer, revisar, opinar sobre
>    aspecto específico, ou só ciência? Cite o trecho e o ID (SEI) ou página/ID
>    dos autos (PJe) do rodapé.
> 2. O ato de encaminhamento fixa prazo, e ele é atribuído à PGE-PPI ou a outra
>    unidade? Informe o ID/página do rodapé.
> 3. A petição inicial menciona expressamente a lei estadual de Rondônia, e
>    impugna artigos específicos ou a lei em bloco? Cite o trecho e o ID/página.
> 4. A manifestação da SEPAT afirma que houve ou não titulação efetiva com base
>    na lei estadual? Cite a passagem e o ID/página do rodapé.

## Integração das respostas

Interprete **"as fontes não informam" como "não consta no material
subido ao notebook"** — nunca como inexistência do fato ou do documento.
O NotebookLM só vê o PDF que Franklin carregou; uma certidão pode
existir no PJe, e um ofício pode existir no SEI, sem estarem no arquivo.
A distinção tem consequência prática: "não consta nos autos" pode ser
argumento (ônus da prova, documento não juntado pela parte contrária),
mas só depois de confirmar que o material subido corresponde aos autos
completos — e documentos administrativos citados nas peças do Estado
devem ser conferidos no SEI, fora do alcance do NotebookLM.

Quando Franklin trouxer as respostas do NotebookLM, trate-as como **conteúdo
dos autos**: fundamente a peça nelas, com a precisão que elas trazem, e
preserve as referências de localização que o NotebookLM citou — o ID do SEI ou
a página/ID dos autos do PJe —, levando-as para a peça de modo que cada
afirmação tenha sua âncora verificável no documento de origem. Se uma resposta
vier vaga ou o NotebookLM disser que a fonte não cobre o ponto, registre isso
honestamente — é informação útil (o documento não existe ou é silente) e pode
até virar argumento, como a ausência de titulação efetiva virou preliminar de
não-lesividade na ADPF 1.322.
