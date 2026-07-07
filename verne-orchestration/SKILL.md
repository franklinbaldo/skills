---
name: verne-orchestration
description: >-
  Orchestrate Jules coding sessions via the Verne CLI (uvx verne).
  Use when delegating async coding tasks to Jules, managing multi-repo
  orchestration, checking session status, or approving plans.
---

# Verne — Jules Orchestration via CLI

> **Verne vs. in-harness subagents:** use this skill to delegate work to **external Jules API sessions** — async, cross-repo, and they survive after your own session ends. If you just need to fan out parallel LLM work (labeling, reviewing, extracting) **within the current session**, use the `llm-work-via-subagents` skill instead.

**Verne** é a CLI para a Jules API. Rode sempre via `uvx` — não requer instalação permanente.

```bash
uvx --from git+https://github.com/franklinbaldo/verne verne <command>
```

Ou defina um alias para a sessão:
```bash
alias verne='uvx --from git+https://github.com/franklinbaldo/verne verne'
```

## Configuração

Obtenha a API key em https://jules.google.com/settings#api e exporte:

```bash
export JULES_API_KEY=<sua_key>
```

Verne lê `JULES_API_KEY` do ambiente. Sem a key, todos os comandos falham com 401.

---

## Comandos principais

### Sessions
```bash
# Criar sessão em um repositório
verne sessions create \
  --repo franklinbaldo/pink \
  --branch main \
  --prompt "Add unit tests for src/pink/document.py" \
  --title "Add document tests"

# Listar sessões ativas
verne sessions list

# Ver status de uma sessão
verne sessions get <session_id>

# Aprovar plano (quando requirePlanApproval=true)
verne sessions approve-plan <session_id>

# Enviar mensagem para sessão ativa
verne sessions send-message <session_id> "Fix the edge case for empty files"
```

### Agents
```bash
# Listar agentes disponíveis
verne agents list

# Lançar um agente específico
verne agents launch <agent_name> --repo franklinbaldo/pink
```

### PR
```bash
# Listar PRs criados por Jules
verne pr list --repo franklinbaldo/pink

# Ver PR específico
verne pr show <pr_number> --repo franklinbaldo/pink
```

### Heartbeat
```bash
# Monitorar sessões ativas e ser notificado de mudanças de estado
verne heartbeat --interval 30
```

### Interactive
```bash
# Modo interativo para criar e gerenciar sessões
verne interactive
```

---

## Orchestration Protocol (Master/Worker)

Para tarefas que envolvem múltiplos repositórios, use o padrão Master/Worker documentado em `ORCHESTRATION_PROTOCOL.md` do repositório verne (não deste repo — se o arquivo não existir lá, use o protocolo inline abaixo, incluindo o schema JSON, como fallback).

### Fluxo básico
1. **Master session** (sem repo) define estratégia global
2. **Verne** cria Worker sessions por repositório
3. Workers executam tarefas com dependências entre si
4. Heartbeat reporta status de volta ao Master

### Schema de instrução do Master
```json
{
  "orchestration_id": "feat-X",
  "global_goal": "Implementar Feature X em frontend e backend",
  "execution_mode": "plan_first",
  "workers": [
    {
      "worker_id": "backend",
      "repository": "franklinbaldo/pink",
      "task_description": "Implementar endpoints da Feature X",
      "dependencies": []
    },
    {
      "worker_id": "frontend",
      "repository": "franklinbaldo/verne",
      "task_description": "Consumir novos endpoints da Feature X",
      "dependencies": ["backend"]
    }
  ]
}
```

---

## Session states

| Estado | Significado | Ação |
|---|---|---|
| `QUEUED` | Aguardando início | Esperar |
| `PLANNING` | Gerando plano | Esperar |
| `AWAITING_PLAN_APPROVAL` | Plano pronto | `verne sessions approve-plan <id>` |
| `AWAITING_USER_FEEDBACK` | Precisa de input | `verne sessions send-message <id> "..."` |
| `IN_PROGRESS` | Executando | Esperar (~10min) |
| `COMPLETED` | Concluído | Ver PR criado |
| `FAILED` | Erro | Investigar e recriar |

---

## Padrões de delegação

### Pattern 1: Review assíncrono
```bash
# Após push de branch
verne sessions create \
  --repo franklinbaldo/pink \
  --branch feat/minha-feature \
  --prompt "Review feat/minha-feature: check error handling, test coverage, security" \
  --title "Review feat/minha-feature"
```

### Pattern 2: Geração de testes
```bash
verne sessions create \
  --repo franklinbaldo/pink \
  --prompt "Add BDD tests for src/pink/document.py following pytest-bdd patterns in tests/step_defs/" \
  --title "Add document.py tests"
```

### Pattern 3: Bug fix com regression test
```bash
verne sessions create \
  --repo franklinbaldo/pink \
  --prompt "Fix issue: <descrição do bug> in <arquivo>. Add regression test." \
  --title "Fix <bug>"
```

---

## Workflow com aprovação de plano

```bash
# 1. Criar com aprovação obrigatória
verne sessions create \
  --repo franklinbaldo/pink \
  --prompt "Refactor queries.py to use ibis 12 new API" \
  --require-plan-approval \
  --title "Refactor queries"

# 2. Aguardar AWAITING_PLAN_APPROVAL
verne sessions get <id>

# 3. Revisar plano nos activities
verne sessions activities <id>

# 4. Aprovar
verne sessions approve-plan <id>
```

---

## Jules resumes automaticamente via PR comments

Jules monitora PRs que criou. Ao comentar no PR com feedback específico, Jules retoma automaticamente:

1. Jules completa task → cria PR
2. Você comenta no PR com feedback
3. Jules detecta o comentário → estado muda para `AWAITING_PLAN_APPROVAL`
4. Aprove o novo plano: `verne sessions approve-plan <id>`

**Use PR comments para iterar — não crie nova sessão desnecessariamente.**

---

## Reportando bugs e sugestões

Ao encontrar friction real usando verne, abra uma issue em **https://github.com/franklinbaldo/verne/issues**.

### Quando abrir uma issue

- **Bug**: comando retornou erro inesperado, output quebrado, estado incorreto
- **Friction**: precisou implementar algo manualmente que verne deveria fazer
- **Missing feature**: tentou um fluxo e o comando não existia

### Como escrever uma boa issue

A issue deve descrever **experiência real**, não abstrata:

```markdown
## Problema
[O que você estava tentando fazer]

## Cenário real
[O comando exato que rodou, o output que recebeu, o que esperava]

## Request
[O que verne deveria fazer em vez disso]
```

**Boas issues têm:**
- Comando exato que causou o problema
- Output real (não parafraseado)
- O que o agente precisou fazer como workaround


---

## Referências

- Repositório: https://github.com/franklinbaldo/verne
- Issues: https://github.com/franklinbaldo/verne/issues
- Jules API docs: https://developers.google.com/jules/api/reference/rest
- API key: https://jules.google.com/settings#api
- Orchestration Protocol: `ORCHESTRATION_PROTOCOL.md` no repo verne (pode não existir; nesse caso, use o protocolo inline e o schema JSON desta skill)
