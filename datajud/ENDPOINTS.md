# Inventario e verificacao dos endpoints publicos DataJud

Este inventario cobre os aliases da **API Publica** para pesquisa de metadados.
Nao representa as APIs autenticadas de envio, manutencao ou acesso interno
do CNJ. Nao confundir indice ausente com processo ausente.

## Uso

Na raiz do repositorio:

```bash
uv run datajud/scripts/datajud_endpoints.py
uv run datajud/scripts/datajud_endpoints.py --alias tjro
uv run datajud/scripts/datajud_endpoints.py --probe --alias tjro
```

A primeira operacao e **offline**: imprime as 91 URLs organizadas por familia.
`--probe` consulta o endpoint real por POST com `size=0`; devolve uma linha
JSON por tribunal, sem recuperar documentos ou movimentacoes. Consulte a chave
vigente em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ .
Para uma varredura retomavel dos 91 endpoints e da matriz DSL:

```bash
uv run datajud/scripts/datajud_endpoints.py --probe --journal datajud-probes.jsonl --resume
uv run datajud/scripts/datajud_endpoints.py --probe --features --journal datajud-matriz.jsonl --resume
# Primeira rodada mais prudente, so um tribunal:
uv run datajud/scripts/datajud_endpoints.py --probe --features --alias tjro --journal tjro.jsonl
```

`--features` executa sete consultas independentes (match_all, term, bool,
range, aggs, source, sort). Com 91 aliases, isso representa **637 consultas**;
nao execute todas sem considerar o limite de requisicoes do CNJ. Um retorno
positivo apenas prova que o servidor respondeu adequadamente ao corpo
testado naquele instante; nao estabelece compatibilidade universal do recurso.

O arquivo JSONL registra timestamp UTC, alias, recurso, hash do contrato,
status HTTP e categoria de falha, sem registrar dados pessoais ou a chave.
O journal e somente acrescentado; `--resume` reutiliza apenas sucessos
anteriores do mesmo corpo de teste. Erros HTTP, JSON invalido e falhas
parciais dos shards sao preservados e tentados novamente numa futura rodada.
**A execucao da varredura real nao e implicita na PR.**

O argumento `--delay` controla o intervalo entre chamadas; evite executar
probes indiscriminados em horario de pico. A resposta HTTP ou o erro de
conexao nao e usado para inferir ausencia de processos.

Familias catalogadas:

| Familia                                   | Aliases |
| ----------------------------------------- | ------: |
| Justiça Estadual                          |      27 |
| Justiça Eleitoral                         |      27 |
| Justiça do Trabalho                       |      24 |
| Justiça Federal                           |       6 |
| Tribunais Superiores (STJ, TST, TSE, STM) |       4 |
| Justiça Militar Estadual (MG, RS, SP)     |       3 |
| **Total**                                 |  **91** |

O STF nao figura entre os aliases publicos catalogados. Toda rota segue
`POST https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search`.

## Chave pública e GitGuardian

A autenticacao usa a **chave publica compartilhada** que o DPJ/CNJ publica na
[pagina oficial de acesso](https://datajud-wiki.cnj.jus.br/api-publica/acesso/).
Nao e credencial privada, pessoal nem especifica de uma conta. O valor fica
**literal e versionado** em `PUBLIC_API_KEY`, no arquivo
`scripts/datajud_endpoints.py`, usado tambem por `datajud.py` e pelo MCP.
Fonte consultada em **2026-10-23**; o CNJ pode substituir a chave a qualquer momento.

Sem configurar nada, as requests usam este header:

```text
Authorization: APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==
```

`DATAJUD_API_KEY` e um **override opcional**, lido a cada consulta. Ausente ou
vazio, mantem o padrao publico embutido. Se houver HTTP 401, confira a fonte
oficial e atualize o literal ou use temporariamente o override com a nova
chave publica. Nao e necessario criar conta, segredo ou variavel de ambiente
para usar o padrao. A consulta ainda depende da disponibilidade da API.

O workflow de auditoria real continua **opt-in**. A variavel de repositorio
`DATAJUD_API_KEY` nas Actions Variables pode substituir o padrao, mas nao e
requisito. Versionar esta chave nao autoriza nem dispara a varredura real.

### Excecao pontual no GitGuardian

A integracao GitHub App deste repositorio usa os incidentes do dashboard.
Para o alerta desta chave, confira se o valor encontrado e exatamente o
publicado pelo CNJ e classifique **somente esse incidente** como `Ignored`,
com motivo `False positive (not a secret)` e a URL oficial na justificativa.
Isso preserva a trilha de auditoria e a deteccao de outros segredos.

O GitGuardian documenta que novas ocorrencias de um incidente ignorado nao
reabrem o incidente nem geram novo alerta. A excecao acompanha o mesmo valor;
nao cobre automaticamente outra chave se o CNJ fizer uma rotacao. O agrupamento
padrao e por segredo, podendo abranger ocorrencias em outros repositorios do
workspace; instalacoes Enterprise podem agrupar por segredo e fonte.

**Este commit nao altera o dashboard nem declara o alerta resolvido.** O
responsavel precisa aplicar a classificacao pontual no incidente existente e
verificar um check posterior. Nao revogue uma chave publica compartilhada,
nao reescreva o historico e nao desative o scanner ou detectores inteiros.

A configuracao local `.gitguardian.yaml` / `secret.ignored_matches` so atua no
`ggshield`; nao sincroniza a excecao com o GitHub App. Portanto, nao e usada
como substituto da classificacao do incidente remoto. Um comentario `ggignore`
por linha tambem nao corrige ocorrencias em commits anteriores.

Referencias do GitGuardian:

- [GitHub checkruns e incidentes fechados](https://docs.gitguardian.com/internal-monitoring/prevent/detect-secrets-in-real-time-in-github)
- [Ignored e novas ocorrencias](https://docs.gitguardian.com/internal-monitoring/detect/incident-statuses)
- [Agrupamento de ocorrencias](https://docs.gitguardian.com/internal-monitoring/detect/secrets-occurrences)
- [Limite das exclusoes locais do ggshield](https://docs.gitguardian.com/ggshield-docs/reference/secret/ignore)

## Escopo e evolucao

- A lista e um **contrato local versionado**, nao uma garantia de disponibilidade.
- O probe distingue falha HTTP, falha de rede e JSON de erro de uma resposta
  que contenha `hits`; os testes unitarios nunca fazem rede.
- A origem de um numero CNJ nao demonstra todos os tribunais em que o mesmo
  numero possa aparecer. Para consultar familias, use `datajud.py lote`.
- Um novo alias oficial deve ser incluido com teste, revisao documental e
  probe especifico antes de entrar no catalogo.
- As APIs de transmissao XML, manutencao/exclusao e consulta de indice interno
  possuem autorizacoes e semanticas diferentes; nao sao testadas aqui.

Fontes:

- https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
- https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- https://datajud-wiki.cnj.jus.br/para-tribunais/orientacoes-rest/envio-xml/envio-rest/
- https://datajud-wiki.cnj.jus.br/para-tribunais/manutencao-datajud/endpoints/
