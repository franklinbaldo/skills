---
name: legal-argument-lean
description: >-
  Formaliza e audita argumentos jurídicos brasileiros em Lean 4 quando isso reduz
  uma incerteza estrutural real: dependências ocultas, premissas load-bearing,
  omissão lógica, inconsistência, aderência a precedente ou steelman de uma
  decisão. Também use para continuar uma formalização já existente, interpretar
  `#print axioms` e traduzir achados formais de volta para linguagem jurídica.
  Não use Lean só para “dar rigor” a uma peça já compreensível; a skill deve
  primeiro justificar o ganho esperado da prova formal e pode concluir que não
  vale formalizar.
---

# Legal argument audit with Lean

Lean é uma ferramenta de **auditoria de dependências argumentativas**. Não é um
selo de validade jurídica.

A primeira pergunta desta skill é sempre:

> **Que incerteza concreta ficará menor depois da formalização?**

Se não houver resposta específica, pare antes de escrever Lean.

## Gate de formalização

Só formalize quando pelo menos um destes ganhos estiver presente:

- descobrir quais premissas são realmente necessárias para a conclusão;
- testar se uma alegada omissão é uma lacuna derivacional ou apenas ausência de
  frase expressa;
- verificar se duas conclusões dependem de conjuntos incompatíveis de premissas;
- reconstruir caridosamente uma decisão e localizar exatamente onde ela precisa
  de uma premissa não expressa;
- comparar duas rotas de prova e saber qual pressupõe mais autoridade/fato;
- distinguir consequência lógica de escolha interpretativa;
- tornar uma dependência em precedente/norma/fato auditável por `#print axioms`.

Não formalize quando o objetivo real for apenas:

- redigir melhor;
- parecer mais técnico;
- resumir jurisprudência;
- resolver disputa predominantemente valorativa/proporcional;
- substituir pesquisa de fonte;
- provar que a tese preferida “está certa”.

### Teste de valor antes de abrir Lean

Declare em linguagem natural:

```text
alvo: conclusão ou defeito que será testado
incerteza: o que hoje não sabemos sobre a estrutura do argumento
evidência de sucesso: qual saída do Lean mudaria a análise jurídica
custo: o que precisaremos modelar/verificar para chegar lá
```

Se “evidência de sucesso” não mudar nenhuma decisão, Lean seria cerimônia.

## O que Lean pode e não pode provar

Lean prova derivabilidade a partir das premissas declaradas. Ele não estabelece
que:

- um fato ocorreu;
- uma citação está correta;
- um precedente continua controlling;
- uma interpretação é juridicamente superior;
- um steelman corresponde à intenção real do julgador.

Consequência: cada resultado formal deve sair acompanhado da classificação das
premissas que o tornam possível.

## Contrato de modelagem

Use seis camadas:

```text
1. tipos básicos
2. predicados jurídicos opacos
3. normas
4. precedentes
5. fatos/claims do caso
6. teoremas
```

Antes de modelar, leia
[`references/modeling-and-lean.md`](references/modeling-and-lean.md).

Nunca esconda interpretação jurídica em definição computacional só para deixar a
prova “bonita”. Quando um passo depende de julgamento jurídico, torne a
premissa visível.

## Fluxo direto

Para um alvo claro:

1. passe pelo gate de formalização;
2. declare o alvo e a hipótese jurídica que está sendo auditada;
3. classifique as premissas necessárias;
4. verifique fontes materiais antes de transformá-las em axiomas;
5. modele o mínimo suficiente para distinguir as rotas relevantes;
6. compile;
7. rode `#print axioms` em todo teorema material;
8. interprete o conjunto de dependências;
9. traduza o achado de volta para linguagem jurídica convencional.

O produto não é “compilou”. O produto é algo como:

> A conclusão só decorre se forem aceitas simultaneamente as premissas X e Y; Y
> não aparece no acórdão / depende de interpretação autônoma / é contrariada pelo
> documento Z.

## Omissão: teste estrutural antes do entusiasmo

Para alegada omissão, diferencie:

1. a questão foi expressamente tratada?
2. houve rejeição implícita plausível?
3. a questão era decisiva para o resultado?
4. a conclusão omitida era univocamente determinada pelas premissas aceitas?
5. a decisão pode ser reconstruída sem inventar nova premissa material?

Uma frase ausente não é automaticamente uma derivação ausente.

## Adversarial / steelman mode

O uso mais valioso frequentemente é formalizar **a decisão atacada**, não a tese
do usuário.

Fluxo:

1. mapear o argumento sem escolher vencedor;
2. identificar gaps reais;
3. usar `sorry` para passos que ainda não seguem;
4. formular variantes plausíveis de `STEEL_n` somente como hipóteses caridosas;
5. testar quais variantes salvam a conclusão;
6. auditar dependências;
7. verificar se o record jurídico sustenta alguma dessas variantes;
8. só então classificar o defeito.

Leia [`references/adversarial.md`](references/adversarial.md) integralmente antes
de uma formalização adversarial.

Não transforme “existe um conjunto de axiomas que torna a decisão consistente” em
“a decisão está fundamentada”. O ponto é saber **qual conjunto seria necessário**
e se ele existe na decisão/ordenamento/fatos.

## Pipeline complexo

Quando houver múltiplos ataques ou reconstruções concorrentes:

```text
material original
→ Argdown: anatomia/topologia
→ Lean: um teorema por ataque material
→ revisão substantiva independente/autorizada
→ síntese das derrotas/sobreviventes
→ tradução forense
```

Invariantes:

- Argdown mapeia; não escolhe vencedor;
- compilação é necessária, não suficiente;
- falha de prova volta ao mapa, não gera axioma inventado;
- steelman permanece marcado como steelman;
- a síntese final usa vocabulário jurídico, não workspace jargon.

O exemplo completo permanece em `pipeline/exemplo_marilene/`.

## Dependências load-bearing

`#print axioms` é central porque responde à pergunta mais útil da skill:

> **De que exatamente esta conclusão depende?**

Classifique cada dependência em:

- norma;
- precedente;
- fato;
- escolha interpretativa/predicado opaco;
- premissa de steelman.

Depois pergunte qual delas é:

- necessária em todas as rotas de prova;
- dispensável;
- controversa;
- não verificada;
- inexistente no raciocínio da decisão.

Para bibliotecas reutilizáveis, leia
[`references/libraries-and-audit.md`](references/libraries-and-audit.md).
Esses módulos são templates de formalização, nunca fontes jurídicas substitutas.

## Quando parar

Pare a formalização quando:

- o conjunto load-bearing já está identificado;
- novas definições não mudam a distinção jurídica relevante;
- a disputa restante é de interpretação/valor e não de derivabilidade;
- o custo de modelar mais detalhe não altera nenhuma conclusão acionável;
- a próxima etapa é verificar fonte ou escrever a peça.

Mais Lean não é automaticamente mais rigor.

## Tradução forense

O workspace formal não deve vazar para a peça salvo quando um conceito técnico
for realmente útil.

Antes de redigir o produto forense, leia
[`references/forensic-translation.md`](references/forensic-translation.md).

Traduza:

```text
teorema / proof route / axioms
→ conclusão jurídica
→ premissas necessárias
→ qual delas falta/é controvertida
→ consequência processual pertinente
```

Não comece a peça dizendo que “o Lean demonstrou”.

## Segurança epistêmica

1. verifique normas, precedentes, datas e citações em fonte adequada;
2. ancore axiomas fáticos nos autos;
3. diferencie citação literal de paráfrase do formalizador;
4. não adicione premissa para forçar compilação;
5. reporte formal, factual, precedencial e interpretativo separadamente;
6. não exponha material confidencial a serviços externos sem autorização e base
   adequada.

## Definition of Done

A tarefa termina quando:

- o gate demonstrou por que Lean acrescenta valor;
- o alvo é explícito;
- cada premissa material está classificada;
- fontes necessárias estão verificadas ou marcadas como pendentes;
- o modelo preserva as escolhas jurídicas em vez de escondê-las;
- teoremas materiais compilam ou a falha foi interpretada substantivamente;
- `#print axioms` foi usado nos resultados relevantes;
- steelman e premissas verificadas permanecem distinguíveis;
- está claro quais dependências são load-bearing;
- o resultado foi traduzido em linguagem jurídica acionável;
- a formalização parou quando deixou de reduzir incerteza.

O melhor resultado desta skill às vezes é um arquivo Lean pequeno. E às vezes é a
conclusão, tomada cedo, de que **não vale a pena formalizar este problema**.