---
name: jus-br
description: >-
  Acesso autenticado ao portal unificado da Justiça Brasileira (www.jus.br / PDPJ-Br)
  e serviços do CNJ (ComunicaAPI, Consulta Processual Unificada e Peticionamento).
  Suporta autenticação federada gov.br/Certificado Digital via Keycloak com PKCE S256,
  armazenamento seguro no Windows Credential Manager (com chunking WinVault),
  renovação automática via refresh token e CLI rica para consultas e peticionamento.
compatibility: >-
  Requires Python 3.12+ with PEP 723 script metadata. Compatible with Windows 11
  Credential Manager (WinVaultKeyring), macOS Keychain and Linux SecretService.
  Dependencies managed via `uv run`.
---

# Jus.br / PDPJ-Br — Acesso Unificado à Justiça Brasileira

Esta skill implementa o cliente e a CLI de integração com a **Plataforma Digital do Poder Judiciário (PDPJ-Br)** e o portal unificado **Jus.br** (`https://www.jus.br`), mantido pelo Conselho Nacional de Justiça (CNJ).

Ela permite que agentes operem serviços judiciais de forma segura e auditável:
1. **Comunicações Processuais Oficiais**: Consulta em tempo real na ComunicaAPI (`https://comunicaapi.pje.jus.br`).
2. **Consulta Processual Unificada**: Dados de processos distribuídos em tribunais integrados à PDPJ.
3. **Peticionamento Eletrônico Intercorrente**: Protocolo unificado de petições e documentos.

---

## 1. Arquitetura de Autenticação Segura

### Federação OIDC com PKCE S256
A autenticação utiliza o Keycloak oficial da PDPJ/PJe:
- **Realm Base**: `https://sso.cloud.pje.jus.br/auth/realms/pje`
- **Authorization Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth`
- **Token Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/token`
- **Client ID**: `jusbr` (cliente público OIDC, sem segredo de cliente)
- **Método PKCE**: `S256` (code_verifier de 64 bytes com hash SHA-256 base64url)

### Restrição de Callback e Fluxo Assistido
O cliente público `jusbr` do CNJ tem sua lista de `redirect_uris` restrita a `https://www.jus.br/*` (rejeitando `localhost` ou `127.0.0.1` com HTTP 400).

Para garantir segurança total sem depender de Playwright, scraping ou interceptação indevida de senhas:
1. O comando `jusbr auth login` gera o par PKCE (`code_verifier` e `code_challenge`) e um token anti-CSRF (`state`).
2. Abre o navegador padrão do usuário na URL de autorização oficial do CNJ.
3. O usuário realiza a autenticação com **Gov.br** (ouro/prata) ou **Certificado Digital (ICP-Brasil)**, incluindo qualquer MFA exigido diretamente nos servidores do governo.
4. Ao concluir, o Keycloak redireciona o navegador para `https://www.jus.br/callback?code=...&state=...` (evitando o script de recarregamento da raiz).
5. O usuário copia a URL final da barra de endereços e a insere no prompt da CLI.
6. A CLI valida o parâmetro `state`, extrai o `authorization_code` e realiza a troca direta com o Token Endpoint via TLS, obtendo `access_token` e `refresh_token`.

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

Submete petição intermediária ao barramento da PDPJ ([Documentação Oficial de Petição Intercorrente da PDPJ-Br](https://docs.pdpj.jus.br/servicos-negociais/portal-servicos/pet-intercorrente/)):

```powershell
# Submeter petição intercorrente ao barramento da PDPJ
uv run jus-br/cli.py peticionamento intercorrente `
  --processo "7001234-56.2024.8.22.0001" `
  --tribunal "TJRO" `
  --tipo "Manifestação" `
  --descricao "Manifestação sobre laudo pericial" `
  --arquivo "minutas/2026-10-21-manifestacao.pdf"
```

> **Aviso de Fluxo Assíncrono:** O protocolo gerado na submissão atesta o acolhimento da peça pelo barramento do CNJ. A juntada definitiva aos autos depende do processamento assíncrono pelo tribunal de destino (confirmação ou recusa).

---

## 3. Diretrizes de Segurança e Confiabilidade Forense

1. **Tolerância Zero a Dados Fictícios:** O cliente e a CLI **nunca simulam** recibos de protocolo, números de protocolo ou dados processuais. Falhas de conexão, indisponibilidade de serviço ou rejeições de barramento propagam `JusBrApiError` imediatamente. Recibo de protocolo é estritamente o retornado pelo barramento oficial, sem valores padrão pré-assumidos (`status` obrigatório).
2. **Nunca Expor Credenciais:** Não faça log, print ou commit de `access_token`, `refresh_token`, `authorization_code` ou `code_verifier`.
3. **Validação Estrita de Callback:** O authorization code só é aceito se fornecida uma URL HTTPS completa iniciando por `https://www.jus.br/callback` (ou `jus.br`), com `state` obrigatório e idêntico ao gerado para a sessão. Fragmentos de query avulsos ou códigos isolados sem validação CSRF são sumariamente rejeitados.
4. **Integridade de Peças com SHA-256:** Todas as requisições de peticionamento calculam o hash SHA-256 local do arquivo PDF antes do envio, registrando a impressão digital da peça para auditoria e confronto com o recibo de juntada emitido pelo tribunal.
5. **Atualização Transacional com Gerações Imutáveis no Keyring:** A persistência de tokens no Windows Credential Manager cria uma nova geração isolada de chunks para cada sessão. A comutação de ponteiro (`active_gen`) é atômica; caso ocorra falha durante a escrita dos novos chunks, a geração antiga permanece 100% intocada.
6. **Tratamento de 401 Unauthorized:** O `JusBrClient` tenta renovar o token automaticamente via refresh token uma vez ao encontrar erro HTTP 401. Caso a sessão esteja revogada remotamente, orienta a execução de `jusbr auth login`.
