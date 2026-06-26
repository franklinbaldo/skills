---
name: triagem-inbox
description: |
  Rotina de triagem da inbox Kanoê (#GAB#FSB). Consulta mcp__pink__inbox,
  analisa cada expediente aberto, posta comentário de triagem no Pink,
  registra o resultado em rotinas/triagem-inbox/YYYY-MM-DD.md, recebe as
  pastas e distribui em caixas por tipo e dígito do processo.
---

# Triagem Inbox

Rotina recorrente. A cada execução: consultar inbox → analisar → comentar no Pink → salvar log no repo.

## Log file

`rotinas/triagem-inbox/YYYY-MM-DD.md` — uma entrada por execução.

### Frontmatter obrigatório

```yaml
---
type: Triagem Inbox
title: Triagem Inbox — YYYY-MM-DD
date: YYYY-MM-DD
setor: "#GAB#FSB"
executor: <nome ou "agente">
total_inbox: <N>
itens_triados: <N>
---
```

### Estrutura do body

```markdown
## Urgentes (prazo ≤ 7 dias)

| Número | pasta_id | exp_id | Classe | Prazo | Ação | Comentário postado |
|---|---|---|---|---|---|---|
| 70445518020258220001 | 261801 | 1188312 | PUIL | 2026-06-23 | Responder prazo | sim |

## Demais

| Número | pasta_id | exp_id | Classe | Prazo | Ação |
|---|---|---|---|---|---|
...

## Observações

Notas livres sobre padrões, dúvidas ou itens a acompanhar.
```

## Passo a passo

1. `mcp__pink__inbox` — obtém lista completa
2. Ordenar por prazo (vencidos e ≤7 dias primeiro)
3. Para cada item urgente: `mcp__pink__pasta_show` + `mcp__pink__expediente_show`
4. Se pasta_show + expediente_show não revelam a ação: ver skill `sei-gemini-analise`
   - Gerar PDF do processo SEI via `sei_gerar_pdf_processo`
   - Enviar ao Gemini API com key rotation (keys em `../.env`)
   - Usar `gemini-2.5-flash` como modelo primário
5. Postar comentário no expediente via `mcp__pink__expediente_comentar` com dois parágrafos:
   - **§1 — Ação e motivo**: o que a PGE-IPERON deve fazer (ou não fazer) e por quê. Direto, sem rodeios. Ex.: "Ciência apenas — troca de perito é ato do juízo, sem providência do IPERON." ou "Manifestação necessária em 5 dias — retorno de Turma Recursal exige leitura do acórdão para decidir se há recurso cabível."
   - **§2 — Discussão atual e relevância**: estado do processo, último ato, quem tem a palavra, e por que isso importa (ou não) para a PGE-IPERON. 2-3 frases no máximo.
6. Registrar no log: número, pasta_id, exp_id, prazo, ação resumida, `comentario_postado: sim/não`
7. **Receber todas as pastas** da inbox: `mcp__pink__pasta_receber` com todos os `pasta_id` do inbox de uma vez.
8. **Distribuir em caixas**: `mcp__pink__pasta_mover` em lote — ver seção "Distribuição em Caixas" abaixo.
9. Commitar o log e a skill se houve atualização, depois abrir PR.

## Prioridades

- Prazo vencido ou hoje → triagem imediata
- Cumprimento de sentença com obrigação de fazer (suspender IRRF, pagar RPV) → urgente
- Precatório, PUIL, recursos em tribunais superiores → verificar sessão
- Cumprimentos de sentença comuns → triagem normal
- Processos com trânsito em julgado favorável → apenas registrar e indicar arquivamento

## Distribuição em Caixas

Após comentar todos os expedientes e registrar o log, receber e distribuir em lote.

### Passo 1 — Receber

```
mcp__pink__pasta_receber(pasta_ids=[<todos os pasta_id do inbox>])
```

Aceita um array; trata cada pasta individualmente internamente. Zero falhas esperadas.

### Passo 2 — Classificar

| Tipo | Critério | Destino |
|---|---|---|
| **Mera ciência** | Ação = "Ciência —" ou "Acompanhar —" sem prazo ativo do IPERON | Caixa **Ciência** (id 915) |
| **IRRF** | Isenção IR servidores civis — JEFP, perito médico, cumprimento de isenção IR | Estagiárias (por dígito) |
| **Demais** | Precatórios, recursos, pensão, penhora, SINDEPRO, etc. | Assessores (por dígito) |

### Passo 3 — Dígito de distribuição

Usar o **último dígito do número sequencial** (primeiros 7 dígitos do número CNJ). Ex.: processo `70128783520268220001` → sequencial `7012878` → dígito **8**.

| Caixa | id | Dígitos |
|---|---|---|
| Mayla — Triagem 0123 | 3337 | 0, 1, 2, 3 |
| Erion — Triagem 456 | 3344 | 4, 5, 6 |
| Micaella — Triagem 789 | 3317 | 7, 8, 9 |
| Est Luzia — Triagem 01234 | 3418 | 0, 1, 2, 3, 4 |
| Est Fernanda — Triagem 56789 | 3419 | 5, 6, 7, 8, 9 |

### Passo 4 — Mover em lote

```
mcp__pink__pasta_mover(movimentos=[
  {"pasta_id": 261603, "caixa_id": 3418},  # IRRF, dígito 2 → Est Luzia
  ...
])
```

Primeiro mover as de **Ciência** (mais numerosas e uniformes), depois IRRF, depois demais.

---

## Padrões de triagem por tipo de caso

### IRRF — Isenção de Imposto de Renda (militares da reserva)

**ACAO padrão: apenas ciência. Não requer petição do IPERON.**

Motivos:
- IPERON é sistematicamente excluído do polo passivo nesses processos
- Militares da reserva remunerada **não são segurados do IPERON** (regime próprio dos militares é distinto)
- IPERON **não gerencia a folha de pagamento** de militares da reserva
- Os eventuais valores de restituição de IRRF são suportados pelo **Estado de Rondônia**, não pelo IPERON
- Quem responde e peticiona é o setor da PGE que representa o **Estado de Rondônia** (PGE-Estado) — distinto da PGE-IPERON (este setor). A PGE representa tanto o IPERON quanto o Estado, mas por setores diferentes; nestes processos, a PGE-IPERON não tem atuação.

Portanto: ao receber intimação em processo de isenção de IRRF de militar, a ação do IPERON é apenas tomar ciência e encaminhar para arquivo. Não montar petição, não peticionar.

## Orientações aprendidas em uso

- **Preferir Kanoê antes do SEI**: `pasta_show` e `expediente_show` revelam o contexto na maioria dos casos sem precisar abrir o SEI.
- **Análise SEI via Gemini**: quando necessário, usar skill `sei-gemini-analise` — gera PDF do processo e analisa via Gemini API com key rotation (não ler documento por documento via MCP).
- **Modelos Gemini**: `gemini-2.5-flash` é o modelo recomendado para free tier em 2026; `gemini-2.0-flash` esgota quota rápido com PDFs.
- **Triagem é ciência, não petição**: na maioria dos casos o comentário de triagem apenas registra o que foi verificado e indica a ação pendente. Só peticionar quando há prazo imediato e responsabilidade do IPERON.
- **Processos de IRRF de militares**: IPERON não é parte legítima — apenas dar ciência e arquivar (ver padrão acima).
- **`expediente_comentar` usa `texto=`**, não `comentario=` — parâmetro errado retorna erro 422.
- **Trocas de perito (Andervan, Eduardo William, Marlon)**: mera ciência — ato do juízo, IPERON não peticiona.
- **Ciência inclui "Acompanhar"**: processos onde não há prazo ativo para o IPERON agir vão para a caixa Ciência, mesmo que o log registre "Acompanhar".

## Tipo OKF

`Triagem Inbox` — específico desta rotina. Outros tipos de triagem têm suas próprias skills.
