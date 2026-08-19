---
name: redacao-pecas
description: >
  Heurísticas de redação de peças judiciais e pareceres para Franklin
  Baldo (PGE-RO). Use SEMPRE que estiver escrevendo, reescrevendo ou
  editando peça processual ou parecer — contestação, recurso, embargos,
  contrarrazões, manifestação, memoriais, agravo, parecer — seja
  redação do zero, seja reescrita pós-triagem da skill revisao-minutas.
  Dispara em qualquer produção de texto jurídico-processual, mesmo que
  Franklin não a invoque. A revisao-minutas usa este arquivo como
  checklist das categorias de risco redacional. NÃO use para blog,
  papers, e-mails ou documentos não jurídicos.
---

# Redação de peças — práticas

Cada item descreve a prática a exercitar, o padrão em que ela se
realiza, e o vício que ela substitui. Sempre que possível, a prática
traz o par vício → correção na mesma linha ("não dispõe de meios" →
"extrapola a competência"): o contraste imediato ensina mais que a
regra isolada. Regras, não sugestões.

## Anamnese antes de qualquer linha

**Nenhuma peça começa pelo texto, nem pelo esqueleto: começa pela
anamnese do caso**, gravada em `anamnese.md` ao lado da peça. Sem
esperar pedido, e mesmo quando o ato a responder parece trivial.

Sete blocos, todos lidos dos autos por `documento_download`:

1. **Partes** — quem a inicial aponta **e** quem o PJe autuou, em
   colunas separadas. Não são a mesma coisa com a frequência que se
   supõe, e a divergência não se anuncia.
2. **Pedido** — o que se pede, com que causa de pedir e que valor.
3. **Linha do tempo** — um ato por linha, com data, órgão e ID. Inclui
   os atos do processo administrativo, quando ele instrui a inicial.
4. **Onde o processo está** — a última decisão conhecida e o que ela
   produziu. Se houver lacuna entre dois atos, ela entra na linha do
   tempo como lacuna, não se preenche por inferência.
5. **O ato a responder** — a quem se dirige, o que exige, prazo
   conferido pelo `contar_prazo.py`, e as incongruências do texto.
6. **O que já se fez** — peças protocoladas, citação, tarefas. "Nada, e
   não há registro de citação" é resposta, e das mais importantes.
7. **Lacunas** — o que falta saber, cada uma com o que ela decide.

Fecha com a pergunta **há ato a praticar?**, cuja resposta admissível
inclui "a decidir". Anamnese que só descreve o processo sem chegar a
essa pergunta não terminou.

**Por que este bloco existe.** Ele foi acrescentado depois de quatro
versões descartadas da mesma manifestação
(7001815-16.2026.8.22.0000, 2026-08-19). Cada versão caiu por um fato
que a anamnese daria de saída: o objeto da ação era aposentadoria e não
licença-prêmio; havia sentença de indeferimento da inicial cinco meses
antes; e o polo passivo autuado no PJe divergia do apontado na inicial.
Os três apareceram tarde, um por acidente diferente, porque a redação
começou antes da leitura. Anamnese é barata; peça descartada não é.

## Fluxo de produção

Feita a anamnese, peça longa nasce em dois tempos: primeiro o esqueleto
— títulos assertivos (item 2) mais uma linha por seção dizendo o que ela
demonstra —, submetido a Franklin; o texto só depois da aprovação.
O esqueleto barato de corrigir é o mesmo documento que, aprovado,
vira o sumário-defesa. Em reescrita pós-triagem da revisao-minutas,
o fluxo é o mesmo, partindo do relatório OKF. O entregável é sempre
`.md`; Word apenas se pedido, e por conversão (md→docx via software),
nunca por reescrita do conteúdo.

## Sidecar de verificação

A peça nunca sai sozinha. Junto dela, sempre e sem esperar pedido, sai
um arquivo `.md` em OKF — `<CNJ>-<peca>-verificacao.md` — contendo o
prompt que confere a peça contra os autos. Peça e sidecar saem juntos ou
não saem.

**O sidecar se responde sozinho.** `scripts/verificar_peca.py` manda o
corpo do sidecar ao Gemini junto das fontes dos autos, baixadas por
`documento_download`, e grava a resposta. Não há passo manual de colar
prompt em lugar nenhum: verificação que depende de alguém lembrar é
verificação que não acontece sob prazo, que é quando ela importa.

```bash
uv run --with google-genai --with keyring python scripts/verificar_peca.py \
    <CNJ>-<peca>-verificacao.md --autos casos/<cnj>/docs
```

**A resposta vai para arquivo próprio** — `<sidecar>-respostas[-<bloco>].md`,
que referencia o sidecar no frontmatter; o sidecar recebe só o ponteiro em
`respostas:` e o estado em `veredito_gemini:`. Prompt e resultado têm ciclos
de vida distintos: o prompt se reenvia a cada versão da peça, a resposta é de
um modelo, numa data, sobre um conjunto de fontes. Fundidos, o prompt cresceria
a cada rodada e a comparação entre rodadas — que é o registro de que a
correção resolveu a divergência — se perderia.

**Junte as fontes antes de perguntar, e confira quais são.** Na primeira
execução real (2026-08-19) o sidecar foi enviado só com os anexos da
inicial, e três perguntas voltaram "não encontrada" porque o despacho
atacado não estava entre as fontes. Não era defeito da peça nem do
prompt: era fonte faltando. A seção "fora de escopo" da resposta existe
para expor isso — leia-a antes da conclusão.

Fonte não é só PDF. Despacho e sentença do PJe vêm em HTML por
`documento_download`; teor de expediente do Kanoê não vem em arquivo
nenhum e precisa ser salvo como texto. O script aceita `.pdf`, `.html`,
`.md` e `.txt`.

**O que o sidecar pede, e o que não pede.** A conclusão pedida é de
**aptidão fática**: se toda afirmação da peça sobre os autos se
sustenta. Não se pede — nem se aceita — conclusão sobre aptidão a
peticionamento: tempestividade depende da aba Expedientes do PJe, que
não está no PDF dos autos; cabimento, estratégia de carteira e posição
institucional dependem de contexto que a fonte não tem. Prompt que pede
veredito de protocolo recebe resposta confiante e inútil. O veredito é
de Franklin; o sidecar só lhe entrega o fato conferido.

**Regra de derivação.** Toda afirmação da peça sobre os autos — data,
ID, teor da decisão, o que a parte alegou, existência de documento
citado, valor, rubrica — vira uma pergunta formulada **na direção que a
derruba**, não na que a confirma (o método — perguntas
autossuficientes, sem dêixis, um fato por pergunta, exigindo ID e página
do rodapé — vem da skill `notebooklm-processos`, e vale igual com o
Gemini; a orientação adversarial é a da `revisao-minutas`).

Frontmatter:

```markdown
type: Prompt de Verificacao de Peca
title: <peça> — <processo CNJ>
description: <uma linha: o que a verificação decide>
tags: [verificacao, <tipo-de-peca>, <carteira>]
timestamp: <ISO 8601>
processo: <número CNJ>
peca_verificada: <arquivo da peça>
orgao: <PGE-IPERON | PGE-PPI | ...>
afirmacoes_verificaveis: <n>
veredito_gemini: <pendente | apta-faticamente | com-divergencias>
```

Corpo do prompt, cinco blocos:

1. **Papel e fontes** — o que o Gemini deve fazer (conferir as
   afirmações abaixo exclusivamente contra as fontes carregadas), e a
   regra de que ausência nas fontes é "não encontrada", nunca
   "desmentida".
2. **Ancoragem** — uma pergunta por afirmação da peça, autossuficiente,
   sem dêixis, um fato por pergunta, exigindo trecho e ID/página do
   rodapé.
3. **Rastreamento de origem** — as quatro perguntas fixas: capítulo de
   pedidos transcrito alínea por alínea com destinatário e objeto;
   primeira aparição nos autos de cada termo-chave do dispositivo
   atacado; quem requereu a inclusão de cada réu no polo passivo;
   redação literal do pedido de tutela, se houver.
4. **Superveniência** — "há nos autos documento, manifestação ou ato
   posterior a [data] que altere o quadro descrito acima?"
5. **Formato de resposta exigido** — por pergunta: *confirmada /
   desmentida / não encontrada*, mais trecho e ID/página; ao final, a
   conclusão de aptidão fática; e, por último, a lista do que ficou
   fora de escopo ("estes pontos não são verificáveis nas fontes
   carregadas: ..."). O formato é o que faz a resposta voltar
   estruturada, comparável entre rodadas, em vez de virar prosa solta.

O script grava as respostas em `<sidecar>-respostas[-<bloco>].md` e vira
`veredito_gemini` para `respondido`. Divergência apontada não dispara
reescrita automática: dispara correção da afirmação na peça, e a peça
corrigida gera sidecar v2 — que se responde de novo, gerando outro
arquivo de respostas. É a comparação entre os dois que registra que a
divergência foi resolvida.

## 1. Escreva cada seção para o leitor que começa por ela

O juiz lê o tópico que lhe interessa; o assessor confere um item; a
parte contrária ataca um capítulo. Escreva cada seção como texto de
entrada.

**Pratique:**
- Abra o subitem situando o leitor em uma frase — o que está em
  discussão ali e de onde vem. Recapitulação de uma linha custa nada
  e torna a seção portátil ("Uma vez lançado," → "Averbado o período,
  o lançamento incorpora-se aos assentamentos...").
- Identifique cada ato pelo que ele é: decisão pelo ID ("a ordem" →
  "a decisão de ID X determinou..."), requerimento pela data, ofício
  pelo número.
- Remeta apenas a item numerado ("como visto acima" → "como
  demonstrado no item IV.4"), e recapitule junto o essencial do que
  lá se demonstrou.
- Antes de refutar um pedido, descreva-o: qual pedido, fundado em que
  fatos, com que valor. O ataque vem depois da descrição — e quase
  sempre sai mais forte, porque a descrição bem feita já expõe a
  fragilidade.
- Ao impugnar uma decisão, transcreva o dispositivo uma vez, no
  capítulo dono do tema, e argumente contra o texto transcrito.

**Em vez de:** "na preliminar anterior", "tudo quanto acima", "o
pedido indenizatório" (qual?), "o próprio dispositivo" (de quê?).

## 2. Faça do sumário a defesa em miniatura

Quem lê apenas os títulos deve terminar sabendo a conclusão de cada
tópico. Escrever o título por último, depois que a seção existe,
ajuda: o título é a tese da seção comprimida.

**Pratique:**
- Formule o título como afirmação completa: sujeito, verbo, conclusão
  ("Do que os documentos provam e do que não provam" → "Os documentos
  juntados pelo réu registram X, não Y").
- Tese subsidiária ganha subitem próprio, com título igualmente
  afirmativo ("Ainda que de averbação se tratasse, faltam-lhe os
  pressupostos" → dois títulos: "A averbação pressupõe certidão, e
  nenhuma foi apresentada" + "A averbação produz efeitos definitivos
  e não admite a qualificação de provisória"). Dois títulos
  assertivos valem mais que um condicional.
- Ponha no título da preliminar o precedente vinculante que a
  sustenta ("(Tema N do STF)"): o leitor vê a âncora antes do
  argumento.
- Um título, uma tese. Precisou de "e", avalie dividir.

**Em vez de:** títulos-assunto ("Da documentação"), títulos-charada,
títulos condicionais.

## 3. Escreva do que se sabe, na medida em que se sabe

A força da peça pública está em nunca afirmar além do que os autos
sustentam — o que também significa nunca conceder além do necessário.

**Pratique:**
- Descreva o que o documento registra, não o fato que ele
  supostamente prova ("as fichas comprovam a retenção" → "as fichas
  registram descontos sob a rubrica X"). O registro é fato seguro; o
  fato provado é conclusão que cabe ao juízo.
- Calibre a negativa ao estado da prova ("não houve ingresso" → "não
  há comprovação do ingresso"). Para a defesa, quase sempre basta que
  o fato não esteja provado — e essa formulação é inatacável.
- Impugne mostrando ("impugnam-se todas as alegações na forma do
  art. 341" → três negativas concretas, cada uma retomada adiante com
  documento). A impugnação específica é isso; feita assim, o art. 341
  se cumpre sem ser citado.
- Atribua cada alegação a quem a fez — inicial, corréu, terceiro. A
  atribuição precisa evita imputar à parte o que ela não disse e
  revela contradições entre os autores.
- Do fato que não se pretende discutir, silencie. O silêncio preserva
  a questão para a sede própria; a declaração de não-contestação
  ("fato incontroverso", "e o réu não a contesta") a entrega de
  graça.

## 4. Fundamente na norma e enquadre com precisão

**Pratique:**
- Extraia o conceito do texto normativo, nesta ordem: primeiro a
  norma (ou a doutrina, nomeada), depois o conceito que dela decorre
  ("a averbação, em sentido técnico, é..." → "o art. X dispõe...;
  averbar é, nesse regime normativo, ..."). Tecnicidade afirmada não
  demonstra nada — o juiz e o processo também são técnicos; a
  definição ganha autoridade da fonte, não de quem a enuncia.
- Use o vocabulário do CPC/2015 e faça a nomenclatura da peça
  coincidir com o dispositivo invocado ("carência de ação",
  "condições da ação" → "ausência de interesse processual",
  "ilegitimidade", art. 485, VI).
- Delimite a lide pelos atos do autor e pelas regras de congruência
  ("a lide tem por objeto X" dito pelo réu → "a parte deduziu
  pretensão de X, à qual o julgamento ficará adstrito, arts. 141 e
  492; não se deduziu — nem seria lícito deduzir — pretensão de Y,
  art. 18"). A defesa "se articula em N proposições" — ela não se
  declara contida em limites.
- Enquadre a impossibilidade de cumprir ordem como questão de
  competência ("não dispõe de meios" → "o ato extrapola a competência
  legal do destinatário; competência administrativa é vinculada e
  improrrogável; o cumprimento importaria ato de autoridade
  incompetente, viciado e insuscetível de produzir o efeito
  pretendido"). "Não consigo" se discute; "se eu fizer, não vale" o
  juízo tem de enfrentar.
- Quando a norma prescreve procedimento para a situação dos autos
  (sobrestar, diligenciar, notificar), demonstre que a Administração
  o seguiu: o mesmo fato que, narrado como justificativa, soa a
  escusa ("não pude deferir") reaparece, ancorado na norma, como
  conduta devida ("a norma determina X, e foi X que se fez"). Escusa
  se desculpa; procedimento cumprido se constata.
- Enuncie a melhor leitura possível da tese contrária antes de
  derrubá-la ("poder-se-ia cogitar de leitura que...") e feche também
  essa porta. O ideal é o cerco: a peça mostra todas as leituras
  possíveis do pedido ou da ordem e demonstra que cada uma falha por
  razão própria — antes que a sentença encontre sozinha a que faltou.

## 5. Traga o precedente pelo que ele vincula, e deixe a matéria prequestionada

**Pratique:**
- Vinculante entra pelo tema e pela tese: identifique por número de
  tema ou repetitivo e transcreva a tese firmada, uma vez, no
  capítulo dono ("colacione-se o seguinte julgado" + ementa de página
  → "a tese do Tema N é: *'...'*"). Ementa inteira é para o anexo,
  não para o corpo.
- Persuasivo, um basta: três acórdãos onde um vinculante resolve é
  ruído que dilui. O segundo precedente só entra se cobre fato que o
  primeiro não cobre.
- Distinguishing explícito: quando a parte contrária invoca
  precedente, nomeie o fato que o caso não tem ("o precedente
  pressupõe X; aqui não há X"). Nunca ignore, nunca rebata apenas
  com precedente contrário — precedente contra precedente sem
  distinção é empate que o juiz desempata sozinho.
- Prequestionamento por dispositivo nomeado: ancore cada tese da
  peça, expressamente, no artigo de lei ou da Constituição que a
  sustenta ou que a decisão contrária violaria. É o pressuposto do
  fluxo recursal de Franklin (dois embargos de declaração
  sucessivos, invocando os Temas 1306/STJ e 339/STF, antes de
  REsp/RE): embargos cobram omissão sobre dispositivo nomeado na
  origem — tese órfã de artigo não se prequestiona, e isso se decide
  na contestação, não no recurso.

## 6. Dê a cada matéria o seu capítulo, e ao juízo os seus degraus

**Pratique:**
- Estruture a contestação em: síntese da defesa → fatos →
  preliminares → mérito → tutela de urgência (se houver) → prova →
  pedidos. O mérito responde à petição inicial; o capítulo da tutela
  responde à decisão — transcrição do dispositivo, decomposição em
  elementos, e um subitem por vício (competência, objeto, excesso,
  multa). Mérito não abre com "a r. decisão...".
- Escalone os pedidos em degraus independentes: alínea própria para a
  revogação da tutela; alínea autônoma para o excesso parcial ("ainda
  que mantida quanto ao restante"). O juízo deve conseguir conceder o
  menos sem se comprometer com o mais.
- Rotule a peça pela substância: argui preliminar e pede
  improcedência, é contestação — qualquer que seja o nome da minuta.
- Dirija cada pedido a quem é parte. Providência que dependa de
  terceiro entra como consequência do julgado ou como via a percorrer
  pela parte interessada, nunca como provimento requerido contra o
  terceiro.
- Traduza cada necessidade no instituto processual que a satisfaz sem
  carregar pressupostos: documento em poder de parte é exibição
  (arts. 396 e ss., art. 400), não "determinação de regularização" —
  regularizar pressupõe o mérito que se contesta e, quando a via
  administrativa já falhou, pedir de novo é requerer a repetição
  documentada de um fracasso. Formulada como exibição, a mesma
  providência não pressupõe nada, e a exibição malfeita fica
  registrada como descumprimento de ônus.
- Selecione preliminares pelo que elas sinalizam: cada uma deve
  fortalecer o conjunto. A que só existe para prevenir um flanco que
  ninguém atacou (revelia sem revelia arguida) chama atenção
  exatamente para o flanco que quer proteger.

## 7. Afirme direto e corte o que não trabalha

A frase assertiva carrega a autoridade da peça. Diga a tese;
demonstre-a; passe à próxima.

**Pratique:**
- Cada parágrafo faz um trabalho que nenhum outro faz. O que repete
  o anterior com outras palavras sai inteiro.
- Corte deletando, não resumindo — resumir preserva a redundância em
  miniatura.
- Doutrina que só confirma o óbvio sai; precedente que não acrescenta
  fato nem fundamento sai junto.

Teste de todo trecho: se eu apagar, a demonstração enfraquece? Se
não, apague.

**Em vez de:** anunciar o que se vai fazer ("importa fixar", "cumpre
consignar", "por lealdade processual antecipa-se") → a tese direto;
qualificar a própria demonstração ("dispensa esforço interpretativo",
"de simples cotejo") → a demonstração, que se qualifica sozinha;
repetir ressalva já feita → o corte.

## 8. Formate para o leitor do PDF

**Pratique:**
- Citação entre aspas sempre em itálico — bloco recuado
  (`> *"..."*`) para transcrição longa (dispositivo, ementa, norma,
  requerimento); inline (`*"..."*`) para a citação curta que é objeto
  imediato da frase.
- Aspas sem itálico para a palavra mencionada como palavra
  ("averbação" enquanto termo).
- Títulos de `##` para baixo; `###` nunca aparece em parágrafo
  corrido — se a linha não é título, não leva marcação.
- Cada texto transcrito uma vez, no capítulo dono do tema; os demais
  recapitulam e remetem ao item numerado.

**Em vez de:** `#`, `---`, `###` em parágrafo corrido, citação em
romano.

## Varredura final (antes de entregar qualquer peça)

Nenhum passo abaixo é busca por palavra. O vício não mora na string:
a peça que passa no grep falha em todos eles, e a que não usa nenhuma
das expressões típicas comete o mesmo erro por outras. Cada passo é
uma leitura com uma pergunta na mão. As expressões entre parênteses
são pistas frequentes, não a definição — achá-las não condena, não
achá-las não absolve.

1. Leia só os títulos em sequência: o sumário conta a defesa inteira?
   Se não, reescreva títulos.
2. Abra três seções ao acaso e leia cada uma como primeiro contato:
   ela se sustenta? Atos identificados, pedido descrito antes de
   refutado?
3. Cada parágrafo abre pela tese ou pelo anúncio dela? (típicas:
   "importa fixar", "cumpre consignar", "de simples cotejo") Corte o
   anúncio; a tese fica.
4. Alguma passagem manda o leitor procurar sozinho o que já se disse?
   (típicas: "acima", "anterior", "o referido") Item numerado, mais
   uma linha recapitulando.
5. A peça afirma, em algum ponto, que um fato ocorreu ou que não se
   discute? Vale para a declaração expressa e para a tácita —
   descrever como dado o que só existe como registro. Silêncio, ou
   descrição do que o documento registra.
6. Cada preliminar e cada tese chega nomeada pelo CPC/2015 e pelo
   dispositivo? Definição que se anuncia técnica sem citar fonte,
   impossibilidade posta como falta de meios em vez de incompetência
   → item 4.
7. Cada tese que sustenta um pedido tem artigo nomeado no corpo?
   Tese órfã de artigo, nomear antes de protocolar.
8. Toda afirmação da peça sobre os autos tem pergunta correspondente no
   sidecar de verificação? Afirmação sem pergunta é afirmação que
   ninguém vai conferir.
9. Citações em itálico; `###` só em título. Este é o único passo
   mecânico da lista.
