# Folha em branco aplicada a estratégia jurídica

A técnica transfere para qualquer domínio em que exista um **artefato acumulado** cuja
forma atual passou a ser tratada como premissa. Direito é o caso mais interessante — e o
mais perigoso — porque parte das restrições brownfield ali **não é revogável nem mesmo
quando está errada**.

## A diferença que mata: preclusivo vs. inercial

Em software, quase toda decisão passada é, em princípio, revogável: dá para refatorar,
depreciar, reescrever. No processo, não. As restrições brownfield jurídicas se dividem em
duas espécies, e confundi-las é o erro caro nos dois sentidos.

**Preclusivas / irreversíveis** — não cedem a mérito nenhum:

- preclusão consumativa, lógica e temporal; prazo escoado;
- coisa julgada e efeitos de decisão não impugnada;
- confissão, revelia, fato incontroverso por ausência de impugnação específica;
- tese já sustentada nos autos (a mudança de versão tem custo de credibilidade, e às vezes
  é vedada — *venire contra factum proprium* processual);
- ato administrativo já publicado com efeitos produzidos;
- competência e legitimidade — não se redesenha quem pode agir.

**Inerciais** — só continuam porque foi assim que se fez:

- a tese herdada do modelo do setor, replicada há anos sem revisão;
- o pedido copiado de contestação anterior que não corresponde ao caso;
- a estrutura da peça (o relatório de 12 páginas que ninguém lê);
- o capítulo preliminar levantado por hábito, que só dilui;
- a linha argumentativa desenhada para uma jurisprudência que já virou.

**A folha em branco só opera sobre as inerciais.** Tratar preclusão como inércia perde o
caso. Tratar inércia como preclusão garante que nada melhore nunca. O passo 4 da skill —
classificar cada diferença — é exatamente onde essa separação é feita, e aqui ela ganha um
balde adicional obrigatório:

| Balde extra (jurídico) | Significado | Ação |
| --- | --- | --- |
| O existente é preclusivo | Não é escolha, é consequência processual consumada | Manter, e registrar *por quê* — para o próximo não achar que foi preguiça |

## O contrafactual, na versão jurídica

> Suponha que os autos sejam exatamente estes, mas que **esta peça / esta tese / este ato
> ainda não tivesse sido escrito**. O que escreveríamos?

O que se suspende é a **forma atual da solução** — o modelo, a minuta anterior, a tese
padrão do setor. O que **não** se suspende é o conhecimento: os autos, a prova, a
jurisprudência vinculante, o que já foi alegado e o que já precluiu.

Regra prática: rode o passo 3 (desenhar o ideal) **antes** de abrir o modelo do setor ou a
minuta anterior. Depois de lido, o modelo vira âncora e o exercício degenera em edição. Se
já leu, delegue o rascunho ideal a quem não leu.

## Onde isso rende no dia a dia

**Teoria do caso.** Em vez de "quais teses da contestação padrão se aplicam?", pergunte:
*qual é a narrativa mínima que, se aceita, resolve o caso a favor do órgão?* Depois
confronte com o que é sustentável nos autos. Teses que sobram sem função na narrativa são
ruído — e ruído tem custo: dilui a tese boa e entrega flanco.

**Peça repetitiva / modelo do setor.** É o alvo mais rentável, porque o modelo é
literalmente um artefato acumulado que ninguém redesenhou. Refaça o modelo do zero contra a
classe de casos que ele realmente atende hoje, e classifique cada divergência. Costuma
aparecer muita coisa no balde "decisão superada" — preliminar que a jurisprudência já
pacificou contra, pedido subsidiário que virou letra morta.

**Ato normativo, edital, regulamento.** Comece pela finalidade em uma frase: *"esta norma
existe para que X possa Y sem Z."* Boa parte do texto acumulado não sobrevive a essa
pergunta — e o que não sobrevive geralmente é o que gera litígio.

**Processo institucional.** Quem propõe, quem analisa, quem aprova, quem assina. Aqui a
reengenharia clássica (Hammer & Champy) é literalmente o método: *estamos tornando mais
eficiente um fluxo que não deveria existir?* A restrição inegociável é a competência — o
desenho ideal não pode realocar autoridade que a lei fixou.

**Portfólio de teses do órgão.** Do zero: quais teses defenderíamos hoje, dado o acervo e a
jurisprudência atual? A diferença contra a lista praticada revela teses mantidas por inércia
e teses perdidas por esquecimento.

## Passo 6, versão jurídica: contra quais tarefas testar

Um desenho ideal que não sobrevive a estas perguntas não está pronto:

- A tese sobrevive à **contra-tese mais forte**, não à mais fácil de refutar?
- Cada pedido é alcançável a partir de uma causa de pedir efetivamente deduzida?
- Sobrevive ao **juízo que não leu os autos** — a tese se sustenta na leitura apressada?
- O que precluiu está tratado como preclusão, e não silenciado?
- A peça distingue o que é **análise** do que é **decisão institucional** já tomada?
- Alguma omissão deixa um risco material invisível para quem assina?
- Alguma regra da peça impede iniciativa legítima de quem vai executá-la?

## Não-negociáveis

O rascunho ideal é o momento de maior risco de invenção, porque nada nele veio de fonte
verificada ainda. Antes de reconciliar:

- **nenhum precedente, ementa, número de tema ou dispositivo sem verificação na fonte** —
  a plausibilidade de uma citação é exatamente o que a torna perigosa;
- **nenhum ato institucional fabricado** — não se descreve como existente uma decisão,
  aprovação ou orientação que ninguém tomou;
- **análise não é aprovação** — o desenho ideal é proposta até que a autoridade competente
  decida;
- **o que precluiu não vira ficção** — a folha em branco não desfaz os autos.

## Relação com outras skills

Esta técnica ataca **o modelo, a tese ou o fluxo** — a pergunta é "isto deveria ser assim?".
Para triagem de risco de uma minuta concreta que já foi redigida ("dá para protocolar?"), o
instrumento é a skill `revisao-minutas`. Para verificar a existência e o teor de precedentes
antes de citar, `juris-tjro`. Para ancorar afirmações de fato nos autos, `notebooklm-processos`.

## Outros domínios, mesma estrutura

Vale onde quer que haja artefato acumulado + restrições reais que ninguém quer perder:
política pública e desenho de programa; contrato-modelo; organograma e alocação de
competências; grade curricular; arquitetura de um argumento acadêmico; onboarding e
documentação interna. A pergunta invariante é sempre a mesma: **qual restrição é real, e
qual é só a forma que a solução por acaso tomou?**
