# Fase 1 — Análise Toulmin

## Por que Toulmin

A estrutura de Toulmin decompõe qualquer argumento jurídico em elementos com
carga útil distinta. No contexto de Embargos de Declaração, a decomposição
revela o que o acórdão afirma (A*) e o que a peça contraria (P*), com
visibilidade sobre onde os dois diferem — e por quê.

Quatro elementos obrigatórios:

| Elemento | Pergunta-guia | Papel na formalização |
|---|---|---|
| **Claim** | O que está sendo afirmado? | Camada 6 (teorema) |
| **Data** | Em que fatos ou documentos isso se apoia? | Camada 5 (fatos do caso) |
| **Warrant** | Que regra ou princípio conecta Data à Claim? | Camadas 3-4 (normas/precedentes) |
| **Rebuttal** | Sob quais condições a Claim cede? | Ponto de ataque potencial |

Dois elementos opcionais:

| Elemento | Papel |
|---|---|
| **Backing** | Autoridade que sustenta o Warrant (doutrina, jurisprudência) |
| **Qualifier** | Grau de certeza da Claim ("salvo melhor juízo", "com ressalva de...") |

## Regra crítica — Warrant completo

**O Warrant deve ser registrado em sua integralidade, incluindo ressalvas e
exceções.**

Esta é a regra que captura omissões e aplicações seletivas de precedente. Se
a ementa de um acórdão do STF contém ressalva, a ressalva entra no Warrant
mesmo que o acórdão atacado tenha ignorado-a. Warrant incompleto é a
assinatura de um vício de omissão ou de aplicação seletiva.

Exemplos de Warrants incompletos vs. completos:

> **Incompleto**: "A acumulação de cargo de professor com cargo técnico-científico
> é lícita (ratio da ADI 3.772)."

> **Completo**: "A acumulação de cargo de professor com cargo técnico-científico
> é lícita, *excluídos os especialistas em educação* (ratio da ADI 3.772,
> Tribunal Pleno, relator Min. Carlos Britto)."

## Template de pacote

Usar numeração **A\*** para argumentos do acórdão e **P\*** para argumentos da peça.

---

**Pacote [A1 / P1] — [título curto]**

- **Claim**: [afirmação central do argumento]
- **Data**: [fatos, documentos, precedentes invocados como base factual]
- **Warrant**: [regra que conecta Data à Claim — completo, com ressalvas]
- **Backing**: [autoridade que sustenta o Warrant, se aplicável]
- **Qualifier**: [grau de certeza ou condições de aplicação, se explícito]
- **Rebuttal**: [condições sob as quais a Claim cederia; preencher mesmo se
  o acórdão não as discutiu]
- **Observações**: [ambiguidades, lacunas, interações com outros pacotes]

---

## Heurísticas de leitura

Após decompor cada pacote, verificar:

1. **Warrant completo?** Se o precedente invocado tem ressalvas ou exceções,
   elas estão no Warrant? Se não, é candidato a P*.
2. **Data corresponde à Claim?** Os fatos concretos apontados realmente
   sustentam a conclusão, ou a Claim salta além dos fatos?
3. **Rebuttal foi enfrentado?** Se um Rebuttal óbvio existe e o acórdão
   não o discutiu, é candidato a omissão (art. 1.022, I, CPC).
4. **Interação entre pacotes A\*?** Pacotes A2 e A3 frequentemente são
   instrumentais a A1. Identificar a estrutura de suporte antes de passar
   à Fase 2.

## Output esperado

Documento Markdown com:
- Todos os pacotes do acórdão (A*), incluindo os instrumentais
- Todos os pacotes da peça (P*), um por vício identificado
- Observações sobre interações e lacunas

O documento serve de insumo direto para a Fase 2 (Dung estrutural).
