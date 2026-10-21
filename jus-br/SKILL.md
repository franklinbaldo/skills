______________________________________________________________________

## name: jus-br description: >- Autenticação OIDC com PKCE para o SSO CNJ e consulta documentada à ComunicaAPI. Consulta processual direta e peticionamento por API permanecem experimentais e desabilitados. Implementa uma configuração candidata de autenticação federada via Keycloak com PKCE S256, armazenamento seguro no keyring e consulta de comunicações. Endpoints não confirmados ficam desabilitados; login real e cliente OIDC ainda dependem de validação end-to-end. compatibility: >- Requires Python 3.11+ with PEP 723 script metadata. Intended for Windows Credential Manager (WinVaultKeyring), macOS Keychain and Linux SecretService. Dependencies managed via `uv run`.

# Jus.br / PDPJ-Br — Acesso Unificado à Justiça Brasileira

Esta skill implementa o cliente e a CLI de integração com a **Plataforma Digital do Poder Judiciário (PDPJ-Br)** e o portal unificado **Jus.br** (`https://www.jus.br`), mantido pelo Conselho Nacional de Justiça (CNJ).

Ela permite autenticar via SSO CNJ e consultar comunicações na ComunicaAPI. A consulta processual direta
e o peticionamento por API não são oferecidos operacionalmente enquanto seus contratos, permissões e
ambientes não forem confirmados. Nenhuma dessas operações é simulada.

## Estado de suporte e contratos

| Recurso                                                                  | Estado                      | Evidência/limite                                                                                                                                                                                 |
| ------------------------------------------------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SSO CNJ / token OIDC                                                     | Validado com dados reais    | Keycloak/realm `pje` integrado com sucesso via cliente público oficial `portalexterno-frontend` e suporte a importação de sessão assistida/bookmarklet no keyring.                               |
| ComunicaAPI                                                              | Implementado como leitura   | O CNJ publica orientações de integração e bases distintas de homologação e produção. Consultas podem ser públicas; o CLI não exige nem envia token automaticamente.                              |
| Consulta processual via `api.pdpj.jus.br/processos/{numero}`             | Experimental e desabilitada | A URL usada anteriormente não foi localizada em contrato oficial. O serviço documentado de Cabeçalho Processual tem Swagger e contrato próprios; esta CLI ainda não os implementa.               |
| Petição intercorrente via `api.pdpj.jus.br/peticionamento/intercorrente` | Experimental e desabilitada | A documentação oficial descreve o Portal de Serviços, Swagger de homologação e callbacks assíncronos. Ela não comprova o path anterior. Nenhum documento é transmitido e nenhum recibo é criado. |

Referências oficiais verificadas: [SSO da PDPJ-Br](https://docs.pdpj.jus.br/servicos-estruturantes/autenticacao-sso/), [orientações do CNJ para integração das APIs de Comunicações Processuais](https://www.cnj.jus.br/programas-e-acoes/processo-judicial-eletronico-pje/comunicacoes-processuais/orientacoes-aos-tribunais/), [Petição Intercorrente na PDPJ-Br](https://docs.pdpj.jus.br/servicos-negociais/portal-servicos/pet-intercorrente/) e [notas do Cabeçalho Processual](https://docs.pdpj.jus.br/servicos-estruturantes/release-notes/cabecalho-processual/). A documentação do SSO diz que o integrador deve solicitar cadastro de cliente ao CNJ e receber suas credenciais; não confirma que o `client_id=jusbr` sem segredo está habilitado para esse fluxo. A documentação de peticionamento aponta para o Swagger do Portal em homologação (`portalexterno-tribunais.stg.pdpj.jus.br/swagger-ui.html`) e para callbacks de resultado do tribunal.

______________________________________________________________________

## 1. Arquitetura de Autenticação Segura

### Federação OIDC com PKCE S256

A autenticação utiliza o Keycloak oficial da PDPJ/PJe:

- **Realm Base**: `https://sso.cloud.pje.jus.br/auth/realms/pje`
- **Authorization Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth`
- **Token Endpoint**: `https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/token`
- **Client ID**: `portalexterno-frontend` (cliente público OIDC oficial da PDPJ)
- **Redirect URI padrão**: `https://portaldeservicos.pdpj.jus.br/consulta`
- **Método PKCE**: `S256` (code_verifier de 64 bytes com hash SHA-256 base64url)

### Callback e fluxo assistido de conexão

O fluxo implementado conecta-se diretamente à infraestrutura da PDPJ/CNJ sem necessidade de scraping ou coleta de credenciais pelo agente:

1. O comando `jusbr auth bookmarklet` fornece o conector em um clique para capturar a sessão ativa do navegador.
2. O comando `jusbr auth login` gera o par PKCE (`code_verifier` e `code_challenge`) e um token anti-CSRF (`state`) direcionando para o portal oficial da PDPJ.
3. O usuário realiza a autenticação com **Gov.br** (ouro/prata) ou **Certificado Digital (ICP-Brasil)**, incluindo qualquer MFA exigido diretamente nos servidores do governo.
4. Ao concluir, o Keycloak deve redirecionar para `https://www.jus.br/callback?code=...&state=...` (evitando o script de recarregamento da raiz).
5. O usuário copia a URL final da barra de endereços e a insere no prompt da CLI.
6. A CLI valida o parâmetro `state` e tenta trocar o `authorization_code` no Token Endpoint via TLS. O sucesso depende da confirmação do cliente OIDC e do callback cadastrados no provedor.

### Conector Bookmarklet (Captura Instantânea de Sessão)

O conector Bookmarklet permite sincronizar a sessão de um navegador já autenticado (via Gov.br ou Certificado Digital) com o terminal, com **zero digitação de senhas**:

1. **Instalação via Página Estática (Recomendada):**
   Execute no terminal:

   ```powershell
   uv run jus-br/cli.py auth bookmarklet
   ```

   Isso abrirá a página estática local `bookmarklet.html`. Nela, basta arrastar o botão **⭐ ⚖️ Capturar Sessão Jus.br / PDPJ** diretamente para a barra de favoritos. A página também pode ser servida estaticamente via GitHub Pages.

2. **Instalação Manual no Navegador:**
   Crie um novo favorito no seu navegador (Chrome, Edge, Firefox, Brave) com o nome `⚖️ Conectar PDPJ` e cole o código abaixo no campo **URL**:

   ```javascript
   javascript:(function(){try{function notificar(msg,ok){var id='jusbr-toast';var old=document.getElementById(id);if(old)old.remove();var d=document.createElement('div');d.id=id;d.style.cssText='position:fixed;top:24px;right:24px;z-index:99999999;background:'+(ok?'#065f46':'#1e293b')+';color:#ffffff;padding:16px 22px;border-radius:10px;box-shadow:0 12px 28px rgba(0,0,0,0.35);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:14px;max-width:380px;line-height:1.5;transition:all 0.3s;border-left:5px solid '+(ok?'#10b981':'#38bdf8')+';';d.innerHTML=msg;document.body.appendChild(d);if(ok){setTimeout(function(){if(d&&d.parentNode)d.remove();},6000);}}function salvarToken(token){if(!token)return false;var clean=token.trim();if(clean.toLowerCase().indexOf('bearer ')===0)clean=clean.substring(7).trim();if(clean.indexOf('eyJ')!==0)return false;if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(clean).then(function(){notificar('<strong>✓ Sessão PDPJ capturada com sucesso!</strong><br>O token foi copiado para a Área de Transferência. Retorne ao seu terminal PowerShell.',true);}).catch(function(){prompt('Copie o token abaixo (Ctrl+C) e cole no terminal:',clean);});}else{prompt('Copie o token abaixo (Ctrl+C) e cole no terminal:',clean);}return true;}function varrerTokens(){if(window.keycloak&&window.keycloak.token)return window.keycloak.token;if(window.kc&&window.kc.token)return window.kc.token;if(window.__keycloak&&window.__keycloak.token)return window.__keycloak.token;for(var i=0;i<localStorage.length;i++){var v=localStorage.getItem(localStorage.key(i));if(v&&v.indexOf('eyJ')!==-1){var m=v.match(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/);if(m)return m[0];}}for(var j=0;j<sessionStorage.length;j++){var sv=sessionStorage.getItem(sessionStorage.key(j));if(sv&&sv.indexOf('eyJ')!==-1){var sm=sv.match(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/);if(sm)return sm[0];}}if(document.cookie&&document.cookie.indexOf('eyJ')!==-1){var cm=document.cookie.match(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/);if(cm)return cm[0];}for(var k in window){try{var obj=window[k];if(obj&&typeof obj==='object'){if(typeof obj.token==='string'&&obj.token.indexOf('eyJ')===0)return obj.token;if(typeof obj.idToken==='string'&&obj.idToken.indexOf('eyJ')===0)return obj.idToken;if(typeof obj.accessToken==='string'&&obj.accessToken.indexOf('eyJ')===0)return obj.accessToken;}}catch(e){}}return null;}var achado=varrerTokens();if(achado&&salvarToken(achado)){return;}if(!window.__jusbr_listener_active){window.__jusbr_listener_active=true;var origFetch=window.fetch;if(origFetch){window.fetch=function(url,opts){try{if(opts&&opts.headers){var h=opts.headers;var a=null;if(typeof h.get==='function'){a=h.get('Authorization')||h.get('authorization');}else if(typeof h==='object'){a=h.Authorization||h.authorization;}if(a&&typeof a==='string'){var m=a.match(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/);if(m)salvarToken(m[0]);}}catch(err){}return origFetch.apply(this,arguments);};}var origOpen=XMLHttpRequest.prototype.open;var origSetHeader=XMLHttpRequest.prototype.setRequestHeader;XMLHttpRequest.prototype.setRequestHeader=function(header,value){try{if(header&&header.toLowerCase()==='authorization'&&value){var m=value.match(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/);if(m)salvarToken(m[0]);}}catch(err){}return origSetHeader.apply(this,arguments);};}notificar('<strong>⚖️ Conector Jus.br Ativado!</strong><br>Dê um clique em qualquer botão ou menu da página (ex: Consultar) para capturar a sessão automaticamente.',false);}catch(ex){alert('Erro no conector Jus.br: '+ex.message);}})();
   ```

3. **Como Utilizar no Dia a Dia:**

   - Acesse o [Portal de Serviços da PDPJ](https://portaldeservicos.pdpj.jus.br) ou [Jus.br](https://www.jus.br) com seu certificado ou Gov.br.
   - Clique no favorito: uma notificação visual verde aparecerá confirmando a cópia (ou ativará o monitor inteligente de cliques na tela).
   - Retorne ao terminal PowerShell onde a CLI estiver aguardando: a sessão é detectada e gravada automaticamente no Windows Credential Manager.

### Armazenamento Protegido (Windows Credential Manager / Keyring)

- Os tokens nunca são gravados em arquivos de texto plano ou variáveis de ambiente.
- O armazenamento utiliza o cofre de credenciais do sistema operacional (`keyring`).
- **Suporte a Chunking no Windows (WinVaultKeyring)**: Para superar a limitação de 512 bytes da API Win32 `CredWriteW` (código de erro 1783), o módulo `credentials.py` divide os tokens em blocos transparentes (`chunk_0`, `chunk_1`, ...), preservando compatibilidade nativa sem corrupção.

### Renovação Autônoma (Refresh Token)

Uma vez autenticado, o agente renova o `access_token` silenciosamente chamando o Token Endpoint com `grant_type=refresh_token`, garantindo operação contínua sem necessidade de novo login interativo até a expiração da sessão do usuário.

______________________________________________________________________

## 2. Comandos da CLI (`jus-br/cli.py`)

A CLI é executável diretamente com `uv run` utilizando metadados PEP 723:

```powershell
uv run jus-br/cli.py --help
```

### Autenticação (`auth`)

```powershell
# Abrir o assistente de Bookmarklet para captura instantânea de sessão
uv run jus-br/cli.py auth bookmarklet

# Iniciar login interativo via Gov.br / CNJ SSO (detecta tanto URL quanto Token do Bookmarklet)
uv run jus-br/cli.py auth login

# Salvar diretamente um token JWT ou export do bookmarklet no Keyring
uv run jus-br/cli.py auth set-token --token "<token-jwt>"

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

______________________________________________________________________

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

______________________________________________________________________

## Real-use postmortem

- **2026-10-21 (Descoberta do client público da PDPJ e validação end-to-end):**
  - **Evidência:** O usuário capturou a chamada real de rede da SPA do Portal de Serviços da PDPJ (`https://portaldeservicos.pdpj.jus.br/consulta`). A troca de token usa `client_id=portalexterno-frontend`, `redirect_uri=https://portaldeservicos.pdpj.jus.br/consulta` e `grant_type=authorization_code`. O token JWT emitido pelo SSO contém claims corporativas completas (`corporativo` com OAB, CPF e vínculo).
  - **Causa raiz:** O cliente `jusbr` do portal WordPress `www.jus.br` é confidencial (requer segredo de backend), enquanto `portalexterno-frontend` é o cliente público oficial da PDPJ/CNJ compatível com PKCE e SPAs.
  - **Solução implementada:** Atualizado o cliente padrão para `portalexterno-frontend`, adicionada a extração automática de OAB no perfil do usuário, e integrado o fluxo híbrido (Bookmarklet assistido + importação atômica no keyring do Windows).
  - **Validação com dados reais:** Execução bem-sucedida de `auth status` e `usuario obter` com exibição de nome, CPF mascarado e OAB, além de consulta em tempo real na ComunicaAPI com `comunicacoes buscar --tribunal TJRO` retornando publicações ativas.

Após qualquer uso material desta skill, realize uma breve auto-avaliação antes de encerrar a tarefa:
avalie se o roteamento foi correto, se a skill melhorou, foi neutra ou degradou o resultado, qual
instrução concreta fez diferença e eventuais atritos ou contornos necessários. O sucesso de rotina
permanece efêmero. Havendo aprendizado acionável, pesquise as issues de `franklinbaldo/skills` e acrescente
evidências a uma issue existente ou abra uma issue de feedback devidamente saneada. Nunca publique
segredos, credenciais, dados pessoais ou fatos sigilosos.
