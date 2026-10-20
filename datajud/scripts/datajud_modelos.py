# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.6"]
# ///
"""Modelos Pydantic do que a API publica do DataJud recebe e devolve.

E o contrato do fio: `RequisicaoBusca` e o corpo do POST `_search`,
`RespostaBusca` e o que volta. O acervo SQLite (`datajud_store.py`) decompoe a
`Fonte` de cada `Hit` nas suas tabelas; os comandos leem a capa por eles.

Medido em 2026-10-19 sobre 4.820 documentos de 3.448 processos (TJRO, TRT14,
TRF1, STJ, TST), e e isso que os tipos dizem:

- `orgaoJulgador.codigo` e inteiro na capa e texto no movimento; aqui vira
  sempre texto, para os dois casarem;
- `complementosTabelados` falta em metade dos movimentos (ausente, nao vazio);
- `codigoMunicipioIBGE` e nulo em 5 capas e o `nome` falta em 145 assuntos e
  em 1.528 movimentos;
- o mesmo movimento, identico campo a campo, aparece repetido no mesmo
  documento (9.308 repeticoes em 406.385 movimentos): repeticao e dado, nao
  ruido de leitura, e o acervo a guarda.

Todos os modelos aceitam campo extra (`extra="allow"`): campo novo da API passa
e fica em `model_extra`, em vez de sumir ou derrubar a consulta.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Aberto(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def bruto(self) -> dict[str, Any]:
        """O objeto como veio: so as chaves que a API mandou, com os nomes dela.

        E sobre ele que o acervo calcula o hash de identidade de capa, assunto
        e movimento. Os dois ajustes dos validadores (codigo do orgao em texto,
        assuntos achatados) entram no hash, que fica igual entre tribunais.
        """
        return self.model_dump(by_alias=True, exclude_unset=True)


class Codificado(_Aberto):
    """`classe`, `sistema` e `formato`: codigo das tabelas do CNJ e nome."""

    codigo: int | None = None
    nome: str | None = None


class OrgaoJulgador(_Aberto):
    codigo: str | None = None
    nome: str | None = None
    codigo_municipio_ibge: int | None = Field(default=None, alias="codigoMunicipioIBGE")

    @field_validator("codigo", mode="before")
    @classmethod
    def _codigo_texto(cls, valor: Any) -> Any:
        return str(valor) if isinstance(valor, int) else valor


class Assunto(_Aberto):
    codigo: int | None = None
    nome: str | None = None


class Complemento(_Aberto):
    """Item de `complementosTabelados` (ex.: tipo de decisao, de audiencia)."""

    codigo: int | None = None
    valor: int | None = None
    nome: str | None = None
    descricao: str | None = None


class Movimento(_Aberto):
    codigo: int | None = None
    nome: str | None = None
    data_hora: str | None = Field(default=None, alias="dataHora")
    orgao_julgador: OrgaoJulgador | None = Field(default=None, alias="orgaoJulgador")
    complementos: list[Complemento] = Field(default_factory=list, alias="complementosTabelados")


def _achatar(valor: Any) -> Any:
    """Ha tribunal que manda `assuntos` como lista de listas; vira lista simples."""
    if not isinstance(valor, list):
        return valor
    plano: list[Any] = []
    for item in valor:
        plano.extend(_achatar(item) if isinstance(item, list) else [item])
    return plano


class Fonte(_Aberto):
    """O `_source` de um hit: um registro (um grau) do processo num tribunal.

    `assuntos` e `movimentos` nulos querem dizer "nao veio na resposta" (recorte
    por `_source`), e nao "o processo nao tem".
    """

    numero_processo: str = Field(default="", alias="numeroProcesso")
    id: str | None = None
    tribunal: str | None = None
    grau: str | None = None
    classe: Codificado | None = None
    sistema: Codificado | None = None
    formato: Codificado | None = None
    orgao_julgador: OrgaoJulgador | None = Field(default=None, alias="orgaoJulgador")
    nivel_sigilo: int | None = Field(default=None, alias="nivelSigilo")
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")
    data_hora_ultima_atualizacao: str | None = Field(default=None, alias="dataHoraUltimaAtualizacao")
    timestamp: str | None = Field(default=None, alias="@timestamp")
    assuntos: list[Assunto] | None = None
    movimentos: list[Movimento] | None = None

    @field_validator("assuntos", mode="before")
    @classmethod
    def _achatar_assuntos(cls, valor: Any) -> Any:
        return _achatar(valor)


class Hit(_Aberto):
    indice: str = Field(default="", alias="_index")
    doc_id: str | None = Field(default=None, alias="_id")
    score: float | None = Field(default=None, alias="_score")
    fonte: Fonte = Field(alias="_source")


class Total(_Aberto):
    value: int = 0
    relation: str | None = None


class Hits(_Aberto):
    total: Total | None = None
    hits: list[Hit] = Field(default_factory=list)


class RespostaBusca(_Aberto):
    """Corpo da resposta de `_search`, inclusive a de erro do Elasticsearch."""

    took: int | None = None
    timed_out: bool | None = None
    hits: Hits | None = None
    aggregations: dict[str, Any] | None = None
    error: Any = None


class RequisicaoBusca(_Aberto):
    """Corpo do POST `_search` (Query DSL do Elasticsearch)."""

    query: dict[str, Any] | None = None
    size: int | None = None
    track_total_hits: bool | int | None = None
    sort: list[Any] | None = None
    source: list[str] | str | bool | dict[str, Any] | None = Field(default=None, alias="_source")
    aggs: dict[str, Any] | None = None
