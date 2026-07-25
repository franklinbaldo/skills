# Fase 3 — Análise Jurídica Subjetiva

## Princípio fundamental

**Compilação Lean é condição necessária, não suficiente, para marcar derrota.**

Um teorema pode compilar porque os axiomas que o sustentam foram formulados de
modo vago ou excessivamente favorável. A Fase 3 examina a qualidade material
dos axiomas, não apenas a validade formal do proof.

## O ciclo iterativo

Esta fase pode retornar à Fase 2 se algum axioma central falhar nos critérios
abaixo. O ciclo Fase 2 ↔ Fase 3 encerra quando todos os axiomas centrais de
todos os teoremas relevantes passam nos três critérios — ou quando se conclui
que um ataque não é sustentável e deve ser descartado.

## Critérios de parada (seis condições por axioma central)

Para cada axioma que sustenta um teorema relevante, verificar:

1. **Ancoragem documental ou jurisprudencial direta**: O axioma tem apoio
   expresso no acórdão recorrido, nos autos, ou em precedente identificado?
   Axioma sem ancoragem é hipótese, não fato.

2. **Contra-argumento equivalente enfrentado**: Existe um axioma adverso de
   força comparável que o theorema não refuta? Se sim, o raciocínio está
   incompleto — não marca derrota.

3. **Formulação razoável**: O axioma, tal como formulado, seria aceito por
   um operador do direito informado e imparcial? Formulações excessivamente
   favoráveis ("universalização generosa") são candidatas a reformulação
   na Fase 2.

4. **Proveniência e status verificados**: se um axioma central tem
   `prov: pendente` ou `status: pendente` na anotação Argdown da Fase 1, o
   ônus argumentativo é adicional. Registrar explicitamente na análise e
   recomendar verificação antes de protocolar a peça. Axioma pendente não
   trava o pipeline — mas derrota marcada com base em axioma pendente é
   derrota condicional, não definitiva.

5. **Qualificação cognitiva da omissão**: para ataques por omissão, confirmar
   o resultado do gate da Fase 1. Se os compromissos anteriores determinam
   univocamente a resposta, registrar integração recognitiva. Se apenas
   direcionam ou deixam alternativas compatíveis, registrar cognição
   geratória e evitar descrever a conclusão como consequência já contida no
   acórdão. Rejeição implícita plausível deve ser enfrentada como
   contra-argumento.

6. **Ficha epistemológica de STEEL_n**: toda premissa steelman deve indicar
   ator, base textual, tipo de reconstrução, status de suporte e condição de
   falsificação. `semSuporte` ou `puramenteCaridosa` não significa derrota
   automática, mas impede apresentar a premissa como descrição do que o
   tribunal efetivamente decidiu.

Se algum critério falha, retornar à Fase 2 com instrução específica de
refinamento. Não ajustar o axioma dentro desta fase — a reformulação ocorre
no arquivo Lean.

## Registro em prosa jurídica

A análise desta fase é escrita em registro de **parecer institucional**,
não de workspace. O leitor do documento é um procurador-sênior revisando
trabalho de um júnior — espera-se linguagem técnica, qualificadores
cautelosos e conclusões explícitas.

### Comparação de registros

| Registro workspace (proibido aqui) | Registro forense/institucional |
|---|---|
| "O steelman V1_a falha no §1º III check" | "O fundamento invocado presta-se a justificar qualquer decisão sobre matéria análoga, violando o art. 489, §1º, III, do CPC" |
| "O axioma compila mas a formulação é generosa" | "A premissa tem ancoragem, cabe ressalvar contudo que sua amplitude poderia abranger situações não cobertas pelo precedente" |
| "A partição foi completada com cinco saídas" | "Não se identifica postura legítima do tribunal diante do precedente vinculante invocado" |

### Qualificadores cautelosos (usar sistematicamente)

- "tem sólida ancoragem em..."
- "cabe ressalvar contudo que..."
- "demanda enfrentamento explícito de..."
- "a força do argumento é significativa, mas..."
- "o contra-argumento adverso não foi integralmente afastado"

## Estrutura sugerida do documento

Para cada teorema relevante:

---

**Teorema [N] — [nome curto]**

*Identificação*: [o que o teorema estabelece em termos jurídicos]

*Análise dos axiomas centrais*:
- Axioma `[nome]`: [análise de ancoragem, contra-argumento, formulação]
- Axioma `[nome]`: [idem]

*Força argumentativa*: [avaliação geral, com qualificadores]

*Riscos e contra-ataques*: [o que a parte adversa poderia opor; se o
counter-axiom existe e tem força comparável]

*Parecer parcial*: prosseguir com este ataque / retornar à Fase 2 para
[instrução específica]

---

*Apreciação conjunta*: [como os ataques que prosseguem se complementam;
lacunas de cobertura]

*Parecer final*: prosseguir para a Fase 4 / retornar à Fase 2 para os
ataques [N] com instrução [X]

---

## Heurística para a LLM-analista

Se a análise é feita pela mesma LLM que formalizou (Fase 2), o risco de
viés de confirmação é maior: a LLM tende a avaliar positivamente os axiomas
que ela mesma formulou.

Heurística prática: ao analisar cada axioma, formular explicitamente o
counter-axiom mais forte possível e verificar se ele também compilaria.
Se compilar, o teorema não marca derrota — o espaço argumentativo é disputado.

## Output esperado

Documento Markdown com:
- Análise por teorema (estrutura acima)
- Apreciação conjunta
- Parecer final explícito: lista de ataques que prosseguem para a Fase 4
  e lista de ataques a descartar ou refinar

O documento serve de insumo para a Fase 4 (Síntese de derrotas).
