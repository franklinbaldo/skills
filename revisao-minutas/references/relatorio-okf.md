# Relatório OKF de triagem

Leia este arquivo ao emitir ou persistir o relatório estruturado da triagem.

## Contrato

Cada triagem produz um concept OKF em Markdown com frontmatter YAML e corpo legível. O objetivo é permitir automação posterior sem sacrificar a leitura humana.

Campos recomendados:

```yaml
---
type: Relatorio de Triagem de Minuta
title: <peça> — <processo ou identificador>
description: <veredito + risco dominante em uma linha>
tags: [triagem, <tipo-de-peca>, <carteira>]
timestamp: <ISO 8601>
processo: <CNJ>
peca: <tipo enumerado>
orgao: <órgão representado>
veredito: <apta | apta-com-ajustes | inapta>
riscos_fatais: <n>
riscos_relevantes: <n>
edits_propostos: <n>
verificacao_fatica: <realizada | dispensada | pendente>
---
```

Evite campos livres quando um valor enumerado estável resolver.

## Corpo mínimo

Use `##` em diante e não use regras horizontais fora dos delimitadores YAML.

```markdown
## Veredito

🟡 Apta com ajustes cirúrgicos. <motivo dominante>

## Riscos identificados

### Fatais
<nenhum | lista>

### Exposição institucional
<lista>

### Ancoragem fática
<confirmado / desmentido / pendente>

### Sanções e formais
<somente consequências práticas>

## Edits cirúrgicos

1. **Localização**: <tópico/parágrafo>
   **Original**: "<trecho exato>"
   **Substituto**: "<trecho exato>"
   **Motivo**: <risco eliminado>

## Não mexi porque
<opcional>

## Checklist de protocolo
<providências materiais externas ao texto>

## Verificação fática
<fontes, perguntas e pendências relevantes>
```

## Regra de limpeza da peça

Pendência de verificação nunca deve ser inserida dentro do texto que será protocolado. Nada de colchetes, TODOs ou comentários que possam vazar para a versão assinada.

A pendência fica no relatório e no checklist de protocolo. A peça/edit entregue permanece limpa.

## Veredito condicionado

Quando uma conclusão dependa de confirmação externa ainda pendente, explicite a condição no relatório e marque a verificação como pendente. Não registre `apta` de forma incondicional sobre fato material não confirmado.

## Organização de bundle

Uma organização possível:

```text
triagem/
├── index.md
├── log.md
└── 2026/
    └── <CNJ>-<peca>.md
```

A organização é convenção de armazenamento, não parte necessária de cada triagem.
