---
name: software-review
description: >-
  Revisa PRs, RFCs e mudanças arquiteturais de software com foco em defeitos
  reproduzíveis, invariantes quebrados e severidade calibrada ao tipo real de
  aplicação. Use quando Franklin pedir review, re-review, triagem de findings,
  avaliação de RFC/arquitetura, investigação de checks falhando ou alternativas
  criativas para um problema técnico. Não use para implementação greenfield sem
  objeto de revisão nem para lint cosmético sem consequência.
---

# Software review

A função desta skill é responder:

> **O que nesta mudança pode fazer o sistema real se comportar de forma errada,
> ficar impossível de evoluir com segurança ou prometer um contrato que não
> consegue cumprir?**

Review não é caça a diferenças nem competição por quantidade de comentários.
Um bom review encontra poucos defeitos materiais, demonstra por que importam e
sabe declarar quando não há findings restantes.

## Invariantes

1. **Entenda o produto antes da severidade.** Um problema só é P1/P2 em relação
   ao tipo de aplicação que está sendo construído.
2. **Reproduza antes de acusar.** Sempre que for razoável, prove o comportamento
   com teste, código, comando, query ou contraexemplo.
3. **Ataque contratos, não estilo.** Prefira invariantes quebrados, dados
   incorretos, API enganosa, estados impossíveis, perda de informação e falsa
   segurança a preferências de implementação.
4. **Diferencie defeito presente de risco hipotético.** “Poderia um dia” não tem
   a mesma severidade de “esta entrada válida já quebra”.
5. **Leia a arquitetura existente antes de duplicá-la.** Procure primeiro se a
   biblioteca, banco, framework ou domínio já oferece a primitiva necessária.
6. **Correção mínima e correção estrutural são opções diferentes.** Mostre ambas
   quando isso ajudar a decisão.
7. **Re-review reabre somente o que ainda está quebrado.** Não repita findings
   já resolvidos nem mova a trave depois da correção.
8. **Verde pode ser conclusão.** Se não houver defeito material restante, diga
   isso claramente.

## 1. Reconstrua o contrato da mudança

Antes do diff, responda:

- qual problema a PR/RFC diz resolver?
- para quem?
- qual comportamento público muda?
- quais dados entram e saem?
- quais invariantes não podem quebrar?
- que restrições do produto importam de verdade (read-only, offline, atomicidade,
  compatibilidade, performance, segurança, determinismo etc.)?
- quais decisões já estão explicitamente fora de escopo?

Não imponha requisito que o produto não possui.

## 2. Descubra o caminho crítico

Localize as poucas superfícies onde um erro seria material:

- parsing/normalização;
- persistência/migração;
- boundaries entre tipos;
- autorização/escrita;
- serialização/deserialização;
- compatibilidade de schema;
- concorrência/atomicidade;
- fallback/error handling;
- geração de código;
- round-trip;
- CLI/API contract;
- projeções/derivados;
- gates que alegam provar propriedades.

Em RFC, faça o equivalente conceitual: encontre onde uma decisão declarada não
é sustentada pelo mecanismo proposto.

## 3. Reproduza

Para cada suspeita forte, tente produzir uma evidência executável ou um
contraexemplo mínimo.

Boas evidências:

```text
input válido
→ caminho de código
→ estado produzido
→ invariante esperado
→ divergência observada
```

ou:

```text
RFC promete X
→ mecanismo M é o único gate para X
→ M não observa o caso Y
→ Y passa apesar de violar X
```

Se não der para reproduzir por limitação de ambiente, diga o que foi verificado e
qual passo permanece inferido.

## 4. Calibre a severidade pelo produto real

### P1

Defeito que bloqueia a direção proposta ou torna falsa uma garantia central:

- corrupção/perda de dados relevante;
- comportamento público materialmente incorreto em entrada válida;
- gate de segurança/correção que pode passar um estado que deveria impedir;
- arquitetura que não consegue cumprir um requisito essencial declarado;
- mudança incompatível com o formato/fluxo que o próprio produto depende.

### P2

Defeito real e relevante, mas contornável ou menos central:

- comportamento incorreto em caso suportado de menor frequência;
- diagnóstico enganoso que atrapalha operação;
- incompatibilidade parcial;
- cobertura/gate incompleto sem quebrar a promessa principal.

### Observação

Melhoria, simplificação, dívida ou caso futuro sem defeito demonstrado.

Antes de marcar P1, pergunte:

> **Se isto ficar como está, o aplicativo que estamos de fato construindo fica
> incorreto ou apenas menos geral/elegante?**

## 5. Procure falsos verdes

Dê atenção especial a checks que parecem validar mais do que validam:

- teste que não percorre a entrada relevante;
- `tee`/pipeline escondendo exit code;
- validação depois de um filtro que remove o caso defeituoso;
- schema check que compara só nomes/tipos mas não semântica necessária;
- parser que ignora extensão/arquivo que o gate chama de “corpus completo”;
- fallback que transforma erro em sucesso silencioso;
- derived artifact que não é regenerado no CI;
- query/teste que mede um proxy diferente da promessa.

Um gate enganoso costuma ser mais grave que a ausência explícita de gate.

## 6. Explore primitivas existentes antes de inventar infraestrutura

Quando encontrar um problema, procure soluções na seguinte ordem:

1. primitiva nativa da biblioteca/runtime/banco;
2. composição de primitivas já usadas no repo;
3. extensão pequena do IR/contrato existente;
4. helper local determinístico;
5. nova abstração/framework somente se as anteriores não bastarem.

Exemplos de raciocínio desejado:

- usar planner/catalog do banco em vez de parser SQL paralelo;
- usar tipos exatos do engine em vez de enum próprio simplificado;
- usar projection/IR existente em vez de JSON paralelo;
- usar graph/query relacional em vez de regras duplicadas em Python.

## 7. Dê solução proporcional

Para finding material, quando útil apresente:

### Correção mínima

A menor mudança que restaura o contrato nesta PR.

### Correção estrutural

Uma solução que remove a classe de bug aproveitando a arquitetura existente.

### Fora da caixa

Somente quando trouxer simplificação real: inverter o fluxo, delegar a uma
primitiva mais forte, transformar validação em propriedade derivada, remover
configuração em vez de adicionar outra camada etc.

Não use criatividade para aumentar superfície de manutenção.

## 8. RFC review

Uma RFC precisa fechar a cadeia:

```text
objetivo
→ contrato
→ mecanismo
→ gate observável
→ migração/compatibilidade
→ estado de falha
```

Procure especialmente:

- objetivo que não tem gate correspondente;
- decisão que depende de comportamento não oferecido pela ferramenta atual;
- read/write boundary ambígua;
- migração sem rollback/compatibilidade suficiente;
- formato fonte e derivado misturados;
- campo opcional que na prática vira obrigatório;
- requisito universal baseado num piloto estreito;
- responsabilidade específica do domínio empurrada para infraestrutura genérica.

RFC pode ser rejeitada como direção mesmo quando a ideia central é boa. Nesse
caso, diga qual lacuna precisa ser fechada para a direção se tornar segura.

## 9. Re-review

Ao revisar correções:

1. liste os findings anteriores;
2. verifique cada um contra o novo head;
3. marque resolvido, parcialmente resolvido ou restante;
4. procure regressões introduzidas pela correção;
5. não reabra decisão encerrada sem evidência nova;
6. rode os gates relevantes novamente;
7. se tudo estiver resolvido, conclua sem inventar nova rodada de nitpicks.

Quando a correção muda a arquitetura, reavalie o contrato, não apenas o trecho
que recebeu patch.

## 10. Formato de entrega

Priorize findings. Para cada um:

```text
[P1/P2] título curto
localização
comportamento/contrato esperado
comportamento observado ou contraexemplo
consequência para este produto
correção recomendada
```

Depois dos findings, acrescente somente contexto útil:

- gates executados;
- limitações da reprodução;
- observações não bloqueantes realmente valiosas.

Se não houver findings:

> **Nenhum achado material restante nesta rodada.**

E diga quais propriedades relevantes foram verificadas. Não substitua ausência
de findings por elogio genérico.

## 11. Quando preparar mudança

Se o usuário autorizar execução:

- preserve escopo da PR;
- escreva/ajuste testes que reproduzem o finding antes ou junto da correção;
- prefira correção estrutural pequena a workaround opaco;
- rode gates locais/CI relevantes;
- abra PR separada quando a correção for follow-up e não pertencer ao head
  revisado;
- não faça merge sem autorização quando essa for a convenção do trabalho.

## Definition of Done

O review termina quando:

- o contrato e o tipo de aplicativo estão claros;
- cada finding material tem evidência ou cadeia causal verificável;
- severidade foi calibrada pela consequência real;
- riscos puramente hipotéticos foram separados;
- primitivas existentes foram consideradas antes de nova abstração;
- gates relevantes foram checados por falsos verdes;
- correções anteriores foram reavaliadas sem mover a trave;
- está claro o que bloqueia, o que é follow-up e o que é mera preferência;
- se não restam defeitos materiais, isso foi dito explicitamente.

O objetivo não é provar que o reviewer consegue imaginar mais coisas. É aumentar
a probabilidade de que a mudança **faça exatamente o que promete no sistema que
realmente existe**.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
