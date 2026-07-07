---
name: datajud
description: >-
  Consulta METADADOS processuais na API Publica do DataJud/CNJ — capa (classe,
  assuntos, orgao julgador, grau, datas) e LINHA DE MOVIMENTACAO de processos de
  qualquer tribunal brasileiro (padrao TJRO; tambem STJ, STF, TRFs, outros TJs).
  Use SEMPRE que Franklin quiser: acompanhar a tramitacao/andamento de um
  processo por numero CNJ; dimensionar ou levantar acervo por classe, assunto,
  orgao, grau ou periodo de ajuizamento ("quantos / quais processos de execucao
  fiscal ajuizados em 2025", "distribuicao por vara"); ou um panorama estatistico
  do acervo (quantos por classe/assunto/orgao). Dispare mesmo sem a palavra
  "DataJud" — basta o pedido ser sobre andamento processual, contagem ou
  distribuicao de processos. NAO use para TEOR de decisao, ementa, voto ou
  fundamentacao (o DataJud NAO tem inteiro teor): para jurisprudencia e teor do
  TJRO use a skill juris-tjro.
---

## O que esta skill faz

Consulta a API Publica do DataJud (CNJ), que expoe **metadados** dos processos
de todos os tribunais brasileiros, indexados em Elasticsearch — um indice por
tribunal (`api_publica_tjro`, `api_publica_stj`, `api_publica_trf1`, etc.). Cada
documento traz a **capa** (numero CNJ, classe, assuntos, orgao julgador, grau,
sistema, formato, data de ajuizamento, ultima atualizacao, nivel de sigilo) e a
**linha de movimentacao** (tabelas processuais unificadas do CNJ, com codigo,
nome e complementos tabelados de cada movimento).

Limite conceitual central: **o DataJud NAO tem inteiro teor**. Nada de texto de
decisao, ementa, voto ou fundamentacao. Ele responde "quais/quantos processos de
tal classe/assunto/orgao/periodo" e "qual a tramitacao de tal processo" — nao "o
que o tribunal decidiu". Para teor de acordao/voto/sentenca do TJRO, use a skill
**juris-tjro**.

Toda a interacao acontece pelo script `scripts/datajud.py` (Python 3, so
stdlib). Ele ja encapsula a chave publica, o retry/backoff do rate limit e as
armadilhas de campo descritas abaixo — nao refaca as chamadas HTTP a mao.

## Como usar o script

Assuma rede liberada. Comece pelo `-h` de cada modo se precisar.

Tramitacao de um processo (traz todos os graus; aceita CNJ com ou sem mascara):

```
python scripts/datajud.py processo 7027457-61.2021.8.22.0001
python scripts/datajud.py processo 7027457-61.2021.8.22.0001 --movimentos
```

Descobrir o codigo de uma classe ou assunto pelo nome (via agregacao na propria
API — nao precisa decorar tabela):

```
python scripts/datajud.py codigos "execucao fiscal" --por classe
python scripts/datajud.py codigos "aposentadoria" --por assunto
```

Listar processos que casam com filtros:

```
python scripts/datajud.py buscar \
    [--classe COD] [--assunto TEXTO] [--assunto-codigo COD] \
    [--orgao TEXTO] [--grau G1|G2|JE|TR|SUP] \
    [--de DD/MM/AAAA] [--ate DD/MM/AAAA] \
    [--recentes] [--tamanho N] [--tribunal tjro] [--json]
```

Contar (total real, barato — use para dimensionar antes de puxar):

```
python scripts/datajud.py contar --classe 1116 --de 01/01/2025 --ate 31/12/2025
```

Panorama por dimensao (agregacao):

```
python scripts/datajud.py facetas --por classe        # ou assunto|orgao|grau|sistema
python scripts/datajud.py facetas --classe 1116 --por orgao --limite 10
```

Outro tribunal: acrescente `--tribunal` em qualquer modo (`stj`, `stf`, `trf1`,
`tjsp`, ...). O padrao e `tjro`. Franklin litiga em materia previdenciaria/INSS,
entao TRF1 e STJ encostam com frequencia.

Acrescente `--json` a qualquer modo para processar o resultado (planilha, tabela,
recurso repetitivo).

## Armadilhas da API — leia antes de consultar

Rate limit e a armadilha PRINCIPAL, e tem **dois sabores** (ambos ja tratados
pelo script com backoff exponencial, ate 5 tentativas):

- **HTTP 429** no gateway quando as requisicoes vem rapido demais.
- **HTTP 200 com `es_rejected_execution_exception` no corpo** quando a fila de
  busca do Elasticsearch enche. O status e 200; o erro esta no JSON. Se o script
  esgotar as tentativas, ele avisa — espere alguns segundos e repita. Ao rodar
  varias consultas em sequencia, **de um respiro entre elas** (~5s).

Outras pegadinhas ja resolvidas pelo script (nao as recrie):

- **Contagem**: sem `track_total_hits: true` o total satura em 10.000
  (`"relation": "gte"`). O script sempre pede a contagem real em `buscar`,
  `contar` e `facetas`.
- **Sort/filtro por `grau`**: o campo bruto e `text` (sem fielddata; sort/term
  cru -> HTTP 400). Use sempre `grau.keyword` — o script ja faz. O mesmo vale
  para agregacoes de campos textuais (`classe.nome.keyword`,
  `assuntos.nome.keyword`, `orgaoJulgador.nome.keyword`).
- **Data de ajuizamento** e string `AAAAMMDDHHMMSS` (14 digitos). Range com
  data de 8 digitos casa zero. O script normaliza `--de/--ate` (DD/MM/AAAA) para
  os 14 digitos, cobrindo o dia inteiro.
- **Multi-grau**: o MESMO numero de processo aparece em documentos separados por
  grau (1o grau, Juizado, Turma Recursal, 2o grau). O `_id` codifica
  `{TRIBUNAL}_{classe}_{grau}_{orgao}_{numero}`. O modo `processo` lista todos.
- **`codigos --por assunto`**: um processo tem varios assuntos, entao a
  agregacao traria assuntos "vizinhos". O script filtra os buckets para os nomes
  que de fato contem o termo e ordena por volume.
- **Chave publica**: e a MESMA para todos, embutida no script. O CNJ pode
  troca-la a qualquer momento; se comecar a dar HTTP 401, pegue a atual em
  https://datajud-wiki.cnj.jus.br/api-publica/acesso/ e atualize `APIKEY` no
  topo de `scripts/datajud.py`.
- **Sem inteiro teor** (repetindo porque importa): nao adianta procurar texto de
  decisao aqui. Para isso -> juris-tjro.

## Como apresentar os resultados a Franklin

Sintetize, nao despeje (o array de movimentos de um processo pode ter centenas
de itens; nunca jogue o JSON cru no contexto). Fluxo recomendado:

1. Se o pedido cita classe/assunto por nome, rode `codigos` primeiro para achar
   o codigo, depois filtre por `--classe`/`--assunto-codigo` (mais preciso que
   `--assunto`, que e match textual).
2. Para "quantos", `contar` resolve num tiro. Para "quais", `buscar`. Para
   "distribuicao/panorama", `facetas`.
3. Ao acompanhar UM processo, use `processo`; so acrescente `--movimentos`
   quando o andamento fino importar, e ao relatar destaque os movimentos
   relevantes (remessa, baixa, transito em julgado, sentenca, decisao) em vez de
   listar os "Decurso de Prazo"/"Publicacao" repetidos.
4. Deixe claro que sao metadados oficiais do CNJ (capa + movimentacao), sem teor,
   e ofereca o proximo passo util: puxar a integra do teor via juris-tjro (TJRO),
   exportar a lista (`--json`), refinar por orgao/periodo, ou dimensionar com
   `contar` antes de puxar um recorte grande.

## Campos uteis em cada resultado

`numeroProcesso` (20 digitos), `classe{codigo,nome}`, `assuntos[]{codigo,nome}`,
`orgaoJulgador{codigo,nome,codigoMunicipioIBGE}`, `grau` (G1=1o grau, JE=juizado,
G2=2o grau, TR=turma recursal, SUP=superior), `sistema{nome}` (PJe etc.),
`formato{nome}`, `dataAjuizamento` (AAAAMMDDHHMMSS), `dataHoraUltimaAtualizacao`
(ISO), `nivelSigilo`, `movimentos[]{codigo,nome,dataHora,complementosTabelados,
orgaoJulgador}`.
