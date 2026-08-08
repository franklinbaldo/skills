---
name: notebooklm-processos
description: >-
  Use para transformar autos ou processos administrativos volumosos em um corpus
  interrogável e produzir evidência documental ancorada para a próxima decisão do
  trabalho. Dispare quando um caso concreto depender de documentos que não estão
  integralmente no contexto, especialmente para cronologia, fatos controvertidos,
  reconstrução de atos, confronto entre versões e preparação de revisão/minuta.
  O usuário continua como intermediário do NotebookLM. Não use para pesquisa
  jurídica externa, jurisprudência fora das fontes ou perguntas genéricas.
---

# NotebookLM para processos

NotebookLM é uma **camada de leitura grounded do corpus**, não um oráculo jurídico
e não um mero gerador de perguntas.

O objetivo é converter:

```text
processo bruto
→ corpus minimamente conhecido
→ perguntas orientadas por decisão
→ evidência ancorada
→ mapa de lacunas/contradições
→ próxima decisão jurídica ou institucional
```

## Invariantes

1. **Comece pela decisão que precisa ser tomada.** Não inventarie centenas de
   documentos sem saber qual pergunta o corpus precisa ajudar a resolver.
2. **O usuário é o intermediário.** Formule blocos copiáveis; o usuário executa
   no NotebookLM e retorna o resultado.
3. **Um bloco por vez.** A resposta de uma rodada pode mudar completamente a
   seguinte.
4. **Grounded-only.** O NotebookLM só responde pelo material carregado.
5. **Evidência precisa de âncora.** Peça documento, trecho e ID/página quando
   disponível.
6. **Silêncio não é inexistência.** “As fontes não informam” significa lacuna do
   corpus consultado.
7. **Contradição não deve ser conciliada automaticamente.** Preserve versões
   incompatíveis até saber qual documento, data ou autoridade prevalece.
8. **Toda tese relevante merece tentativa de falsificação.** Pergunte o que
   poderia derrubá-la.
9. **Não transforme extração em conclusão jurídica.** O corpus fornece fatos,
   atos e textos; a análise jurídica vem depois.

## 1. Defina a próxima decisão

Antes de formular perguntas, identifique qual decisão do trabalho depende do
processo. Exemplos:

- qual foi exatamente a pretensão administrativa?
- qual ato está sendo impugnado?
- o que a sentença/acórdão efetivamente decidiu?
- houve pedido ou fundamento que ficou sem enfrentamento?
- qual período, rubrica ou pessoa está em disputa?
- qual fato precisa ser confirmado antes de assinar uma minuta?
- existe documento posterior que muda o enquadramento?

Se nem isso estiver claro, o primeiro bloco serve para descobrir **qual é a
tarefa**, não o mérito.

## 2. Faça uma leitura estrutural mínima do corpus

Quando o processo estiver pouco conhecido, a primeira rodada deve mapear apenas
o suficiente para orientar a investigação. Pergunte por:

- ato inicial/objeto;
- principais decisões;
- manifestações das partes/unidades;
- documentos probatórios centrais;
- cronologia dos eventos materiais;
- ato mais recente relevante;
- eventuais lacunas aparentes.

Não peça um “resumo completo dos autos”. Resumos globais tendem a apagar
contradições e relações de proveniência.

## 3. Interrogue por frentes, não por documentos

Agrupe perguntas por **questão decisória**. Uma rodada boa mistura:

- recuperação direta de fato/ato;
- cronologia;
- comparação entre dois documentos;
- busca de exceção/ressalva;
- pergunta falsificadora;
- pergunta sobre ausência de cobertura, quando material.

Normalmente use até cerca de dez perguntas, mas prefira seis perguntas boas a
dez genéricas.

Para desenho detalhado, leia
[`references/question-design.md`](references/question-design.md).
Para o formato copiável, use
[`references/artifact-protocol.md`](references/artifact-protocol.md).

## 4. Exija uma unidade mínima de evidência

Quando uma resposta puder sustentar decisão, peça:

```text
proposição encontrada
+ trecho literal suficiente
+ documento de origem
+ ID/página/localização, quando disponível
+ data do documento, quando temporalidade importar
```

Ao integrar, mantenha essa proveniência próxima da proposição. Evite produzir um
novo resumo sem origem rastreável.

## 5. Construa três mapas mentais

Depois de cada rodada, classifique o retorno em:

### Confirmado

O corpus contém suporte direto suficiente para a proposição.

### Contraditório/ambíguo

Há versões incompatíveis, mudança temporal, documento posterior, linguagem
ambígua ou fontes que não se encaixam.

### Sem cobertura

O material consultado não responde. Isso gera uma decisão de roteamento:
procurar outro documento, atualizar o corpus ou sair do NotebookLM.

Não converta “sem cobertura” em fato negativo.

## 6. Use cronologia como ferramenta causal, não decoração

Uma linha do tempo só é útil quando ajuda a responder algo. Priorize eventos que
mudam:

- direito aplicável;
- posição das partes/unidades;
- objeto litigioso;
- valor/período;
- competência;
- estado processual;
- possibilidade de alegar ou cumprir algo.

Se a cronologia não muda a próxima decisão, não gaste contexto produzindo-a.

## 7. Faça confronto adversarial

Quando já existir uma tese, minuta ou leitura preferida, formule pelo menos uma
pergunta como:

- qual documento mais contradiz esta conclusão?
- existe ressalva, exceção ou período que a torne parcialmente falsa?
- alguma decisão posterior alterou o que o documento anterior dizia?
- o pedido real foi mais estreito/amplo do que a minuta presume?
- há evidência de que o fato ocorreu em data diferente?

Quando o alvo for uma minuta pronta, combine com
[`revisao-minutas`](../revisao-minutas/SKILL.md): a minuta fornece as proposições
que precisam ser testadas contra o corpus.

## 8. Saiba quando sair do NotebookLM

Saia quando a pergunta for sobre algo que não pertence às fontes carregadas.

- **metadados/andamento processual:** [`datajud`](../datajud/SKILL.md);
- **jurisprudência e inteiro teor do TJRO:**
  [`juris-tjro`](../juris-tjro/SKILL.md), quando aplicável;
- **lei/jurisprudência atual:** fonte oficial ou pesquisa externa;
- **ato superveniente não carregado:** obtenha/adicione o documento primeiro.

Leia [`references/external-routing.md`](references/external-routing.md) quando a
fronteira não estiver clara.

## 9. Transforme evidência em próxima ação

Ao fim de uma rodada, não entregue só “o que o NotebookLM disse”. Diga:

- o que ficou comprovado;
- o que mudou no enquadramento;
- quais contradições permanecem;
- o que está sem cobertura;
- qual é a **próxima decisão** que agora pode ser tomada;
- se outra rodada é necessária e por quê.

A investigação termina quando informação adicional não muda materialmente a
próxima decisão.

## Perguntas ruins

Evite:

- “resuma o processo inteiro”;
- “quem tem razão?”;
- “qual a melhor tese jurídica?”;
- “o STF entende que...?” quando isso não está nas fontes;
- dezenas de perguntas independentes numa única rodada;
- perguntas sem nome do processo, parte, documento ou contexto suficiente;
- perguntas que pedem ao NotebookLM para preencher o que os autos não dizem.

## Definition of Done

O uso termina quando:

- a decisão que motivou a investigação está explícita;
- o corpus foi mapeado apenas na profundidade necessária;
- cada proposição material usada está acompanhada de proveniência adequada;
- contradições foram preservadas, não suavizadas;
- lacuna de corpus foi distinguida de inexistência de fato;
- pelo menos uma hipótese relevante foi testada adversarialmente;
- questões externas foram roteadas para a fonte correta;
- está claro o que as fontes permitem decidir agora e o que ainda falta.

O produto final não é um resumo dos autos. É **evidência documental suficiente
para tomar a próxima decisão sem fingir que o corpus disse mais do que disse**.
