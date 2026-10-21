---
name: datajud
description: >-
  Consulta metadados processuais oficiais no DataJud/CNJ: capa, classe, assuntos,
  órgão, grau, datas, contagens, facetas e linha de movimentação. Use para saber
  quais processos existem, quantos são, onde tramitam e o que aconteceu na linha
  processual. Não use para afirmar o teor, fundamento ou ratio de sentença,
  decisão, voto ou acórdão. Para teor do TJRO, use juris-tjro; para autos
  carregados e reconstrução documental, use notebooklm-processos.
compatibility: >-
  Requires Python 3 and outbound HTTPS access to the public DataJud/CNJ API.
  No private credential is required; the bundled client carries the CNJ public
  API key and handles retry/backoff. Dependencies are declared inline (PEP 723)
  and resolved by `uv run`.
---

# DataJud — metadados e movimentação

A função desta skill é responder perguntas sobre a **existência, classificação,
volume e trajetória processual** de casos registrados no DataJud.

Contrato da fonte:

```text
DataJud sabe:   processo, capa, classe, assunto, órgão, grau, datas, movimentos
DataJud não sabe: fundamento jurídico, ratio, argumento, conteúdo integral do ato
```

Nunca preencha o segundo conjunto por inferência a partir do primeiro.

## Regra de roteamento

Escolha a fonte pela proposição que precisa ser provada:

- “o processo existe / em que grau está / qual foi o último movimento?” → DataJud;
- “quantos processos com classe/assunto/órgão/período?” → DataJud;
- “o TJRO decidiu X por causa de Y?” → [`juris-tjro`](../juris-tjro/SKILL.md);
- “o que os documentos deste processo dizem, inclusive peças e anexos?” →
  [`notebooklm-processos`](../notebooklm-processos/SKILL.md) quando o corpus estiver
  carregado;
- “a jurisprudência atual do STJ/STF/outro tribunal diz X?” → pesquisa externa/
  fonte oficial adequada.

Um movimento chamado “Sentença”, “Decisão” ou “Provimento” prova que o ato foi
registrado, não o que o ato fundamentou.

## Fluxo

1. Defina se a pergunta é sobre **um processo**, **uma lista**, **uma contagem** ou
   **uma distribuição**.
2. Use o modo mais barato que resolve a pergunta. **Mais de um processo é sempre
   `lote`**, nunca um laço de `processo`: a API cobra por requisição, não por
   processo (seção "Lote é o padrão"). Todas as respostas recebidas são
   acrescentadas automaticamente ao SQLite append-only.
3. Não puxe movimentos completos quando capa/último estado bastarem.
4. Quando o próximo passo depender do conteúdo de um ato, pare e roteie para a
   fonte de teor.
5. Apresente apenas os movimentos/metadados que mudam a conclusão.

## Como executar

Toda interação com a API do DataJud passa pelos scripts empacotados em `scripts/`. As dependências são declaradas inline (PEP 723) e resolvidas automaticamente por `uv run` — não é preciso usar `--with`.

> **Atenção ao diretório de trabalho (`cwd`):**
> Os comandos abaixo assumem que você está na raiz desta skill (`datajud/` ou `skills/datajud/`). Se você estiver em outro diretório (por exemplo, dentro de um repositório como `pink` ou `judicial`), passe o caminho do script:
>
> ```bash
> # A partir de qualquer diretório:
> uv run "<caminho_da_skill>/scripts/datajud_mcp.py" processo <CNJ>
> # Ou entrando no diretório da skill:
> cd <caminho_da_skill>
> uv run scripts/datajud_mcp.py processo <CNJ>
> ```

### 1. `scripts/datajud_mcp.py` — Triagem rápida e marcos processuais (Recomendado)

Expõe o DataJud como **tool MCP** e como **CLI humana formatada em tabelas Rich**. Prefira-o para a pergunta mais comum — *onde este processo está?* — porque ele devolve resumo e **marcos**, não a lista inteira de movimentos:

```bash
uv run scripts/datajud_mcp.py processo 7000667-67.2026.8.22.0000
uv run scripts/datajud_mcp.py processo <cnj> --incluir-movimentos   # payload cru com todos os movimentos
uv run scripts/datajud_mcp.py processo <cnj> --json                 # saída em JSON estruturado
```

Medido em dois processos reais: 59 movimentos viraram 24 marcos; 138 (dois
graus) viraram 69. O que sai é ruído estável — decurso de prazo, publicação,
disponibilização no DJE, expedição de documento, juntada, petição, conclusão,
mero expediente, intimação e mandado expedidos, ajuste de classe (`RUIDO` no
script). **Filtra-se o ruído, não se enumeram os marcos**: a lista de códigos
que importam é longa e envelhece a cada revisão das Tabelas Processuais
Unificadas; a de ruído é curta e estável. Em 2026-10-19, num acervo de 3.448
processos, a lista original de cinco deixava "Petição" como último marco de 728
processos; os códigos acrescentados vieram dessa medição.

Sem `--tribunal`, o processo é procurado na **família** do número (seção
"Onde o processo pode estar"); `--tribunal` consulta só aquele índice e
`--so-origem`, só o tribunal de origem.

### 2. `scripts/datajud.py` — Pesquisa aprofundada, contagens, facetas e lote

Cliente focado em buscas avançadas, agregações, descoberta de códigos TPU e
download em lote.

## Catalogo de endpoints oficiais

O inventario versionado dos **91 aliases publicos** e o verificador opt-in
estao em [ENDPOINTS.md](ENDPOINTS.md). O catalogo pode ser inspecionado sem
rede com `python scripts/datajud_endpoints.py` (estando na pasta `datajud/`).
Nunca trate APIs restritas de transmissao/manutencao como se fossem rotas
publicas de consulta; o comando `--probe` so deve ser usado explicitamente,
com a chave publica atual fornecida no ambiente.

## Onde o processo pode estar

A API não tem índice unificado: cada tribunal é um índice
(`api_publica_tjro`, `api_publica_stj`…). Vários índices numa só requisição,
por vírgula ou curinga, esbarram no tempo-limite de 60 s do balanceador do CNJ
(medido em 2026-10-19: três tribunais grandes ou `*` dão 504). Por isso a busca
consulta um índice por requisição, em paralelo.

O número CNJ diz o tribunal de **origem** (segmento `J.TR`), e por ele a skill
monta a **família** onde procurar:

- a **origem** (`tjro`, `trt14`, `trf1`, `tre-ro`, `tjmmg`, `stj`, `tst`…);
- os **demais tribunais do estado de origem**: TJ, TRT da região, TRF da
  região, TRE e, em MG, RS e SP, o TJM — processo pode mudar de ramo por
  declínio de competência; é raro, mas acontece. Número federal só diz a região
  (o TRF1 cobre 13 estados), então ali entram só o TRF e os superiores;
- os **superiores**: STJ, TST, TSE, STM. Quem sobe ao STJ segue lá **com o
  mesmo número de origem**, grau `SUP` e a classe do recurso (medido: 7 de 100
  processos do TJRO com 2º grau estavam no índice `stj`).

O **STF não tem índice** na API pública (`index_not_found`): número do STF
sai como "sem tribunal deduzível", e passagem pelo STF não aparece no DataJud.

Cada registro devolvido carrega o tribunal onde foi achado (`_index` no cru,
`tribunal` na saída), e a resposta lista os índices **consultados** — ausência
só significa algo para quem foi consultado e respondeu.

## Acervo SQLite: relacional, só de acréscimo

**Toda chamada real à API** passa por datajud.search(), incluindo a tool MCP,
processo, lote, buscar, contar, facetas e codigos. O transporte registra
automaticamente a resposta em um único banco SQLite persistente:

- Padrão: diretório de dados do usuário (Linux: ~/.local/share/datajud/acervo.sqlite;
  Windows: %LOCALAPPDATA%/datajud/acervo.sqlite).
- Para usar outro local persistente: variável de ambiente DATAJUD_SQLITE.
- O banco NÃO deve ir para o Git nem para caches efêmeros. Preserve-o com backup
  privado; metadados processuais podem exigir controle de acesso.

Leitura sem acessar a API:

```bash
uv run scripts/datajud.py estado <CNJ>                   # capa, assuntos e movimentos vigentes
uv run scripts/datajud.py estado <CNJ> --em 2026-10-01   # como o acervo o conhecia naquela data
uv run scripts/datajud.py historico <CNJ> --detalhar     # o que entrou e saiu em cada observação
uv run scripts/datajud.py novidades 2026-10-19 --numeros acervo.txt  # o que mudou no acervo desde a data
uv run scripts/datajud.py banco                          # linhas por tabela
```

Com `--json`, cada comando emite o modelo Pydantic correspondente
(`EstadoProcesso`, `HistoricoProcesso`, `Novidades`, `Estatisticas`), e o agente também pode
consultar o SQLite direto.

`novidades` é para a rotina que reconsulta um acervo inteiro (`lote`) e quer
só o que a passada trouxe: movimentos que entraram ou saíram (com `marco`
falso para os códigos de `RUIDO`), capas novas e processos que apareceram
noutro tribunal ou grau. A primeira observação de um registro é linha de base:
os movimentos que ele já trazia viram contagem, e não novidade.

O documento do DataJud é **decomposto em tabelas**, e só se guarda o que não
se deduz. Andamento novo é uma linha em `movimentos`, e não uma cópia do
histórico. Processo visto sem mudança é uma linha de dois inteiros em `vistas`.
Medido em 2026-10-20 sobre o acervo real (3.477 processos, 4.847 documentos,
408 mil movimentos, três passadas): 29,8 MB, contra 165,6 MB das duas versões
anteriores no mesmo arquivo. A conversão levou 3,6 s.

| Tabela                                      | Uma linha por…                                                                |
| ------------------------------------------- | ----------------------------------------------------------------------------- |
| `consultas`                                 | requisição à API, com sucesso ou erro; corpo comprimido e recorte `_source`   |
| `registros`                                 | documento: índice + `_id` (um grau de um processo num tribunal)               |
| `capas`                                     | versão da capa (classe, órgão, sistema, formato, sigilo, ajuizamento)         |
| `assuntos`, `movimentos`                    | item do registro (hash do conteúdo + ocorrência), com a observação de entrada |
| `tipos_movimento`, `orgaos`, `complementos` | catálogo do que se repete entre os itens                                      |
| `movimento_complementos`                    | complemento tabelado de um movimento                                          |
| `observacoes`                               | registro visto **com mudança**, com os campos voláteis                        |
| `vistas`                                    | registro visto **sem mudança** numa consulta                                  |
| `presencas_movimento`, `presencas_assunto`  | item que **saiu** ou **voltou** (retificação na fonte)                        |

Regras que o desenho garante:

- **Volátil não é mudança.** `@timestamp`, `dataHoraUltimaAtualizacao` e
  `_score` não criam observação: só se guardam junto de uma mudança.
- **Retificação não apaga.** Movimento corrigido na fonte sai e o corrigido
  entra; os dois ficam, com a data em que trocaram.
- **Repetição é dado.** O mesmo movimento idêntico aparece repetido no mesmo
  documento (9.308 vezes no acervo medido), e cada ocorrência tem linha própria.
- **Recorte não é ausência.** Campo fora do `_source` pedido (o `buscar` pede só
  a capa) não foi observado, e não gera "saiu". O `estado` diz quando cada
  coleção veio pela última vez (`movimentos_observados_em`) e devolve `null`, e
  não lista vazia, para a coleção que nenhuma consulta trouxe.
- **Data do movimento em segundos.** `movimentos.instante` guarda a `dataHora`
  em segundos UTC, e `data_hora` a refaz exata. Texto em outra forma fica em
  `data_hora_texto`, como veio.
- Cada tabela tem um modelo Pydantic (`Linha*` em `datajud_store.py`), e o DDL
  é gerado dele. A resposta da API também tem modelos (`datajud_modelos.py`),
  com campo extra aceito: campo novo do CNJ não derruba a consulta.
- Triggers impedem UPDATE e DELETE em todas as tabelas.

Banco de versão anterior (#125, documento inteiro por versão; #128, primeira
versão relacional): na primeira abertura, o acervo é convertido num arquivo
novo, a partir das tabelas antigas e sem consultar a API. O antigo fica ao lado
como `acervo-antes-v3-<instante>.sqlite`, para conferência; apague-o quando não
precisar mais. `uv run scripts/datajud.py migrar` faz isso num momento
escolhido. Com o banco aberto noutro processo, a conversão espera a próxima
abertura e diz isso.

A data do **registro de um movimento no tribunal** (`movimentos.instante`)
não é a data da **observação pela skill** (`observacoes.observado_em`).
Mantenha as duas separadas. Exemplo SQL, os movimentos de um processo, com a
data em que a skill os viu entrar:

```sql
SELECT r.tribunal, r.grau, datetime(m.instante, 'unixepoch') AS data_hora,
       t.codigo, t.nome, o.observado_em AS visto_em
FROM registros AS r
JOIN movimentos AS m ON m.registro_id = r.id
JOIN tipos_movimento AS t ON t.id = m.tipo_id
JOIN observacoes AS o ON o.id = m.observacao_id
WHERE r.numero_processo = '70095117120248220001'
ORDER BY m.instante;
```

O SQLite é um **histórico de observações**, não espelho vivo. Processos
podem receber novos atos, correções ou até remoções na fonte. Para obter
nova observação, volte a consultar o DataJud; uma consulta feita no mês
passado não prova a situação atual.

## Lote é o padrão

Cada requisição ao DataJud leva de segundos a dezenas de segundos (medido em
2026-10-19: ~40 s), e custa o mesmo com 1 ou com 100 processos. Um laço de
`processo` sobre um acervo de milhares leva horas; o modo `lote` levou ~6 min
para 3.448 processos só na origem. Sempre que houver **mais de um processo**,
use-o:

```bash
uv run scripts/datajud.py lote numeros.txt                           # SQLite, nova observação
uv run scripts/datajud.py lote numeros.txt --so-origem                # só índice de origem
uv run scripts/datajud.py lote numeros.txt --saida .cache/datajud     # JSON legado opcional
```

- `numeros.txt` tem um CNJ por linha, com ou sem máscara; duplicatas caem.
- Cada índice da família vai em consultas `terms` de até 100 processos, em
  paralelo (`--trabalhadores`, padrão 4). A família multiplica as consultas
  (oito índices para um número do TJRO), não o custo por processo.
- Por padrão, todas as respostas vão para o SQLite, sem criar milhares de JSONs.
  Rodar novamente observa a fonte de novo e registra nova data/hora; o que não
  mudou rende só uma vista.
- `--saida` é compatibilidade opcional: exporta também JSON por processo e
  mantém a retomada antiga nesse diretório. A história canônica é o SQLite.
- Índice sem resposta (504, rede etc.) registra um evento de falha, nunca
  ausência do processo. Observações anteriores permanecem intactas.
- Use os resultados acumulados para análises posteriores com SQL, sem novas
  requisições desnecessárias. Para atualizar a informação, faça nova consulta.

O resumo final diz quantos foram observados e encontrados, quais aparecem
em outro tribunal, quais números não revelam índice e quais tiveram índice
sem resposta (código de saída 1). Uma nova execução registra nova observação.

## Movimento e documento envelhecem em ritmos diferentes

O DataJud reflete o **registro de movimentos do próprio tribunal**. Qualquer
cópia local dos documentos de um processo — exportação, espelho de sistema de
gestão, PDF baixado — reflete o acervo **na data em que foi feita**, e pode
ficar meses atrás.

Daí a regra: quando o documento mais recente de que você dispõe parece antigo
demais para a fase do processo, **não conclua que nada aconteceu**. Consulte os
movimentos antes. A cópia dá o *teor* do que foi capturado; o DataJud dá o
*estado*, inclusive o que veio depois.

É a diferença entre "o processo parou" e "a minha cópia parou", e confundi-las
custa caro: sentença, acórdão e trânsito em julgado são exatamente o que costuma
estar do lado de fora do recorte.

Toda interação com a API deve passar por `scripts/datajud.py` ou pelo servidor
acima — nunca chamada direta ao endpoint.

Processo:

```bash
uv run scripts/datajud.py processo 7027457-61.2021.8.22.0001
uv run scripts/datajud.py processo 7027457-61.2021.8.22.0001 --movimentos
```

Descobrir códigos:

```bash
uv run scripts/datajud.py codigos "execucao fiscal" --por classe
uv run scripts/datajud.py codigos "aposentadoria" --por assunto
```

Buscar:

```bash
uv run scripts/datajud.py buscar \
  [--classe COD] [--assunto TEXTO] [--assunto-codigo COD] \
  [--orgao TEXTO] [--grau G1|G2|JE|TR|SUP] \
  [--de DD/MM/AAAA] [--ate DD/MM/AAAA] \
  [--recentes] [--tamanho N] [--tribunal tjro] [--json]
```

Contar e agregar:

```bash
uv run scripts/datajud.py contar --classe 1116 --de 01/01/2025 --ate 31/12/2025
uv run scripts/datajud.py facetas --por classe
uv run scripts/datajud.py facetas --classe 1116 --por orgao --limite 10
```

Em `buscar`, `contar`, `facetas` e `codigos`, use `--tribunal stj|trf1|tjsp|...`
quando necessário; o padrão é TJRO. Em `processo` e `lote`, a busca cobre a
família do número CNJ.

## Escolha econômica do modo

- **“qual o andamento deste processo?”** → `processo`;
- **“qual o estado destes processos?”** (dois ou mais) → `lote`;
- **“quantos?”** → `contar`;
- **“quais?”** → `buscar`;
- **“como se distribuem?”** → `facetas`;
- **“qual o código da classe/assunto?”** → `codigos`.

Não faça `buscar` grande para depois contar localmente quando `contar` responde
sem transferir o corpus.

## Composição com juris-tjro

DataJud e JURIS são complementares, não concorrentes.

Um fluxo útil para caso do TJRO pode ser:

```text
DataJud: localizar processo/grau/movimento/data
→ JURIS: localizar o documento correspondente e ler o teor
→ análise: separar o que veio do metadata do que veio do texto
```

Quando apresentar uma conclusão composta, mantenha a proveniência explícita:
“DataJud registra movimento X em data Y; o inteiro teor no JURIS afirma Z”. Não
fundir as duas evidências numa frase sem origem.

## Armadilhas que continuam load-bearing

O script já trata:

- HTTP 429 e `es_rejected_execution_exception` em HTTP 200;
- `track_total_hits: true` para não saturar contagens em 10.000;
- `.keyword` em `grau`/campos textuais de agregação;
- datas de ajuizamento `AAAAMMDDHHMMSS`;
- múltiplos documentos do mesmo CNJ por grau (no `lote`, agrupados por número);
- resposta de lote truncada (`total` maior que os hits devolvidos) vira erro,
  nunca "não encontrado";
- filtragem de assuntos vizinhos em `codigos`;
- chave pública do CNJ.

Se houver HTTP 401, confira a chave pública atual na documentação oficial do
DataJud antes de concluir que o serviço caiu.

## Como apresentar

Sintetize. Para um processo, destaque apenas eventos que mudam o estado útil:
distribuição, decisão, sentença, remessa, julgamento, trânsito, baixa e outros
marcos pertinentes ao pedido.

Para listas/estatísticas, mostre o recorte e a dimensão usada. Não despeje JSON
nem centenas de movimentos.

Sempre deixe claro quando a resposta é **metadado oficial sem inteiro teor**.

## Definition of Done

A consulta termina quando:

- a pergunta foi resolvida pelo modo mais econômico;
- o tribunal/grau/período usados estão claros quando relevantes;
- movimentos irrelevantes não ocupam a resposta;
- nenhuma conclusão de fundamento foi inferida de metadata;
- quando teor se tornou necessário, a investigação foi roteada para a fonte
  correta;
- em respostas compostas, metadata e teor permanecem distinguíveis por
  proveniência.

A skill é bem-sucedida quando responde rapidamente **onde, quando, quantos e
qual movimento** — e sabe parar antes de fingir saber **por quê**.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
