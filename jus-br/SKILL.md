---
name: jus-br
description: >-
  Autenticação OIDC com PKCE para o SSO CNJ e consulta documentada à ComunicaAPI.
  Consulta processual direta e peticionamento por API permanecem experimentais e desabilitados.
  Implementa uma configuração candidata de autenticação federada via Keycloak com PKCE S256,
  armazenamento seguro no keyring e consulta de comunicações. Endpoints não confirmados
  ficam desabilitados; login real e cliente OIDC ainda dependem de validação end-to-end.
compatibility: >-
  Requires Python 3.11+ with PEP 723 script metadata. Intended for Windows
  Credential Manager (WinVaultKeyring), macOS Keychain and Linux SecretService.
  Dependencies managed via `uv run`.
---

# Jus.br / PDPJ-Br — Acesso Unificado à Justiça Brasileira

Esta skill implementa o cliente e a CLI de integração com a **Plataforma Digital do Poder Judiciário (PDPJ-Br)** e o portal unificado **Jus.br** (`https://www.jus.br`), mantido pelo Conselho Nacional de Justiça (CNJ).

Ela permite autenticar via SSO CNJ e consultar comunicações na ComunicaAPI. A consulta processual direta
e o peticionamento por API não são oferecidos operacionalmente enquanto seus contratos, permissões e
ambientes não forem confirmados. Nenhuma dessas operações é simulada.

## Estado de suporte e contratos

| Recurso | Estado | Evidência/limite |
| --- | --- | --- |
| SSO CNJ / token OIDC | Implementação candidata; testes simulados | A implementação usa endpoints de Keycloak no realm CNJ e cliente `jusbr`. A configuração do cliente, callback autorizado e login real não foram confirmados end-to-end nesta revisão. |
| ComunicaAPI | Implementado como leitura | O CNJ publica orientações de integração e bases distintas de homologação e produção. Consultas podem ser públicas; o CLI não exige nem envia token automaticamente. |
| Consulta processual via `api.pdpj.jus.br/processos/{numero}` | Experimental e desabilitada | A URL usada anteriormente não foi localizada em contrato oficial. O serviço documentado de Cabeçalho Processual tem Swagger e contrato próprios; esta CLI ainda não os implementa. |
| Petição intercorrente via `api.pdpj.jus.br/peticionamento/intercorrente` | Experimental e desabilitada | A documentação oficial descreve o Portal de Serviços, Swagger de homologação e callbacks assíncronos. Ela não comprova o path anterior. Nenhum documento é transmitido e nenhum recibo é criado. |

Referências oficiais verificadas: [orientações do CNJ para integração das APIs de Comunicações Processuais](https://www.cnj.jus.br/programas-e-acoes/processo-judicial-eletronico-pje/comunicacoes-processuais/orientacoes-aos-tribunais/), [Petição Intercorrente na PDPJ-Br](https://docs.pdpj.jus.br/servicos-negociais/portal-servicos/pet-intercorrente/) e [notas do Cabeçalho Processual](https://docs.pdpj.jus.br/servicos-estruturantes/release-notes/cabecalho-processual/). A documentação de peticionamento aponta para o Swagger do Portal em homologação (`portalexterno-tribunais.stg.pdpj.jus.br/swagger-ui.html`) e para callbacks de resultado do tribunal.

---

## 1. Arquitetura de Autenticação Segura

### Federação OIDC com PKCE S256
A autenticação utiliza o Keycloak oficial da PDPJ/PJe:
- **Realm Base**: `https://sso.cloud.pje.jus.br/auth/realms/pje`
- **Authorization Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth`
- **Token Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/token`
- **Client ID**: `jusbr` (cliente público OIDC, sem segredo de cliente)
- **Método PKCE**: `S256` (code_verifier de 64 bytes com hash SHA-256 base64url)

### Callback e fluxo assistido candidato
O fluxo implementado assume que o cliente público `jusbr` aceita `https://www.jus.br/callback`. A configuração oficial do cliente e seu cadastro de `redirect_uri` precisam de confirmação antes de tratar o login como integração validada.

O fluxo proposto evita Playwright, scraping e coleta de senha pelo agente. Ainda não foi validado end-to-end:
1. O comando `jusbr auth login` gera o par PKCE (`code_verifier` e `code_challenge`) e um token anti-CSRF (`state`).
2. Abre o navegador padrão do usuário na URL de autorização oficial do CNJ.
3. O usuário realiza a autenticação com **Gov.br** (ouro/prata) ou **Certificado Digital (ICP-Brasil)**, incluindo qualquer MFA exigido diretamente nos servidores do governo.
4. Ao concluir, o Keycloak deve redirecionar para `https://www.jus.br/callback?code=...&state=...` (evitando o script de recarregamento da raiz).
5. O usuário copia a URL final da barra de endereços e a insere no prompt da CLI.
6. A CLI valida o parâmetro `state` e tenta trocar o `authorization_code` no Token Endpoint via TLS. O sucesso depende da confirmação do cliente OIDC e do callback cadastrados no provedor.

### Armazenamento Protegido (Windows Credential Manager / Keyring)
- Os tokens nunca são gravados em arquivos de texto plano ou variáveis de ambiente.
- O armazenamento utiliza o cofre de credenciais do sistema operacional (`keyring`).
- **Suporte a Chunking no Windows (WinVaultKeyring)**: Para superar a limitação de 512 bytes da API Win32 `CredWriteW` (código de erro 1783), o módulo `credentials.py` divide os tokens em blocos transparentes (`chunk_0`, `chunk_1`, ...), preservando compatibilidade nativa sem corrupção.

### Renovação Autônoma (Refresh Token)
Uma vez autenticado, o agente renova o `access_token` silenciosamente chamando o Token Endpoint com `grant_type=refresh_token`, garantindo operação contínua sem necessidade de novo login interativo até a expiração da sessão do usuário.

---

## 2. Comandos da CLI (`jus-br/cli.py`)

A CLI é executável diretamente com `uv run` utilizando metadados PEP 723:

```powershell
uv run jus-br/cli.py --help
```

### Autenticação (`auth`)

```powershell
# Iniciar login interativo via Gov.br / CNJ SSO
uv run jus-br/cli.py auth login

# Verificar status da sessão e validade dos tokens
uv run jus-br/cli.py auth status

# Forçar renovação do access token via refresh token
uv run jus-br/cli.py auth refresh

# Encerrar sessão e remover tokens do cofre seguro
uv run jus-br/cli.py auth logout
```

### Dados do Usuário (`usuario`)

```powershell
# Obter perfil, CPF, nome e papeis do usuário autenticado
uv run jus-br/cli.py usuario obter
```

### Consulta de Comunicações (`comunicacoes`)

Consulta a **ComunicaAPI** do CNJ para obter publicações de diários de justiça e intimações eletrônicas:

```powershell
# Buscar comunicações por tribunal (ex: TJRO, TJRS, TJSP, TRF1)
uv run jus-br/cli.py comunicacoes buscar --tribunal TJRO --itens 10

# Buscar publicações de um número de processo específico
uv run jus-br/cli.py comunicacoes buscar --processo 7001234-56.2024.8.22.0001

# Filtrar por data de disponibilização
uv run jus-br/cli.py comunicacoes buscar --tribunal TJRO --data 2026-10-20
```

### Consulta Processual (`processo`)

```powershell
# Consultar metadados básicos de um processo na PDPJ
uv run jus-br/cli.py processo consultar 7001234-56.2024.8.22.0001
```

### Peticionamento Intercorrente (`peticionamento`)

**Não disponível para transmissão por esta skill.** O comando abaixo permanece apenas como aviso de compatibilidade e encerra com código 2. Ele não lê o arquivo, não autentica, não envia requisições e não produz protocolo. A documentação oficial descreve o serviço Portal de Serviços e seu Swagger de homologação, mas não confirma o endpoint REST que havia sido usado nesta implementação.

```powershell
# Submeter petição intercorrente ao barramento da PDPJ
uv run jus-br/cli.py peticionamento intercorrente `
  --processo "7001234-56.2024.8.22.0001" `
  --tribunal "TJRO" `
  --tipo "Manifestação" `
  --descricao "Manifestação sobre laudo pericial" `
  --arquivo "minutas/2026-10-21-manifestacao.pdf"
```

Use o Portal de Serviços oficial do CNJ para protocolar. Quando o contrato oficial for implementado, a resposta de recebimento do Portal e a confirmação ou recusa assíncrona do tribunal deverão ser representadas como estados distintos.

---

## 3. Diretrizes de Segurança e Confiabilidade Forense

1. **Contratos de resposta explícitos:** A resposta de token exige `access_token`, `token_type` e `expires_in` válido; a resposta da ComunicaAPI exige `status=success`, `count` e `items`. JSON incompleto ou com status de erro não vira sessão ou lista vazia.
2. **Tolerância Zero a Dados Fictícios:** O cliente e a CLI nunca simulam recibos, números de protocolo ou dados processuais. Consulta de processo e peticionamento por API lançam `ExperimentalServiceUnavailableError` antes de autenticar ou fazer rede.
3. **Nunca Expor Credenciais:** Não faça log, print ou commit de `access_token`, `refresh_token`, `authorization_code` ou `code_verifier`.
4. **Validação Estrita de Callback:** Só aceita URL absoluta HTTPS em `www.jus.br/callback`, com `state` e `code` únicos, sem fragmento, e `state` idêntico ao da sessão.
5. **Hash local:** Nenhuma verificação ponta a ponta de integridade de documentos é anunciada ou realizada. SHA-256 local apenas identifica bytes locais, salvo confirmação por contrato remoto.
6. **Persistência no Keyring:** Tokens são escritos e lidos de volta numa geração isolada antes de atualizar o ponteiro ativo. Em falha de persistência, o erro é reportado; se o estado do ponteiro for incerto, dados candidatos são preservados para evitar destruir a única sessão válida. Chunks têm no máximo 512 bytes UTF-8.
7. **Renovação:** Quando a resposta de refresh não rotacionar `refresh_token`, a credencial anterior é mantida. A atualização em keyring só ocorre depois de validar a nova geração.
8. **Tratamento de 401 Unauthorized:** O cliente tenta renovar uma vez após 401. Se a sessão estiver revogada, orienta novo login.
9. **Logout:** A remoção local é validada e pode falhar com erro explícito. O comando só informa revogação remota confirmada para HTTP 200/204; em outro caso informa que não houve confirmação remota.
