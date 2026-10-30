# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Modelos de entrada do lote e de saída de cada comando do `datajud.py`."""

from __future__ import annotations

from typing import Any

from datajud_cnj import NumeroCNJ
from datajud_modelos import Assunto, Codificado, Movimento, OrgaoJulgador
from pydantic import BaseModel, ConfigDict, Field


class FalhaIndice(BaseModel):
    """Indice que nao respondeu: o processo nao e ausente nele, so nao foi visto."""

    indice: str
    erro: str


class Registro(BaseModel):
    """Um registro (um grau) do processo num tribunal, como a API o devolveu.

    Guarda o hit cru (`_index`, `_source`) intacto: a capa e os movimentos sao
    o dado; as propriedades so leem o que todo consumidor precisa.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    indice_bruto: str = Field(default="", alias="_index")
    fonte: dict[str, Any] = Field(alias="_source")

    @property
    def tribunal(self) -> str:
        """`api_publica_tjro` -> `tjro`."""
        return self.indice_bruto.removeprefix("api_publica_")

    @property
    def numero(self) -> str:
        return self.fonte.get("numeroProcesso") or ""

    @property
    def grau(self) -> str | None:
        return self.fonte.get("grau")


class ConsultaLote(BaseModel):
    """Entrada de `consultar`: os numeros e onde procura-los."""

    numeros: list[NumeroCNJ]
    so_origem: bool = False
    """so o tribunal de origem, sem a familia (estado de origem + superiores)."""
    trabalhadores: int = Field(default=4, ge=1, le=16)
    """consultas simultaneas a API."""


class ProcessoConsultado(BaseModel):
    """Saida de `consultar` por processo; e tambem o JSON gravado pelo `lote`."""

    model_config = ConfigDict(populate_by_name=True)

    processo: NumeroCNJ
    origem: str | None
    """indice do tribunal de origem deduzido do numero (None: malformado ou STF)."""
    consultados: list[str]
    """indices perguntados; ausencia so vale para quem foi consultado e respondeu."""
    registros: list[Registro] = Field(default_factory=list, alias="hits")
    falhas: list[FalhaIndice] = Field(default_factory=list)

    @property
    def encontrado(self) -> bool:
        return bool(self.registros)

    @property
    def tribunais(self) -> list[str]:
        return list(dict.fromkeys(r.tribunal for r in self.registros))

    def para_disco(self) -> str:
        return self.model_dump_json(by_alias=True)


class FalhaLote(BaseModel):
    processo: NumeroCNJ
    indices: list[str]


class PresencaForaDaOrigem(BaseModel):
    processo: NumeroCNJ
    tambem_em: list[str]


class ResumoLote(BaseModel):
    """Saida do modo `lote`."""

    processos: int
    em_disco: int
    encontrados: int
    tambem_em_outro_tribunal: list[PresencaForaDaOrigem] = Field(default_factory=list)
    sem_tribunal: list[NumeroCNJ] = Field(default_factory=list)
    """numeros validos que nao revelam tribunal com indice na API (malformado, STF)."""
    invalidos: list[str] = Field(default_factory=list)
    """linhas do arquivo que nao sao numero CNJ."""
    falhas: list[FalhaLote] = Field(default_factory=list)
    saida: str


class DocumentoProcesso(BaseModel):
    """Um registro na saida `--json` do modo `processo`."""

    model_config = ConfigDict(populate_by_name=True)

    tribunal: str
    grau: str | None = None
    classe: Codificado | None = None
    assuntos: list[Assunto] | None = None
    orgao_julgador: OrgaoJulgador | None = Field(default=None, alias="orgaoJulgador")
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")
    ultima_atualizacao: str | None = Field(default=None, alias="ultimaAtualizacao")
    movimentos: list[Movimento] | None = None
    """nulo sem `--movimentos`."""


class SaidaProcesso(BaseModel):
    """Saida `--json` do modo `processo`."""

    processo: NumeroCNJ
    consultados: list[str]
    falhas: list[FalhaIndice]
    documentos: list[DocumentoProcesso]


class ItemBusca(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    numero_processo: str = Field(alias="numeroProcesso")
    grau: str | None = None
    classe: Codificado | None = None
    assuntos: list[Assunto] | None = None
    orgao_julgador: str | None = Field(default=None, alias="orgaoJulgador")
    """nome do orgao."""
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")


class SaidaBusca(BaseModel):
    """Saida `--json` do modo `buscar`."""

    tribunal: str
    total: int
    retornados: int
    resultados: list[ItemBusca]


class SaidaContagem(BaseModel):
    """Saida `--json` do modo `contar`."""

    tribunal: str
    total: int


class Faceta(BaseModel):
    chave: str | int
    qtd: int


class SaidaFacetas(BaseModel):
    """Saida `--json` do modo `facetas`."""

    tribunal: str
    total: int
    por: str
    buckets: list[Faceta]


class CodigoEncontrado(BaseModel):
    codigo: int | str
    nome: str
    qtd: int


class SaidaCodigos(BaseModel):
    """Saida `--json` do modo `codigos`."""

    por: str
    termo: str
    itens: list[CodigoEncontrado]


def _imprimir(modelo: BaseModel) -> None:
    print(modelo.model_dump_json(by_alias=True, indent=2))
