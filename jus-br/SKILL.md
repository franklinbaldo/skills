---
name: jus-br
description: >-
  Usa a sessão gov.br do usuário no Portal de Serviços da PDPJ/CNJ
  (portaldeservicos.pdpj.jus.br) para ler autos de qualquer tribunal pela base
  nacional, baixar peças, consultar comunicações (DJEN e Domicílio Judicial
  Eletrônico) e preparar e protocolar petição intercorrente nos tribunais que o
  Portal habilita. Use quando o processo não está no sistema da casa, para
  conferir autos e intimações pela PDPJ, ou para peticionar pelo Portal. Não use
  para tribunais fora do cadastro de peticionamento do Portal (ex.: TRF6): ali o
  protocolo é no sistema do próprio tribunal.
compatibility: >-
  Python 3.11+ com metadados PEP 723 e `uv run`. Sessão no cofre do sistema
  (Windows Credential Manager, macOS Keychain, Linux SecretService).
---

# Jus.br / Portal de Serviços da PDPJ

CLI `uv run jus-br/cli.py` sobre a API do **Portal de Serviços da PDPJ-Br**
(`https://portaldeservicos.pdpj.jus.br/api`), com a sessão gov.br do próprio usuário.

## O que foi verificado e como

Tudo abaixo foi conferido em 26/10/2026 com sessão real, não presumido:

| Recurso                                                         | Estado                              | Fonte                                                                                  |
| --------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| Login gov.br pelo favorito (`auth bookmarklet`)                 | funciona                            | sessão do cliente `portalexterno-frontend`, cerca de 8 h                               |
| Login pelo callback `www.jus.br` (`auth login`)                 | falha                               | o site gasta o código antes da CLI: `Code not valid`                                   |
| Autos (`processo`)                                              | funciona                            | `GET /v2/processos/{cnj}` e `/documentos/{id}/binario`                                 |
| DJEN e Domicílio Eletrônico (`comunicacoes`)                    | funciona                            | `GET /v1/comunicacao` e `/v1/domicilio-eletronico/comunicacao`                         |
| Cadastro e tipos por tribunal (`peticao tribunal`, `tipos`)     | funciona                            | `GET /v1/tribunais/{jtr}`, `/v1/tribunal/listar`, `/v1/tipo/documento/tribunal`        |
| Rascunho, anexos e protocolo (`peticao rascunho`, `protocolar`) | **envio ao S3 negado** (ver abaixo) | `POST /v1/documentos/{cnj}/upload/url`, `POST /v1/peticoes`, `/v1/peticoes/protocolar` |

O contrato está no Swagger de homologação: `uv run jus-br/openapi_discovery.py` acha os
Swagger UI e `.../swagger-resources` lista os grupos (`/v2/api-docs?group=Interno`). Os
valores de cada campo da petição foram conferidos contra petições reais do usuário
(`peticao ver <id>`).

## A escolha consciente: cabeçalhos de navegador

A API de produção devolve **403 do servidor web** a chamadas que não se apresentam como
o navegador do próprio Portal. `portal.py` envia os cabeçalhos dele
(`CABECALHOS_NAVEGADOR`: `User-Agent`, `Referer`, `Sec-Fetch-*`). Isso funciona
hoje, mas é frágil, e o CNJ pode mudar o bloqueio sem aviso. O caminho limpo é um cliente
integrador cadastrado no CNJ, que a documentação do SSO manda pedir. Se o 403 voltar, a
skill não deve insistir em contornar: registre e pare.

## Sessão

```powershell
uv run jus-br/cli.py auth bookmarklet   # abre a página do favorito e espera a captura
uv run jus-br/cli.py auth status        # validade do token guardado
uv run jus-br/cli.py auth logout        # encerra e apaga do cofre
```

No Portal, já logado com o gov.br, clique no favorito **Conectar Sessão PDPJ**. Ele copia
o token para a área de transferência e a CLI o grava no cofre. O código do favorito está em
`bookmarklet.html`. O token é a sessão do usuário no PJe: nunca o cole em chat, issue ou log.

## Autos e comunicações

```powershell
uv run jus-br/cli.py processo consultar 6009021-21.2026.4.06.3802      # capa, partes, movimentos, peças
uv run jus-br/cli.py processo baixar <cnj> <id-da-peça> -o .cache/autos/<cnj>/peca.pdf
uv run jus-br/cli.py comunicacoes domicilio 2026-10-20 2026-10-26       # janela de até 7 dias
uv run jus-br/cli.py comunicacoes buscar --processo <cnj>              # ComunicaAPI pública
uv run jus-br/cli.py api get v1/usuario                                 # rota do Swagger sem comando próprio
```

A família `v1/processos/*` responde "não encontrado" mesmo para processo existente; use
os comandos acima, que vão pela `v2`. O texto extraído (`/texto`) nem sempre existe; o
binário existe.

## Petição intercorrente

Escrita segue o padrão do `todos`: **sem `--confirmar` o comando só mostra o plano**.

```powershell
uv run jus-br/cli.py peticao tribunal TRF1                 # recebe petição intercorrente? que arquivos?
uv run jus-br/cli.py peticao tipos TRF1 --busca contestação
uv run jus-br/cli.py peticao rascunho <cnj> contestacao-PDFA.pdf --tipo 533 `
    --anexo anexo-1-PDFA.pdf --anexo anexo-2-PDFA.pdf --tipo-anexo <id> --confirmar
uv run jus-br/cli.py peticao listar                        # confira o rascunho, também no Portal
uv run jus-br/cli.py peticao protocolar <id> --confirmar   # não se desfaz
uv run jus-br/cli.py peticao conferir <recibo-cnj>         # juntada, aguardando, recusada
uv run jus-br/cli.py peticao excluir <id> --confirmar      # apaga rascunho não usado
```

Regras que a CLI aplica antes de qualquer escrita:

1. **Tribunal habilitado.** Sem cadastro em `GET /v1/tribunais/{jtr}` com
   `PETICAO_INTERCORRENTE`, para e manda peticionar no sistema do tribunal. O TRF6
   (JTR 406) não está no cadastro, embora seus autos apareçam na consulta.
2. **Tipo de documento do tribunal.** O `id` vem de `peticao tipos`, que muda por tribunal
   ("Petição intercorrente" é 517 no TRF1, "PETIÇÃO" é 90 no TJRO e "Petição (Outras)" é 209
   na TPU, usada pelo TJMS). Descrição ambígua é erro, nunca palpite.
3. **Arquivo aceito.** Extensão e tamanho conferidos contra `tiposArquivosAceitos` do
   tribunal (PDF até 10 MB no TRF1). Converta para PDF/A antes, com a skill `convert-to-pdfa`.
4. **Dados do processo saem dos autos.** Órgão julgador, distribuição, grau, classe,
   partes e assuntos vêm de `GET /v2/processos/{cnj}` (`peticao_montagem.py`); nada é
   digitado.
5. **Rascunho antes de protocolo.** O rascunho fica em "Minhas petições" para conferência
   humana; `protocolar` mostra os documentos e exige `--confirmar`. Falha no meio do
   envio deixa o rascunho: confira em `peticao listar` antes de repetir.

**O fluxo é o do formulário do Portal**, lido no JavaScript público dele
(`portaldeservicos.pdpj.jus.br`, chunks do módulo de petição) e conferido contra uma
petição real do usuário (`peticao ver`):

1. Tipos de documento pela origem do tribunal (`GET /v1/tribunal/listar?jtrTribunal=`,
   campo `origemTipoDocumento`): `1` é a TPU do CNJ (`GET /v1/tpu/tipoDocumentos`, o
   `id` é o `cod_item`; caso do TJMS, cuja lista própria vem vazia); `2` é a lista do
   tribunal (`/v1/tipo/documento/tribunal`, caso do TJRO). Na TPU há duas entradas
   "Manifestação (Outras)" (180 e 128): use o id.
2. Cada arquivo vai antes ao repositório do processo:
   `POST /v1/documentos/{numeroProcesso}/upload/url` com os metadados (SHA-1 em hex,
   tipo, `idOrigemTipoDocumento`, `sigiloso` booleano), e o PDF segue por `PUT` na
   `urlPreSigned` da resposta. Sem `urlPreSigned`, aquele SHA-1 já está registrado.
3. O rascunho (`POST /v1/peticoes`) só referencia os arquivos, aninhados:
   `peticaoDocumentos: [{"documento": {...}}]`. Era o formato que faltava (o 500 de
   26/10 vinha dos campos soltos, sem o envio antes).
4. O protocolo do formulário é `POST /v1/peticoes/protocolar` com a petição inteira.

**Bloqueio atual (30/10/2026): o `PUT` no S3 é negado.** O registro (passo 2) é aceito,
mas o S3 responde `AccessDenied` com *explicit deny in an identity-based policy* do usuário
IAM `pdpj`, com ou sem `Origin`/`Referer` do Portal. A URL só assina `host` e vale 10
minutos. Não insista: cada tentativa registra um documento órfão (sem conteúdo nem
petição, sem rota para apagar). Antes de nova tentativa, confira no navegador se o envio
pelo Portal funciona e capture o `PUT` (F12, Network, sem `authorization` nem cookie): se o
navegador também recebe 403, é indisponibilidade do Portal; se não, compare os cabeçalhos.

## Arquivos

| Arquivo                            | Papel                                                              |
| ---------------------------------- | ------------------------------------------------------------------ |
| `cli.py`                           | reúne os grupos de comandos                                        |
| `cli_auth.py`, `captura_sessao.py` | sessão: favorito, importação, status, renovação                    |
| `cli_consultas.py`                 | perfil, comunicações, Domicílio Eletrônico, `api get`              |
| `cli_processo.py`                  | autos e peças                                                      |
| `cli_peticao.py`                   | cadastro, tipos, rascunho, protocolo                               |
| `portal.py`                        | cliente HTTP do Portal (cabeçalhos, renovação em 401, envio ao S3) |
| `peticao_montagem.py`              | monta a petição a partir dos autos, sem rede                       |
| `auth.py`, `credentials.py`        | SSO (Keycloak `pje`) e cofre com blocos de 512 bytes               |
| `client.py`                        | perfil (`userinfo`) e ComunicaAPI pública                          |
| `openapi_discovery.py`             | inventário dos Swagger oficiais                                    |

Testes offline: `uv run --with pytest --with cyclopts --with httpx --with keyring --with pydantic --with rich -- pytest -q jus-br/tests`.

## Segurança

- Nunca registre, imprima ou publique `access_token`, `refresh_token`, código de
  autorização ou o cabeçalho `Authorization`.
- O envio ao repositório (URL pré-assinada do S3) vai sem o Bearer da PDPJ.
- Nenhum recibo, protocolo ou dado processual é simulado: o que a CLI mostra veio do Portal.
- Rascunho, protocolo e exclusão só com `--confirmar`, e o protocolo é decisão de quem
  assina a peça.

## Real-use postmortem

- **2026-10-21:** o cliente público do Portal é `portalexterno-frontend`; o favorito
  captura a sessão e `usuario obter` confirmou nome, CPF mascarado e OAB.
- **2026-10-26:** login gov.br pelo favorito funcionou; `auth login` pelo callback do
  `www.jus.br` falhou com `Code not valid`. A API de produção só respondeu com os
  cabeçalhos do navegador (403 do servidor web sem eles). Varredura dos 61 `GET` do
  Swagger mapeou o que responde. Uma contestação ao TRF6 não pôde ir pelo Portal: o
  tribunal não está no cadastro de peticionamento e o protocolo fica no eproc. Os autos
  trazem `permitePeticionar`, `idFonteDadosCodex` e `idOrigem`; a data de distribuição vem
  com milissegundos, que o Portal não guarda. Criar rascunho no TRF1 falhou (422, 403,
  500), sem deixar rascunho: falta capturar o fluxo do navegador.
- **2026-10-30:** usucapião no TJMS (manifestação de desinteresse do Estado de RO). O TJMS
  usa tipos da TPU, que a CLI não consultava: `peticao tipos TJMS` vinha vazio. O fluxo
  real foi lido no JS do Portal e o formato confirmado numa petição já juntada (documentos
  aninhados em `documento`). Registro do arquivo aceito; `PUT` no S3 negado por política IAM
  do Portal (4 tentativas, documentos órfãos). Conversão para PDF/A exigiu seguir o shim do
  Scoop no `convert-to-pdfa`.

Após uso material, avalie se o roteamento foi correto, se a skill ajudou ou atrapalhou e
que atrito houve. Havendo aprendizado acionável, registre em issue de `franklinbaldo/skills`,
sem segredos, dados pessoais ou fatos sigilosos.
