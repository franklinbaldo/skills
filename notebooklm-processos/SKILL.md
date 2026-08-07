---
name: notebooklm-processos
description: >-
  Quando o trabalho estiver ancorado em um processo específico e os documentos
  forem volumosos ou estiverem apenas parcialmente no contexto, sugira
  proativamente usar o NotebookLM para perguntas grounded, com o usuário como
  intermediário. Trabalhe em blocos iterativos, um por vez, esperando as
  respostas antes do próximo. Não use para perguntas jurídicas genéricas nem
  quando os documentos relevantes já estiverem integralmente disponíveis e
  forem curtos.
---

# NotebookLM para processos

Use o NotebookLM como uma camada de **extração documental grounded**. Ele não substitui análise jurídica, pesquisa externa nem acesso corrente ao processo.

## Contrato sempre ativo

1. **Sugira proativamente quando fizer sentido.** Não espere o usuário mencionar NotebookLM se o trabalho depende de autos extensos ou parcialmente disponíveis.
2. **O usuário é o intermediário.** Esta skill formula os blocos; o usuário roda no NotebookLM e traz as respostas.
3. **Um bloco por vez.** Espere as respostas antes de formular a rodada seguinte. A investigação deve poder mudar de direção.
4. **Perguntas autossuficientes.** O NotebookLM não conhece a conversa. Use nomes concretos de órgão, parte, documento e processo; evite dêixis como "este caso", "nós" ou "minha unidade".
5. **Grounded-only.** Pergunte apenas o que pode ser respondido pelos documentos carregados. Lei, jurisprudência, doutrina, fatos supervenientes e outras fontes externas pertencem a outro fluxo.
6. **Exija âncoras.** Peça trecho literal, documento de origem e localização verificável (ID/página quando disponível).
7. **Inclua falsificação.** Quando já existir uma tese ou enquadramento, ao menos uma pergunta do bloco deve tentar derrubá-lo.
8. **"As fontes não informam" não significa inexistência.** Significa apenas que o material carregado não cobre o ponto.

## Antes do mérito: confirme qual é a tarefa

Em processos concretos, não presuma que o encargo é redigir a peça principal. O ato de encaminhamento interno pode pedir revisão, parecer pontual, manifestação sobre recorte específico, ciência ou redistribuição.

Quando o papel do órgão/unidade não estiver claro, o primeiro bloco deve esclarecer:

- qual ato encaminhou o processo;
- o que ele pede concretamente;
- se há prazo e a quem ele foi atribuído;
- se outra unidade ou procurador já conduz o feito.

Defina a tarefa antes de executar a tarefa errada muito bem.

## Quando oferecer

Ofereça NotebookLM quando as duas condições coexistirem:

1. há um processo/caso/documento específico; e
2. a resposta depende de conteúdo documental que não está integralmente acessível no contexto atual.

Casos típicos: autos extensos, múltiplos ofícios/manifestações, laudos, acórdãos longos, processo administrativo volumoso ou redação de peça que depende de fatos dispersos.

## Quando não oferecer

Não proponha quando:

- a pergunta é jurídica genérica e não depende de processo concreto;
- os documentos relevantes já estão integralmente disponíveis e são curtos;
- a tarefa não é documental/processual;
- o usuário já rejeitou o uso do NotebookLM naquele caso.

## Ciclo de trabalho

1. Identifique o que precisa ser descoberto antes de continuar a análise.
2. Monte **um bloco enxuto e variado** de perguntas, normalmente até cerca de dez.
3. Para o formato copiável do bloco, siga [`references/artifact-protocol.md`](references/artifact-protocol.md).
4. O usuário roda o bloco e traz as respostas.
5. Integre as respostas preservando as referências de origem.
6. Reavalie o enquadramento e só então decida se uma nova rodada é necessária.

Não despeje todas as perguntas concebíveis de uma vez. O resultado da rodada anterior deve influenciar a seguinte.

## Desenho mínimo das perguntas

Cada pergunta deve:

- mirar um fato, documento, passagem, data, valor, ato ou relação verificável;
- pedir a fonte/localização quando isso for útil à peça;
- ser compreensível sem memória da conversa;
- evitar pedir opinião jurídica ao NotebookLM;
- contribuir para uma frente distinta ou para testar uma hipótese relevante.

Quando precisar de técnicas mais detalhadas — inventário inicial, cronologia, perguntas falsificadoras, calibração por tipo de fato — leia [`references/question-design.md`](references/question-design.md).

## Fronteira do NotebookLM

O NotebookLM só sabe o que está nas fontes carregadas. Portanto:

- não pergunte como STF/STJ/TJRO vêm decidindo se isso não está nos autos;
- não peça interpretação de norma não juntada;
- não trate silêncio do notebook como prova de inexistência;
- não suponha que o PDF exportado contém atos praticados depois da exportação.

Quando a questão for externa ou temporalmente posterior ao material carregado, siga [`references/external-routing.md`](references/external-routing.md) e use a fonte adequada (DataJud, Juris, web oficial, PJe/SEI via usuário etc.).

## Integração das respostas

Trate a resposta como **conteúdo atribuído às fontes**, não como conhecimento próprio da skill.

Ao integrar:

- preserve documento, trecho e ID/página quando fornecidos;
- diferencie explicitamente o que foi encontrado do que permaneceu sem cobertura;
- se houver divergência documental, mantenha a divergência visível;
- não transforme "as fontes não informam" em "o fato não existe";
- se o retorno enfraquecer a tese inicial, mude a tese em vez de procurar apenas confirmação adicional.

## Modo adversarial

Quando já houver uma tese, inclua uma pergunta que procure o fato, documento, ressalva ou fundamento autônomo que mais poderia contrariá-la.

Quando o objeto for uma minuta pronta da assessoria, use a skill `revisao-minutas`: ela herda este método de extração, mas transforma a própria minuta no alvo do teste adversarial.

## Definition of Done

O uso desta skill termina quando:

- a tarefa concreta do órgão/unidade está suficientemente clara;
- cada bloco enviado é grounded, autossuficiente e copiável;
- as respostas foram integradas com suas âncoras documentais;
- lacunas do material foram distinguidas de inexistência do fato;
- questões externas foram roteadas para fontes externas em vez de forçadas para o NotebookLM;
- ao menos uma hipótese relevante foi testada de forma adversarial quando havia tese em construção;
- a próxima decisão do trabalho pode ser tomada com base no que as fontes efetivamente sustentam.