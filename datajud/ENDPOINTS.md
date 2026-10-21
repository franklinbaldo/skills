# Inventario e verificacao dos endpoints publicos DataJud

Este inventario cobre os aliases da **API Publica** para pesquisa de metadados.
Nao representa as APIs autenticadas de envio, manutencao ou acesso interno
do CNJ. Nao confundir indice ausente com processo ausente.

## Uso

Na raiz do repositorio:

```bash
python datajud/scripts/datajud_endpoints.py
python datajud/scripts/datajud_endpoints.py --alias tjro
DATAJUD_API_KEY='<chave-publica-atual-do-CNJ>' python datajud/scripts/datajud_endpoints.py --probe --alias tjro
```

A primeira operacao e **offline**: imprime as 91 URLs organizadas por familia.
`--probe` consulta o endpoint real por POST com `size=0`; devolve uma linha
JSON por tribunal, sem recuperar documentos ou movimentacoes. Consulte a chave
vigente em https://datajud-wiki.cnj.jus.br/api-publica/acesso/ .
Para uma varredura retomavel dos 91 endpoints e da matriz DSL:

```bash
export DATAJUD_API_KEY='<chave-publica-do-CNJ>'
python datajud/scripts/datajud_endpoints.py --probe --journal datajud-probes.jsonl --resume
python datajud/scripts/datajud_endpoints.py --probe --features --journal datajud-matriz.jsonl --resume
# Primeira rodada mais prudente, so um tribunal:
python datajud/scripts/datajud_endpoints.py --probe --features --alias tjro --journal tjro.jsonl
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

A chave de acesso publica do CNJ pode ser copiada da [pagina oficial](https://datajud-wiki.cnj.jus.br/api-publica/acesso/).
Nao inclua o valor literal no codigo nem em commits: defina DATAJUD_API_KEY
no ambiente. Para auditoria GitHub Actions, configure a variavel de repositorio
`DATAJUD_API_KEY` em Settings > Secrets and variables > Actions > Variables.

Isso evita novos achados de token embutido, sem suprimir verificacoes gerais.
Para um alerta historico ja emitido, somente classifique pontualmente como
falso positivo se a chave encontrada for comprovadamente a chave publica do
CNJ; nao habilite ignorancia global de padroes de segredo. Se a chave for
privada, revogue e substitua.

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
