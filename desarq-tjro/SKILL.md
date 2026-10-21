---
name: desarq-tjro
description: Solicita desarquivamento de processos físicos no DESARQ/TJRO via API (curl), em lote, com gratuidade de órgão governamental; também consulta status, eventos e links de download das solicitações. Use quando Franklin pedir para desarquivar processos físicos do TJRO, obter cópia digitalizada de autos arquivados, ou acompanhar pedidos no DESARQ.
compatibility: Requer sessão do usuário no DESARQ (login gov.br ou CNJ feito por ele no navegador). Opera com curl e jq (Jatobá ou terminal) ou com fetch via Claude in Chrome na aba logada.
---

# DESARQ/TJRO — desarquivamento via API

O DESARQ (`https://desarquivamento.tjro.jus.br`) é um SPA Angular sobre uma API REST. Esta skill usa a API direto para pedir desarquivamento em lote pelo caminho **Gratuidade** (Fazenda Pública: isenção para órgãos governamentais, Lei Est. 3.896/2016 e Ato Conjunto 07/2019-PR/CGJ), e para acompanhar pedidos.

Mapa extraído do bundle JS e validado com sessão real (login gov.br) em 20/10/2026. Os GETs estão conferidos. O POST `guia/guiadispensada` ainda não foi chamado direto pela API: na primeira execução real, fazer UM item, conferir a resposta e corrigir esta skill antes do resto do lote.

## Arquitetura

| Item     | Valor                                                                                  |
| -------- | -------------------------------------------------------------------------------------- |
| Front    | `https://desarquivamento.tjro.jus.br` (WAF F5/TSPD — não usar curl contra o front)     |
| API      | `https://desarquivamento-back.tjro.jus.br/back` (sem WAF; exige Bearer; 401 sem token) |
| Keycloak | `https://rhbk.tjro.jus.br/realms/PJRO`, client público `desarq-app`, PKCE S256         |
| Login    | gov.br ou CNJ — ambos funcionam (`identity_provider` = `govbr` / `cnj`)                |

Device flow desabilitado no client. O grant `refresh_token` é aceito para `desarq-app` sem secret.

## 1. Autenticação

Nunca digitar senha nem fazer login pelo usuário. Ele entra no navegador; o token sai da sessão dele. Não gravar tokens em arquivo versionado, memória ou log, nem imprimi-los.

### Opção A — curl (Jatobá ou terminal)

1. O usuário entra no DESARQ.
2. DevTools → Network → filtro `token` → `POST .../openid-connect/token` → Response → copiar `refresh_token`.
3. `export DESARQ_RT='<refresh_token>'`.

```bash
API=https://desarquivamento-back.tjro.jus.br/back
desarq_token() {
  local r; r=$(curl -sS -X POST https://rhbk.tjro.jus.br/realms/PJRO/protocol/openid-connect/token \
    -d client_id=desarq-app -d grant_type=refresh_token --data-urlencode "refresh_token=$DESARQ_RT")
  DESARQ_TOKEN=$(jq -r .access_token <<<"$r"); DESARQ_RT=$(jq -r .refresh_token <<<"$r")
  H=(-H "Authorization: Bearer $DESARQ_TOKEN" -H 'Content-Type: application/json')
}
```

Chamar `desarq_token` antes de cada item. `invalid_grant` = sessão SSO expirou → novo login.

### Opção B — Claude in Chrome (aba logada)

Capturar o Bearer que o próprio app envia, sem expor o valor:

```js
window.__auth=null;
const o=XMLHttpRequest.prototype.setRequestHeader;
XMLHttpRequest.prototype.setRequestHeader=function(k,v){if(k.toLowerCase()==='authorization')window.__auth=v;return o.apply(this,arguments)};
```

Depois clicar em "Minhas solicitações" (dispara chamadas à API) e usar `fetch(API+rota,{headers:{Authorization:window.__auth}})`. Retornar só formatos e contagens, nunca o token. Se der 401, clicar de novo em um menu para o app renovar e recapturar.

## 2. Endpoints (relativos a `$API`)

### Usuário e processo

| Método | Rota                              | Resposta verificada                                                                                                                                                                                                                                                                 |
| ------ | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `api/usuarios/me`                 | `{nome, login, loginComNome, cpfCNPJ, email, origemAutenticacao, pessoaJuridica, admin, permissoes}`                                                                                                                                                                                |
| GET    | `processo/numero/{numero}`        | **array**. `{numero}` só dígitos, CNJ novo (20) ou antigo (14). Campos: `id, nrProcesso, nrAntigo, acao, vara, idVara, autor, reu, advogadoAutor, advogadoReu, caixa, estante, prateleira, volume, destino, dataDistribuicao, obs, removidoEm, url…`. Vazio ou 404 = fora do acervo |
| GET    | `guia/existeSolicitacao/{numero}` | `true`/`false` (pedido deste usuário em andamento)                                                                                                                                                                                                                                  |
| GET    | `guia/valortaxa`                  | número em texto (ex.: `153.1`)                                                                                                                                                                                                                                                      |

**Duplicidade:** `processo/numero` pode trazer 2+ registros do mesmo processo (ids diferentes, mesmos dados — cadastro duplicado no arquivo, ou volumes distintos). O front usa `[0]`. No pré-voo, sinalizar quando houver mais de um, mostrando `id`, `volume` e `caixa`; se os volumes diferirem, perguntar se pede todos. Persistir a **seleção explícita de pares número/ID**. Atenção: `existeSolicitacao/{numero}` consulta por número, não volume; após criar o primeiro volume, pode bloquear os outros do mesmo processo. **Nunca contornar a proteção de duplicidade automaticamente**: suspender e verificar com o DESARQ se pedidos por volume são permitidos.

### Criar solicitação

| Método | Rota                  | Uso                                               |
| ------ | --------------------- | ------------------------------------------------- |
| POST   | `guia/guiadispensada` | **Gratuidade** — cria a solicitação sem boleto    |
| POST   | `guia/gerar`          | Boleto — resposta é PDF (não usar para a Fazenda) |

Corpo de `guiadispensada` (GuiaModel do front):

```json
{
  "login": "<me.login>", "cpfCNPJ": "<me.cpfCNPJ>", "tipoSolicitante": "<me.origemAutenticacao>",
  "solicitante": "<me.nome>", "pagador": "<me.nome>", "email": "<me.email>",
  "telefone": "<11+ dígitos>", "valor": 0, "pessoaEncontrada": true,
  "tipo": "Digitalizado", "idProcesso": 12345, "numeroProcesso": "<só dígitos, como buscado>",
  "natureza": "<processo.destino>",
  "pdf_gratuidade": "data:application/pdf;base64,....", "pdf_procuracao": ""
}
```

- `tipo`: `"Digitalizado"` (cópia digital, padrão) ou `"Físico"` (retirada na vara).
- Obrigatórios no front: `cpfCNPJ`, `solicitante`, `telefone`, `email`. `me` não traz telefone: pedir uma vez.
- `pdf_gratuidade`: data URL completa, PDF de até 1,5 MB, obrigatório na UI.
- **Reaproveitar o comprovante já aceito:** `GET desarquivamento/comprovante/{idSolicitacao}` devolve, em texto, a data URL do PDF de gratuidade enviado naquele pedido. Pegar de uma solicitação anterior com `tipoEmissao` = `Gratuidade SEM Procuração` cuja gratuidade foi concedida (evento "Dispensa de pagamento concedida") e usar no lote — com o OK do usuário sobre qual pedido-base usar.
- `pdf_procuracao`: vazio (procurador do Estado). O sistema registra `tipoEmissao` = `Gratuidade SEM Procuração`.
- Ciclo observado: `Pagamento Dispensado (em análise)` (evento "Dispensa de pagamento solicitada") → `Pagamento Dispensado` ("Dispensa de pagamento concedida", servidor do arquivo, cerca de 1 dia útil) → `Envio Concluído`.

**Regras de múltiplos volumes:** uma resposta positiva de `existeSolicitacao/{numero}` pode cobrir todos os volumes ou apenas um pedido; o contrato ainda não foi demonstrado. Não interpretar automaticamente como autorização para novos POSTs. Se houver dois IDs para o mesmo número, suspender após o primeiro e confirmar com o DESARQ a semântica de solicitação por volume.\n\n### Acompanhamento

| Método | Rota                                                                                | Resposta verificada                                                                                                                                                                                                                    |
| ------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `desarquivamento/busca?page=0&size=10[&processo=&modo=&andamento=&situacao=&data=]` | `{content:[…], page:{size, number, totalElements, totalPages}}`. Item: `id, idProcesso, numeroProcesso, estado, tipoDesarquivamento, tipoEmissao, numeroGuia, dataCriacao, dataUltimoEstado, caixa, obsProcesso, observacao, eventos…` |
| GET    | `desarquivamento/{idSolicitacao}`                                                   | detalhe completo, com `eventos[]`. **Recebe o id da solicitação, não o número do processo** (com número devolve 204)                                                                                                                   |
| GET    | `desarquivamento/eventos/{idSolicitacao}`                                           | `[{nomeEvento, dataEvento, descricaoEvento, nomeUsuario}]` (vazio em pedidos antigos)                                                                                                                                                  |
| GET    | `desarquivamento/{idSolicitacao}/ultimo-evento`                                     | string com a descrição; 500 em pedidos legados — ignorar                                                                                                                                                                               |
| GET    | `desarquivamento/comprovante/{idSolicitacao}`                                       | data URL do PDF de gratuidade                                                                                                                                                                                                          |
| GET    | `link/open-links?id={idSolicitacao}`                                                | `[{descricao, url, token}]` — links de download dos autos digitalizados                                                                                                                                                                |
| POST   | `desarquivamento/anexar-procuracao`                                                 | `{id, procuracao}`                                                                                                                                                                                                                     |
| PUT    | `desarquivamento/estadoGuia`                                                        | `{id, estado, procuracao, descricaoEvento, telefone, email}` — correção após "Recusado para Correção" **[não verificado]**                                                                                                             |

`andamento`: `pendentes`, `solicitados` (concluídos), vazio = todos. `modo`: `Físico` / `Digitalizado`.

## 3. Fluxo em lote

1. Entrada: lista de números (texto, CSV, planilha). Normalizar para só dígitos.
2. Pedir uma vez: telefone, modo (padrão Digitalizado), e qual pedido anterior fornece o comprovante (ou um PDF novo).
3. Pré-voo (só GETs): para cada número, `existeSolicitacao` + `processo/numero`. Tabela para o usuário: número, encontrado?, registros (duplicidade), vara, ação, partes, caixa, já existe pedido?
4. Esperar confirmação explícita do lote. Criar solicitação é ato com efeito externo.
5. Registrar **cada volume autorizado** no arquivo `selecionados.tsv` (`numero<TAB>idProcesso`), uma linha por volume, na ordem escolhida. Não inferir seleção a partir de `.[0]`; não incluir registros não autorizados nem IDs repetidos.
6. Executar `FASE=primeiro` para **uma única tentativa**. Qualquer falha HTTP ou de transporte deixa o resultado **indeterminado** até reconciliação. HTTP 2xx não confirma a criação: não continuar automaticamente. A tentativa cria um registro de intenção local antes do POST.
7. Conferir manualmente a solicitação criada (id da solicitação, processo, volume/`idProcesso`, status, natureza e ausência de duplicidade) em **todas as páginas** da busca ou no detalhe. Criar `VALIDACAO_JSON` local com `confirmado_por_usuario:true`, `numero`, `idProcesso`, `idSolicitacao`, `verificado_em`, `status_confirmado`; apenas depois executar `FASE=restante VALIDACAO_JSON=...`. Nunca versionar este registro com dados de processos.
8. Na fase restante, executar **uma linha por chamada supervisionada**, registrando a conferência individual e avançando o cursor de forma explícita; jamais reenviar linha já tentada. Relatório por volume selecionado: processo, `idProcesso`, volume, resultado (criada / já existia / não encontrado / erro HTTP + `mensagem`). O arquivo de seleção deve refletir o pré-voo já aprovado; não usar resultado novo da API para ampliar o lote.
6. Relatório: processo, vara, resultado (criada / já existia / não encontrado / erro HTTP + `mensagem`).

```bash
# selecionados.tsv: numero<TAB>idProcesso, somente volumes autorizados.
# Esta é uma referência de execução supervisionada, NÃO um worker autônomo.
set -euo pipefail
: "${TELEFONE:?Obrigatório}"
: "${ID_BASE:?Pedido-base autorizado obrigatório}"
: "${DESARQ_RT:?Sessão do usuário obrigatória}"
: "${API:=https://desarquivamento-back.tjro.jus.br/back}"
: "${FASE:=primeiro}"
[[ "$FASE" == primeiro || "$FASE" == restante ]] || exit 1
[[ -s selecionados.tsv ]] || exit 1
awk -F '\t' 'NF!=2 || $1 !~ /^[0-9]+$/ || $2 !~ /^[0-9]+$/ || seen[$1 FS $2]++ {exit 1}' selecionados.tsv
if [[ "$FASE" == restante ]]; then
  # Não confiar em flag livre. Registro criado SOMENTE depois da conferência
  # humana do pedido real, armazenado localmente, fora de Git.
  : "${VALIDACAO_JSON:?Informe arquivo de conferência do primeiro pedido}"
  python3 - "$VALIDACAO_JSON" selecionados.tsv <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
first = Path(sys.argv[2]).read_text().splitlines()[0].split("\t")
assert data.get("confirmado_por_usuario") is True
assert data.get("numero") == first[0] and str(data.get("idProcesso")) == first[1]
assert isinstance(data.get("idSolicitacao"), int) and data["idSolicitacao"] > 0
assert data.get("verificado_em") and data.get("status_confirmado")
PY
fi
desarq_token
ME=$(curl -fsS "${H[@]}" "$API/api/usuarios/me")
PDF=$(curl -fsS "${H[@]}" "$API/desarquivamento/comprovante/$ID_BASE")
[[ "$PDF" == data:application/pdf\;base64,* ]] || exit 1
MODO=${MODO:-Digitalizado}
[[ "$MODO" == Digitalizado || "$MODO" == Físico ]] || exit 1
# O primeiro volume nunca é reenviado na fase restante.
if [[ "$FASE" == primeiro ]]; then linhas=$(head -n 1 selecionados.tsv)
else linhas=$(tail -n +2 selecionados.tsv); fi
while IFS=$'\t' read -r n pid; do
  [[ -n "$n" ]] || continue
  desarq_token
  # Procurar em TODAS as páginas de TODOS os pedidos, e não só nos 100 pendentes.
  # Em qualquer falha/ambiguidade, bloquear o POST.
  export NUMERO_ALVO="$n" ID_ALVO="$pid"
  pagina=0; encontrados=0
  while :; do
    result=$(curl -fsS "${H[@]}" "$API/desarquivamento/busca?page=$pagina&size=100") || exit 1
    qtd=$(jq -er '.content | length' <<<"$result") || exit 1
    match=$(jq -er --arg n "$n" --argjson id "$pid"       '[.content[] | select((.numeroProcesso|tostring)==$n and (.idProcesso|tostring)==($id|tostring))] | length' <<<"$result") || exit 1
    encontrados=$((encontrados + match))
    total=$(jq -er '.page.totalPages' <<<"$result") || exit 1
    pagina=$((pagina + 1))
    (( pagina < total )) || break
  done
  if (( encontrados > 0 )); then
    echo "$n;$pid;JA_EXISTE;sem POST"; continue
  fi
  # Por segurança, a consulta por número pode agregar múltiplos volumes.
  existe=$(curl -fsS "${H[@]}" "$API/guia/existeSolicitacao/$n") || exit 1
  if [[ "$existe" != false ]]; then
    echo "$n;$pid;BLOQUEADO_POR_NUMERO" >&2; exit 1
  fi
  P=$(curl -fsS "${H[@]}" "$API/processo/numero/$n") || exit 1
  p=$(jq -ce --arg id "$pid" '[.[] | select((.id|tostring)==$id)] | if length==1 then .[0] else error("volume ausente ou ambíguo") end' <<<"$P") || exit 1
  body=$(jq -n --argjson me "$ME" --argjson p "$p" --arg n "$n" --arg tel "$TELEFONE"     --arg modo "$MODO" --arg pdf "$PDF" '{
      login:$me.login, cpfCNPJ:$me.cpfCNPJ, tipoSolicitante:$me.origemAutenticacao,
      solicitante:$me.nome, pagador:$me.nome, email:$me.email, telefone:$tel,
      valor:0, pessoaEncontrada:true, tipo:$modo, idProcesso:$p.id,
      numeroProcesso:$n, natureza:($p.destino // ""), pdf_gratuidade:$pdf, pdf_procuracao:""}')
  # Gravar intenção ANTES da operação com efeito externo. Se cair após POST,
  # bloquear reenvio até reconciliação manual (inclusive POST com HTTP 500).
  mkdir -p .desarq-local; chmod 700 .desarq-local
  intent=".desarq-local/${n}_${pid}.intent"
  if [[ -e "$intent" ]]; then
    echo "$n;$pid;RESULTADO_INDETERMINADO_OU_JA_TENTADO;reconciliar" >&2; exit 1
  fi
  (umask 077; printf 'POST_POSSIVEL numero=%s idProcesso=%s\n' "$n" "$pid" > "$intent")
  resp=$(mktemp); trap 'rm -f "$resp"' EXIT
  code=$(curl --max-time 60 -sS -o "$resp" -w '%{http_code}' "${H[@]}"     -X POST "$API/guia/guiadispensada" --data-binary "$body") || {
      echo "$n;$pid;INDETERMINADO;reconciliar sem repetir POST" >&2; exit 1;
    }
  if [[ ! "$code" =~ ^2[0-9][0-9]$ ]]; then
    echo "$n;$pid;HTTP_$code;reconciliar sem repetir POST" >&2; exit 1
  fi
  # Não confundir sucesso HTTP com criação comprovada.
  echo "$n;$pid;POST_2XX;CONFERENCIA_OBRIGATORIA"
  # Não há reenvio ou passagem automática ao próximo volume sem conferir
  # o ID da solicitação no DESARQ e registrar evidência.
  exit 0
done <<<"$linhas"
```

**Aviso operacional:** a fase `restante` acima é deliberadamente fail-closed: encerra após uma tentativa. Para enviar a linha seguinte é necessário mecanismo de cursor persistente e reconciliação; NÃO repetir o comando sem confirmar qual linha foi efetivamente processada. A pasta `.desarq-local/` é privada e deve entrar no `.gitignore`; em ambientes efêmeros o operador deve preservar o estado fora do contêiner.\n\n## 4. Onde rodar

- Com o Jatobá disponível: Opção A em `mcp__jatoba__bash` (`curl`, `jq`).
- Sem shell: Opção B, mesma sequência via `fetch` na aba logada.

## 5. Erros

| Sintoma                        | Causa                                                 | Ação                                          |
| ------------------------------ | ----------------------------------------------------- | --------------------------------------------- |
| 401                            | access token expirou                                  | `desarq_token` / recapturar                   |
| `invalid_grant`                | sessão SSO expirou                                    | novo login                                    |
| `processo/numero` vazio ou 404 | fora do acervo do arquivo, ou número diferente        | tentar o número antigo (14 dígitos); reportar |
| `existeSolicitacao` = true     | já há pedido do usuário em andamento                  | pular e reportar                              |
| `desarquivamento/{x}` 204      | passou número do processo em vez do id da solicitação | usar `id` da busca                            |
| `ultimo-evento` 500            | pedido legado                                         | usar `desarquivamento/{id}`                   |
| 4xx no `guiadispensada`        | campo faltando ou PDF acima de 1,5 MB                 | ler `mensagem`                                |
| Front devolve resposta vazia   | WAF TSPD                                              | usar só o host `-back`                        |

## 6. Limites

- Não pagar boletos nem usar `guia/gerar` sem pedido expresso.
- Não automatizar login nem contornar o WAF.
- Confirmação do usuário antes de cada lote; listas vindas de terceiros só com validação dele.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
