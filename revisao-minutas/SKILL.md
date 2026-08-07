---
name: revisao-minutas
description: >-
  Triagem de risco de minutas JUDICIAIS elaboradas pela assessoria de Franklin
  (contestações, recursos, embargos, contrarrazões, agravos e manifestações),
  para decidir se estão aptas a peticionamento. Use quando Franklin colar ou
  anexar uma minuta que ele não redigiu e pedir avaliação, revisão, conferência
  ou segurança para assinatura/protocolo. O produto é um veredito 🟢/🟡/🔴 com
  riscos concretos e, quando necessário, edits cirúrgicos; não é uma reescrita
  estilística. Não use para redação greenfield da peça, pareceres ou documentos
  administrativos.
---

# Revisão de minutas judiciais

A função desta skill é decidir **se a peça pode ser protocolada**. Não trate a
triagem como coautoria.

## Invariantes

1. **Texto original intocado por padrão.** Só proponha mudança para eliminar
   risco concreto. Preferência estilística não é fundamento de edit.
2. **Edits cirúrgicos.** Quando necessários, entregue localização + trecho
   original + substituto + motivo. Não reescreva uma seção inteira para corrigir
   uma frase.
3. **Fatos são hipóteses até confirmação.** Data, ID, teor de decisão,
   alegação, valor, rubrica e precedente precisam de ancoragem adequada.
4. **Peça limpa.** Pendência de conferência fica no relatório/checklist, nunca
   dentro do texto que pode ser protocolado.
5. **Pare cedo diante de risco fatal.** Não vale polir uma peça que ainda é
   inapta.

## Fluxo obrigatório

1. Identificar tipo de peça, processo, fase, parte/ente representado, decisão ou
   ato respondido e situação do prazo.
2. Rodar o checklist fatal abaixo.
3. Verificar omissões, exposição institucional, coerência lógica, ancoragem
   fática, sanções e formais relevantes. Leia
   [`references/taxonomia-de-risco.md`](references/taxonomia-de-risco.md) quando
   precisar do detalhamento por tipo de peça ou das heurísticas de citações.
4. Se fatos materiais não estiverem suficientemente comprovados, aplicar
   [`references/verificacao-adversarial.md`](references/verificacao-adversarial.md).
5. Emitir o veredito.
6. Se 🟡, propor somente os edits necessários.
7. Se for produzir/persistir o relatório estruturado, seguir
   [`references/relatorio-okf.md`](references/relatorio-okf.md).

## Checklist fatal — sempre carregar

Qualquer falha relevante aqui tende a tornar a peça 🔴 até correção ou decisão
expressa do USER.

- **Tempestividade**: identificar prazo, termo inicial e regime de contagem. A
  fonte autoritativa é o expediente/intimação processual adequado; não presumir
  a partir do PDF exportado dos autos.
- **Cabimento**: confirmar que a via escolhida ataca corretamente o ato e que os
  pressupostos específicos estão presentes.
- **Legitimidade e representação**: conferir ente, polo e capacidade de falar em
  nome da parte correta.
- **Endereçamento, competência e rito**: conferir órgão e requisito formal cuja
  ausência tenha consequência de inadmissibilidade ou perda útil.
- **Preclusão**: verificar se a tese central ainda pode ser arguida naquele
  momento processual.
- **Pedido**: conferir compatibilidade entre pedido, fundamentação, rito e efeito
  realmente buscado.

Não declare tempestividade confirmada sem a fonte processual que fixa o termo
inicial quando essa informação não estiver disponível no contexto autorizado.

## Veredito

Coloque no topo, sem hedging desnecessário:

- 🟢 **Apta** — pode protocolar como está. Imperfeições toleráveis podem ser
  registradas sem edit.
- 🟡 **Apta com ajustes cirúrgicos** — existe uma lista curta e fechada de
  correções. Aplicadas e satisfeitas as conferências materiais, a peça fica
  apta.
- 🔴 **Inapta** — há risco fatal, exposição grave ou volume de correções que
  exige devolver/reconstruir antes do protocolo.

Se uma conclusão depender de fato material ainda não confirmado, use **veredito
condicionado**; não dê 🟢 incondicional.

Como heurística, um 🟡 com muitos edits deixa de ser triagem cirúrgica. Se a
correção virar reescrita por gotejamento, classifique como 🔴 e diga o que
precisa ser refeito.

## O que aprofundar sob demanda

### Taxonomia e estratégia

Leia [`references/taxonomia-de-risco.md`](references/taxonomia-de-risco.md) para:

- omissões específicas de contestação, recursos, contrarrazões e embargos;
- exposição institucional;
- coerência lógica;
- sanções;
- formais com consequência;
- economia e verificação de citações;
- comparação com posições/estratégias já fornecidas no contexto autorizado.

### Verificação dos autos

Leia [`references/verificacao-adversarial.md`](references/verificacao-adversarial.md)
quando precisar testar afirmações contra NotebookLM, DataJud, Juris, fontes
oficiais ou sistemas externos. A regra é adversarial: formule a pergunta que
poderia **desmentir** a minuta.

### Relatório estruturado

Leia [`references/relatorio-okf.md`](references/relatorio-okf.md) somente na fase
de entrega/persistência do relatório. O schema de armazenamento não precisa
ocupar contexto durante a análise jurídica.

## Modo volume

Quando o USER sinalizar pressa ou enviar minutas em lote:

- priorize checklist fatal + omissões + exposição institucional;
- dispense consulta adicional se os fatos relevantes já estiverem comprovados
  no contexto;
- mantenha ressalva explícita para conferência material pendente;
- entregue um veredito por minuta;
- limite a conversa aos riscos que mudam a decisão de protocolar.

O modo volume reduz profundidade operacional, não relaxa risco fatal.

## Definition of Done

A triagem só termina quando:

- o tipo de peça e o ato respondido estão claros;
- o checklist fatal foi percorrido;
- omissões relevantes foram consideradas para aquele tipo de peça;
- afirmações fáticas de consequência estão confirmadas ou marcadas como
  pendentes com impacto explícito no veredito;
- divergências institucionais/estratégicas materialmente relevantes foram
  destacadas;
- o veredito é 🟢, 🟡 ou 🔴 e sua razão dominante cabe em uma frase;
- todo edit proposto elimina um risco identificável;
- providências externas ao texto foram para checklist, não para dentro da peça;
- quando solicitado, o relatório OKF segue o contrato da referência própria.

O objetivo não é produzir a melhor peça que você conseguiria escrever. É saber,
com o menor retrabalho seguro, **se esta minuta pode ir**.