# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.6"]
# ///
"""Acervo relacional e append-only das observacoes da API publica DataJud (SQLite).

Por que relacional
------------------

A primeira versao (franklinbaldo/skills#125) guardava cada documento inteiro
como uma versao: capa e lista completa de movimentos num JSON so. Um andamento
novo copiava o historico inteiro, e a reindexacao do CNJ, que muda
`@timestamp` e `dataHoraUltimaAtualizacao` sem mudar nada no processo, tambem
criava versao. Medido em 2026-10-19: 4.820 documentos, 84 movimentos em media
(1.325 no maior), 18 KB por versao, 100 MB numa unica passada, e cada passada
seguinte acrescentaria quase o mesmo tanto.

Agora o documento e decomposto em tabelas, e so o que mudou ganha linha:

- `registros`: a identidade de um documento (indice + `_id`), uma linha para
  sempre;
- `capas`: classe, orgao, sistema, formato, sigilo, ajuizamento; linha nova so
  quando a capa muda de fato;
- `movimentos` e `assuntos`: um item por linha, identificado pelo hash do
  proprio conteudo e pela ocorrencia (o mesmo movimento identico aparece
  repetido no mesmo documento, e a repeticao se guarda);
- catalogos do que se repete entre milhares de itens: `tipos_movimento`
  (codigo e nome), `orgaos` e `complementos` (ligados ao movimento por
  `movimento_complementos`);
- `observacoes`: cada vez que um registro foi visto numa consulta, com os
  campos volateis da reindexacao e o `_score`;
- `presencas_movimento` e `presencas_assunto`: o item "entrou" ou "saiu" do
  registro naquela observacao. Andamento novo e uma linha aqui, nao uma copia;
- `fontes_brutas`: o hit cru, comprimido, so nas observacoes em que algo mudou
  (prova e reprocessamento).

O estado em qualquer data se reconstroi: capa vigente e os itens cuja ultima
presenca ate aquela data foi "entrou". Conferido na migracao do acervo real:
503 documentos reconstruidos identicos ao legado, movimento a movimento.

Contrato
--------

Cada tabela tem um modelo Pydantic (`Linha*`), e o DDL e gerado a partir dele:
a tabela e o modelo nao divergem. Toda funcao publica recebe e devolve modelos
(`RespostaRegistrada`, `HistoricoProcesso`, `EstadoProcesso`, `Estatisticas`,
`ResultadoMigracao`). Triggers proibem UPDATE e DELETE em todas as tabelas.

Recorte por `_source` nao e ausencia: campo fora do recorte nao foi observado,
e nao gera "saiu" nem capa nova.

As tabelas da primeira versao (`versoes_documento`, `observacoes_documento`)
ficam como estao, so para leitura; as observacoes delas sao decompostas nas
tabelas novas, em ordem cronologica, antes da primeira escrita ou leitura.

Nao armazena cabecalhos HTTP nem credenciais.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import types
import zlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, ClassVar, Literal, Union, get_args, get_origin

from datajud_modelos import Fonte, Hit, OrgaoJulgador, RequisicaoBusca, RespostaBusca
from pydantic import BaseModel, ConfigDict, Field

_LOCK = threading.Lock()


# ----------------------------------------------------------------------------
# Tabelas: um modelo por tabela, e o DDL sai dele
# ----------------------------------------------------------------------------
def _ref(tabela: str, *, nulo: bool = False) -> Any:
    extra = {"sql": f"REFERENCES {tabela}(id)"}
    return Field(default=None, json_schema_extra=extra) if nulo else Field(json_schema_extra=extra)


class Linha(BaseModel):
    """Linha de uma tabela do acervo.

    `CHAVE` vazia: a tabela tem `id` autoincremento. Preenchida: a chave e
    composta e a tabela e WITHOUT ROWID (ligacoes e presencas, que sao muitas
    e so se buscam pela chave).
    """

    model_config = ConfigDict(frozen=True)

    TABELA: ClassVar[str]
    RESTRICOES: ClassVar[tuple[str, ...]] = ()
    CHAVE: ClassVar[tuple[str, ...]] = ()


class LinhaComId(Linha):
    id: int | None = None
    """atribuido pelo SQLite."""


class LinhaConsulta(LinhaComId):
    """Uma requisicao HTTP a API, com sucesso ou nao."""

    TABELA = "consultas"

    observado_em: str
    tribunal: str
    requisicao_json: str
    resultado: Literal["ok", "erro"]
    resposta_meta_json: str | None = None
    """a resposta sem `hits.hits` (total, agregacoes, erro do Elasticsearch)."""
    erro: str | None = None


class LinhaRegistro(LinhaComId):
    """Um documento do DataJud: um grau de um processo num tribunal."""

    TABELA = "registros"
    RESTRICOES = ("UNIQUE(identidade)",)

    identidade: str
    """`<indice>:id:<_id>`, ou a tupla indice/numero/grau/orgao sem `_id`."""
    indice: str
    doc_id: str | None = None
    tribunal: str
    numero_processo: str
    grau: str | None = None
    fonte_id: str | None = None
    """o campo `id` do `_source`."""
    primeira_observacao: str


class LinhaOrgao(LinhaComId):
    """Catalogo de orgaos julgadores (da capa e dos movimentos)."""

    TABELA = "orgaos"
    RESTRICOES = ("UNIQUE(hash64)",)

    hash64: int
    """identidade pelo conteudo: 64 bits do SHA-256 do JSON canonico."""
    codigo: str | None = None
    nome: str | None = None
    municipio_ibge: int | None = None
    extras_json: str | None = None


class LinhaTipoMovimento(LinhaComId):
    """Catalogo de codigo e nome de movimento (Tabelas Processuais Unificadas)."""

    TABELA = "tipos_movimento"
    RESTRICOES = ("UNIQUE(hash64)",)

    hash64: int
    codigo: int | None = None
    nome: str | None = None


class LinhaComplemento(LinhaComId):
    """Catalogo de complementos tabelados (tipo e valor), ex.: tipo de decisao."""

    TABELA = "complementos"
    RESTRICOES = ("UNIQUE(hash64)",)

    hash64: int
    codigo: int | None = None
    valor: int | None = None
    nome: str | None = None
    descricao: str | None = None
    extras_json: str | None = None


class LinhaCapa(LinhaComId):
    """Versao da capa de um registro; os campos volateis ficam na observacao."""

    TABELA = "capas"
    RESTRICOES = ("UNIQUE(registro_id, hash64)",)

    registro_id: int = _ref("registros")
    hash64: int
    classe_codigo: int | None = None
    classe_nome: str | None = None
    sistema_codigo: int | None = None
    sistema_nome: str | None = None
    formato_codigo: int | None = None
    formato_nome: str | None = None
    orgao_id: int | None = _ref("orgaos", nulo=True)
    nivel_sigilo: int | None = None
    data_ajuizamento: str | None = None
    extras_json: str | None = None
    """campos da capa que a API mandou e que nao tem coluna."""


class LinhaAssunto(LinhaComId):
    TABELA = "assuntos"
    RESTRICOES = ("UNIQUE(registro_id, hash64, ocorrencia)",)

    registro_id: int = _ref("registros")
    hash64: int
    ocorrencia: int
    """0 para o primeiro item com este conteudo no registro, 1 para a repeticao..."""
    codigo: int | None = None
    nome: str | None = None
    extras_json: str | None = None


class LinhaMovimento(LinhaComId):
    TABELA = "movimentos"
    RESTRICOES = ("UNIQUE(registro_id, hash64, ocorrencia)",)

    registro_id: int = _ref("registros")
    hash64: int
    """do movimento inteiro, inclusive orgao e complementos."""
    ocorrencia: int
    tipo_id: int = _ref("tipos_movimento")
    data_hora: str | None = None
    orgao_id: int | None = _ref("orgaos", nulo=True)
    extras_json: str | None = None


class LinhaMovimentoComplemento(Linha):
    TABELA = "movimento_complementos"
    CHAVE = ("movimento_id", "ordem")

    movimento_id: int = _ref("movimentos")
    ordem: int
    complemento_id: int = _ref("complementos")


class LinhaObservacao(LinhaComId):
    """Um registro visto numa consulta."""

    TABELA = "observacoes"
    RESTRICOES = ("UNIQUE(observacao_v1_id)",)

    consulta_id: int = _ref("consultas")
    registro_id: int = _ref("registros")
    observado_em: str
    capa_id: int | None = _ref("capas", nulo=True)
    """nulo quando o recorte (`_source`) nao trouxe a capa inteira."""
    projecao_json: str | None = None
    """o `_source` da requisicao; nulo e documento completo."""
    volateis_json: str
    """`@timestamp`, `dataHoraUltimaAtualizacao`, `_score` e demais atributos do hit."""
    mudou: bool
    """primeira observacao do registro, capa nova ou alguma presenca."""
    observacao_v1_id: int | None = None
    """a observacao de `observacoes_documento` de onde esta foi migrada."""


class LinhaPresencaMovimento(Linha):
    TABELA = "presencas_movimento"
    CHAVE = ("movimento_id", "observacao_id")

    movimento_id: int = _ref("movimentos")
    observacao_id: int = _ref("observacoes")
    evento: Literal["entrou", "saiu"]


class LinhaPresencaAssunto(Linha):
    TABELA = "presencas_assunto"
    CHAVE = ("assunto_id", "observacao_id")

    assunto_id: int = _ref("assuntos")
    observacao_id: int = _ref("observacoes")
    evento: Literal["entrou", "saiu"]


class LinhaFonteBruta(LinhaComId):
    TABELA = "fontes_brutas"
    RESTRICOES = ("UNIQUE(observacao_id)",)

    observacao_id: int = _ref("observacoes")
    sha256: str
    """do JSON canonico descomprimido."""
    conteudo_zlib: bytes
    """o hit (`_index`, `_id`, `_source`) em JSON canonico, comprimido por zlib."""


class LinhaVersaoV1(LinhaComId):
    """Legado (#125): o documento inteiro por versao. So leitura."""

    TABELA = "versoes_documento"
    RESTRICOES = ("UNIQUE(identidade, sha256)",)

    identidade: str
    tribunal: str
    numero_processo: str
    grau: str | None = None
    sha256: str
    conteudo_json: str
    primeira_observacao: str


class LinhaObservacaoV1(LinhaComId):
    """Legado (#125). So leitura."""

    TABELA = "observacoes_documento"

    observado_em: str
    consulta_id: int = _ref("consultas")
    versao_id: int = _ref("versoes_documento")
    atributos_hit_json: str


TABELAS: tuple[type[Linha], ...] = (
    LinhaConsulta, LinhaRegistro, LinhaOrgao, LinhaTipoMovimento, LinhaComplemento,
    LinhaCapa, LinhaAssunto, LinhaMovimento, LinhaMovimentoComplemento,
    LinhaObservacao, LinhaPresencaMovimento, LinhaPresencaAssunto, LinhaFonteBruta,
)
LEGADO: tuple[type[Linha], ...] = (LinhaVersaoV1, LinhaObservacaoV1)

_INDICES = (
    "CREATE INDEX IF NOT EXISTS idx_consultas_tribunal_data ON consultas(tribunal, observado_em)",
    "CREATE INDEX IF NOT EXISTS idx_registros_numero ON registros(numero_processo)",
    "CREATE INDEX IF NOT EXISTS idx_observacoes_registro ON observacoes(registro_id, observado_em)",
    "CREATE INDEX IF NOT EXISTS idx_observacoes_consulta ON observacoes(consulta_id)",
    "CREATE INDEX IF NOT EXISTS idx_presencas_movimento_obs ON presencas_movimento(observacao_id)",
    "CREATE INDEX IF NOT EXISTS idx_presencas_assunto_obs ON presencas_assunto(observacao_id)",
)

_TIPOS_SQL = {int: "INTEGER", str: "TEXT", bytes: "BLOB", bool: "INTEGER", float: "REAL"}


def _coluna(nome: str, campo: Any) -> str:
    if nome == "id":
        return "id INTEGER PRIMARY KEY AUTOINCREMENT"
    tipo = campo.annotation
    nulo = False
    if get_origin(tipo) in (Union, types.UnionType):
        sem_nulo = [a for a in get_args(tipo) if a is not type(None)]
        nulo = len(sem_nulo) < len(get_args(tipo))
        (tipo,) = sem_nulo
    partes = [nome]
    if get_origin(tipo) is Literal:
        valores = ", ".join(f"'{v}'" for v in get_args(tipo))
        partes += ["TEXT", f"CHECK({nome} IN ({valores}))"]
    else:
        partes.append(_TIPOS_SQL[tipo])
    if not nulo:
        partes.append("NOT NULL")
    extra = (campo.json_schema_extra or {}).get("sql")
    if extra:
        partes.append(extra)
    return " ".join(partes)


def ddl(modelo: type[Linha]) -> str:
    """O CREATE TABLE da tabela, derivado do modelo."""
    colunas = [_coluna(nome, campo) for nome, campo in modelo.model_fields.items()]
    chave = [f"PRIMARY KEY({', '.join(modelo.CHAVE)})"] if modelo.CHAVE else []
    corpo = ",\n    ".join([*colunas, *chave, *modelo.RESTRICOES])
    sufixo = " WITHOUT ROWID" if modelo.CHAVE else ""
    return f"CREATE TABLE IF NOT EXISTS {modelo.TABELA} (\n    {corpo}\n){sufixo}"


def _inserir(con: sqlite3.Connection, linha: Linha, *, ignorar: bool = False) -> int | None:
    """INSERT da linha; devolve o id, ou None quando OR IGNORE nao inseriu."""
    dados = linha.model_dump(exclude={"id"})
    colunas = ", ".join(dados)
    marcas = ", ".join("?" for _ in dados)
    cursor = con.execute(
        f"INSERT {'OR IGNORE ' if ignorar else ''}INTO {linha.TABELA} ({colunas}) VALUES ({marcas})",
        tuple(dados.values()),
    )
    return cursor.lastrowid if cursor.rowcount else None


def _ler(con: sqlite3.Connection, modelo: type[Linha], onde: str = "1",
         parametros: tuple = (), *, sufixo: str = "") -> list:
    colunas = ", ".join(modelo.model_fields)
    linhas = con.execute(
        f"SELECT {colunas} FROM {modelo.TABELA} WHERE {onde} {sufixo}", parametros
    ).fetchall()
    return [modelo.model_validate(dict(zip(modelo.model_fields, x))) for x in linhas]


# ----------------------------------------------------------------------------
# Conexao
# ----------------------------------------------------------------------------
def caminho_banco() -> Path:
    """O banco padrao fica na area persistente do usuario, fora do Git."""
    configurado = os.environ.get("DATAJUD_SQLITE")
    if configurado:
        return Path(configurado).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "datajud" / "acervo.sqlite"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _hash64(valor: Any) -> int:
    """64 bits do SHA-256 do JSON canonico, como inteiro do SQLite.

    Basta para identidade dentro de um registro ou de um catalogo (centenas de
    milhares de itens: colisao na casa de 1 em 10^8); o hex de 64 caracteres
    custava 26 MB so na coluna de movimentos do acervo de 2026-10-19.
    """
    digest = hashlib.sha256(_json(valor).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _tabelas_existentes(con: sqlite3.Connection) -> set[str]:
    return {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


@contextmanager
def _transacao(con: sqlite3.Connection) -> Iterator[None]:
    con.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def _conexao(banco: Path | None = None) -> sqlite3.Connection:
    caminho = banco or caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # Transacoes explicitas (BEGIN IMMEDIATE): o calculo de presencas le o
    # estado atual antes de escrever, e dois processos nao podem intercalar.
    con = sqlite3.connect(caminho, timeout=30, isolation_level=None)
    try:
        con.execute("PRAGMA busy_timeout = 30000")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA foreign_keys = ON")
        with _transacao(con):
            for modelo in TABELAS:
                con.execute(ddl(modelo))
            for indice in _INDICES:
                con.execute(indice)
            existentes = _tabelas_existentes(con)
            for modelo in (*TABELAS, *LEGADO):
                if modelo.TABELA not in existentes:
                    continue
                for acao in ("UPDATE", "DELETE"):
                    con.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {modelo.TABELA}_sem_{acao.lower()} "
                        f"BEFORE {acao} ON {modelo.TABELA} BEGIN "
                        f"SELECT RAISE(ABORT, 'DataJud append-only: {acao} proibido'); END"
                    )
        return con
    except BaseException:
        con.close()
        raise


# ----------------------------------------------------------------------------
# Decomposicao de um hit
# ----------------------------------------------------------------------------
IDENTIDADE = ("numeroProcesso", "grau", "tribunal", "id")
"""campos do `_source` que vao para `registros`."""
VOLATEIS = ("@timestamp", "dataHoraUltimaAtualizacao")
"""mudam a cada reindexacao do CNJ sem que o processo mude: vao para a observacao."""
COLECOES = ("movimentos", "assuntos")
CAMPOS_CAPA = ("classe", "sistema", "formato", "orgaoJulgador", "nivelSigilo", "dataAjuizamento")

_Cache = dict[tuple[str, int], int]
"""(tabela, hash64) -> id dos catalogos, valido dentro de uma transacao."""


def _identidade(hit: dict[str, Any], tribunal: str) -> str:
    """Identidade logica estavel do documento, independente do seu conteudo."""
    indice = str(hit.get("_index") or f"api_publica_{tribunal}")
    doc_id = hit.get("_id")
    if doc_id is not None:
        return f"{indice}:id:{doc_id}"
    fonte = hit.get("_source") or {}
    orgao = fonte.get("orgaoJulgador") or {}
    return _json(
        [
            indice,
            fonte.get("numeroProcesso") or "",
            fonte.get("grau") or "",
            orgao.get("codigo") or orgao.get("nome") or "",
        ]
    )


def _observado(campo: str, projecao: Any) -> bool:
    """O recorte `_source` da requisicao trouxe este campo inteiro?"""
    if projecao is None or projecao is True:
        return True
    if projecao is False:
        return False
    if isinstance(projecao, str):
        projecao = [projecao]
    if isinstance(projecao, list):
        return any(fnmatch(campo, p) for p in projecao)
    if isinstance(projecao, dict):
        def lista(*chaves: str) -> list[str]:
            for chave in chaves:
                valor = projecao.get(chave)
                if valor:
                    return [valor] if isinstance(valor, str) else list(valor)
            return []

        incluidos = lista("includes", "include")
        excluidos = lista("excludes", "exclude")
        if incluidos and not any(fnmatch(campo, p) for p in incluidos):
            return False
        return not any(fnmatch(campo, p) or p.startswith(campo + ".") for p in excluidos)
    return False


def _extras(modelo: BaseModel) -> str | None:
    return _json(modelo.model_extra) if modelo.model_extra else None


def _catalogo(con: sqlite3.Connection, cache: _Cache, linha: LinhaComId) -> int:
    chave = (linha.TABELA, linha.hash64)
    if chave not in cache:
        _inserir(con, linha, ignorar=True)
        cache[chave] = con.execute(
            f"SELECT id FROM {linha.TABELA} WHERE hash64 = ?", (linha.hash64,)
        ).fetchone()[0]
    return cache[chave]


def _orgao(con: sqlite3.Connection, cache: _Cache, orgao: OrgaoJulgador | None) -> int | None:
    if orgao is None:
        return None
    return _catalogo(con, cache, LinhaOrgao(
        hash64=_hash64(orgao.bruto()), codigo=orgao.codigo, nome=orgao.nome,
        municipio_ibge=orgao.codigo_municipio_ibge, extras_json=_extras(orgao),
    ))


def _capa(con: sqlite3.Connection, cache: _Cache, registro_id: int, fonte: Fonte) -> LinhaCapa:
    recorte = {k: v for k, v in fonte.bruto().items()
               if k not in (*IDENTIDADE, *VOLATEIS, *COLECOES)}
    extras = {k: v for k, v in recorte.items() if k not in CAMPOS_CAPA}
    return LinhaCapa(
        registro_id=registro_id,
        hash64=_hash64(recorte),
        classe_codigo=fonte.classe.codigo if fonte.classe else None,
        classe_nome=fonte.classe.nome if fonte.classe else None,
        sistema_codigo=fonte.sistema.codigo if fonte.sistema else None,
        sistema_nome=fonte.sistema.nome if fonte.sistema else None,
        formato_codigo=fonte.formato.codigo if fonte.formato else None,
        formato_nome=fonte.formato.nome if fonte.formato else None,
        orgao_id=_orgao(con, cache, fonte.orgao_julgador),
        nivel_sigilo=fonte.nivel_sigilo,
        data_ajuizamento=fonte.data_ajuizamento,
        extras_json=_json(extras) if extras else None,
    )


def _com_ocorrencia(itens: list[Any]) -> list[tuple[int, int, Any]]:
    """(hash do conteudo, ocorrencia, item): repeticao identica nao colapsa."""
    vistos: Counter[int] = Counter()
    saida = []
    for item in itens:
        h = _hash64(item.bruto())
        saida.append((h, vistos[h], item))
        vistos[h] += 1
    return saida


def _presentes(con: sqlite3.Connection, tabela_item: str, tabela_presenca: str,
               coluna: str, registro_id: int) -> dict[tuple[int, int], tuple[int, bool]]:
    """(hash64, ocorrencia) -> (id, presente agora) de cada item ja visto no registro."""
    linhas = con.execute(
        f"""
        SELECT i.id, i.hash64, i.ocorrencia,
               (SELECT p.evento FROM {tabela_presenca} AS p
                WHERE p.{coluna} = i.id ORDER BY p.observacao_id DESC LIMIT 1) AS ultimo
        FROM {tabela_item} AS i WHERE i.registro_id = ?
        """,
        (registro_id,),
    ).fetchall()
    return {(h, oc): (item_id, ultimo == "entrou") for item_id, h, oc, ultimo in linhas}


class ObservacaoRegistrada(BaseModel):
    """Saida por hit de `registrar_resposta`."""

    registro_id: int
    observacao_id: int
    identidade: str
    primeira: bool
    capa_nova: bool
    movimentos_entraram: int
    movimentos_sairam: int
    assuntos_entraram: int
    assuntos_sairam: int

    @property
    def mudou(self) -> bool:
        return self.primeira or self.capa_nova or any((
            self.movimentos_entraram, self.movimentos_sairam,
            self.assuntos_entraram, self.assuntos_sairam,
        ))


def _novo_item(con: sqlite3.Connection, cache: _Cache, colecao: str, registro_id: int,
               h: int, ocorrencia: int, item: Any) -> int:
    if colecao == "assuntos":
        return _inserir(con, LinhaAssunto(
            registro_id=registro_id, hash64=h, ocorrencia=ocorrencia,
            codigo=item.codigo, nome=item.nome, extras_json=_extras(item),
        ))
    tipo = {k: v for k, v in item.bruto().items() if k in ("codigo", "nome")}
    movimento_id = _inserir(con, LinhaMovimento(
        registro_id=registro_id, hash64=h, ocorrencia=ocorrencia,
        tipo_id=_catalogo(con, cache, LinhaTipoMovimento(
            hash64=_hash64(tipo), codigo=item.codigo, nome=item.nome)),
        data_hora=item.data_hora,
        orgao_id=_orgao(con, cache, item.orgao_julgador),
        extras_json=_extras(item),
    ))
    for ordem, c in enumerate(item.complementos):
        _inserir(con, LinhaMovimentoComplemento(
            movimento_id=movimento_id, ordem=ordem,
            complemento_id=_catalogo(con, cache, LinhaComplemento(
                hash64=_hash64(c.bruto()), codigo=c.codigo, valor=c.valor, nome=c.nome,
                descricao=c.descricao, extras_json=_extras(c),
            )),
        ))
    return movimento_id


def _observar(con: sqlite3.Connection, cache: _Cache, *, consulta_id: int, observado_em: str,
              tribunal: str, hit_bruto: dict[str, Any], projecao: Any,
              observacao_v1_id: int | None = None) -> ObservacaoRegistrada:
    hit = Hit.model_validate(hit_bruto)
    fonte = hit.fonte
    indice = hit.indice or f"api_publica_{tribunal}"
    identidade = _identidade(hit_bruto, tribunal)
    _inserir(con, LinhaRegistro(
        identidade=identidade, indice=indice, doc_id=hit.doc_id,
        tribunal=indice.removeprefix("api_publica_"),
        numero_processo=fonte.numero_processo, grau=fonte.grau,
        fonte_id=fonte.id, primeira_observacao=observado_em,
    ), ignorar=True)
    registro_id = con.execute(
        "SELECT id FROM registros WHERE identidade = ?", (identidade,)
    ).fetchone()[0]
    primeira = con.execute(
        "SELECT 1 FROM observacoes WHERE registro_id = ? LIMIT 1", (registro_id,)
    ).fetchone() is None

    capa_id, capa_nova = None, False
    if all(_observado(c, projecao) for c in CAMPOS_CAPA):
        capa = _capa(con, cache, registro_id, fonte)
        _inserir(con, capa, ignorar=True)
        capa_id = con.execute(
            "SELECT id FROM capas WHERE registro_id = ? AND hash64 = ?",
            (registro_id, capa.hash64),
        ).fetchone()[0]
        anterior = con.execute(
            "SELECT capa_id FROM observacoes WHERE registro_id = ? AND capa_id IS NOT NULL "
            "ORDER BY id DESC LIMIT 1", (registro_id,),
        ).fetchone()
        capa_nova = not primeira and (anterior is None or anterior[0] != capa_id)

    entradas: dict[str, list[int]] = {}
    saidas: dict[str, list[int]] = {}
    for colecao, presenca, coluna in (
        ("movimentos", "presencas_movimento", "movimento_id"),
        ("assuntos", "presencas_assunto", "assunto_id"),
    ):
        itens = getattr(fonte, colecao)
        if itens is None or not _observado(colecao, projecao):
            continue  # nao veio: nada se conclui sobre presenca
        conhecidos = _presentes(con, colecao, presenca, coluna, registro_id)
        agora: set[int] = set()
        for h, ocorrencia, item in _com_ocorrencia(itens):
            if (h, ocorrencia) in conhecidos:
                agora.add(conhecidos[(h, ocorrencia)][0])
            else:
                agora.add(_novo_item(con, cache, colecao, registro_id, h, ocorrencia, item))
        antes = {item_id for item_id, presente in conhecidos.values() if presente}
        entradas[presenca] = sorted(agora - antes)
        saidas[presenca] = sorted(antes - agora)

    fonte_bruta = hit_bruto.get("_source") or {}
    volateis = {k: v for k, v in hit_bruto.items() if k not in ("_index", "_id", "_source")}
    volateis.update({k: fonte_bruta[k] for k in VOLATEIS if k in fonte_bruta})
    resultado = ObservacaoRegistrada(
        registro_id=registro_id, observacao_id=0, identidade=identidade,
        primeira=primeira, capa_nova=capa_nova,
        movimentos_entraram=len(entradas.get("presencas_movimento", [])),
        movimentos_sairam=len(saidas.get("presencas_movimento", [])),
        assuntos_entraram=len(entradas.get("presencas_assunto", [])),
        assuntos_sairam=len(saidas.get("presencas_assunto", [])),
    )
    observacao_id = _inserir(con, LinhaObservacao(
        consulta_id=consulta_id, registro_id=registro_id, observado_em=observado_em,
        capa_id=capa_id, projecao_json=None if projecao is None else _json(projecao),
        volateis_json=_json(volateis), mudou=resultado.mudou,
        observacao_v1_id=observacao_v1_id,
    ))
    for presenca, coluna, modelo in (
        ("presencas_movimento", "movimento_id", LinhaPresencaMovimento),
        ("presencas_assunto", "assunto_id", LinhaPresencaAssunto),
    ):
        for evento, ids in (("entrou", entradas.get(presenca, [])),
                            ("saiu", saidas.get(presenca, []))):
            for item_id in ids:
                _inserir(con, modelo(**{coluna: item_id}, observacao_id=observacao_id, evento=evento))
    if resultado.mudou:
        conteudo = _json({k: hit_bruto.get(k) for k in ("_index", "_id", "_source")})
        _inserir(con, LinhaFonteBruta(
            observacao_id=observacao_id, sha256=_sha(conteudo),
            conteudo_zlib=zlib.compress(conteudo.encode("utf-8"), 9),
        ))
    return resultado.model_copy(update={"observacao_id": observacao_id})


# ----------------------------------------------------------------------------
# Escrita
# ----------------------------------------------------------------------------
class RespostaRegistrada(BaseModel):
    """Saida de `registrar_resposta`."""

    consulta_id: int
    observacoes: list[ObservacaoRegistrada] = Field(default_factory=list)


def _envelope(resposta: dict[str, Any]) -> dict[str, Any]:
    """Tudo da resposta exceto hits.hits, que vao decompostos para as tabelas."""
    envelope = dict(resposta)
    hits = envelope.get("hits")
    if isinstance(hits, dict):
        envelope["hits"] = {k: v for k, v in hits.items() if k != "hits"}
    return envelope


def registrar_resposta(
    tribunal: str,
    requisicao: dict[str, Any],
    resposta: dict[str, Any],
    *,
    resultado: Literal["ok", "erro"] = "ok",
    erro: str | None = None,
    banco: Path | None = None,
) -> RespostaRegistrada:
    """Acrescenta a consulta e uma observacao por hit, de forma atomica.

    `requisicao` e `resposta` sao validados por `RequisicaoBusca` e
    `RespostaBusca`; os dicts crus continuam sendo a fonte do envelope gravado
    e da fonte bruta. Nao faz UPDATE nem DELETE.
    """
    if resultado not in ("ok", "erro"):
        raise ValueError("resultado deve ser ok ou erro")
    if not isinstance(resposta, dict):
        raise TypeError("resposta DataJud deve ser um objeto JSON")
    hits_container = resposta.get("hits") or {}
    if not isinstance(hits_container, dict):
        raise ValueError("hits deve ser um objeto JSON")
    hits = hits_container.get("hits") or []
    if not isinstance(hits, list):
        raise ValueError("hits.hits deve ser uma lista")
    for hit in hits:
        if not isinstance(hit, dict):
            raise ValueError("hit nao e um objeto")
        if not isinstance(hit.get("_source"), dict):
            raise ValueError("hit nao contem _source valido")
    RespostaBusca.model_validate(resposta)
    projecao = RequisicaoBusca.model_validate(requisicao).source
    observado_em = _agora()
    with _LOCK:
        con = _conexao(banco)
        try:
            _migrar_pendentes(con)
            with _transacao(con):
                consulta_id = _inserir(con, LinhaConsulta(
                    observado_em=observado_em, tribunal=tribunal,
                    requisicao_json=_json(requisicao), resultado=resultado,
                    resposta_meta_json=_json(_envelope(resposta)), erro=erro,
                ))
                saida = RespostaRegistrada(consulta_id=consulta_id)
                cache: _Cache = {}
                for hit in hits:
                    saida.observacoes.append(_observar(
                        con, cache, consulta_id=consulta_id, observado_em=observado_em,
                        tribunal=tribunal, hit_bruto=hit, projecao=projecao,
                    ))
            return saida
        finally:
            con.close()


def registrar_erro(
    tribunal: str,
    requisicao: dict[str, Any],
    erro: str,
    *,
    banco: Path | None = None,
) -> RespostaRegistrada:
    """Registra tentativas falhas; nao cria observacoes falsas de documentos."""
    return registrar_resposta(
        tribunal, requisicao, {}, resultado="erro", erro=str(erro), banco=banco
    )


# ----------------------------------------------------------------------------
# Migracao do legado (#125)
# ----------------------------------------------------------------------------
class ResultadoMigracao(BaseModel):
    """Saida de `migrar`."""

    migradas: int
    """observacoes do legado decompostas nesta chamada."""
    legado: int
    """observacoes em `observacoes_documento` (0 se a tabela nao existe)."""


def _legado_existe(con: sqlite3.Connection) -> bool:
    return {m.TABELA for m in LEGADO} <= _tabelas_existentes(con)


def _migrar_pendentes(con: sqlite3.Connection, *, lote: int = 200) -> int:
    """Decompoe as observacoes do legado ainda nao migradas, em ordem de id.

    A ordem importa: presenca e calculada contra o estado anterior, e as
    observacoes do legado sao anteriores a qualquer observacao nova, porque
    esta funcao roda antes de toda escrita e leitura. Retomavel:
    `observacao_v1_id` marca o que ja foi, e cada lote e uma transacao.
    """
    if not _legado_existe(con):
        return 0
    migradas = 0
    while True:
        ultimo = con.execute("SELECT MAX(observacao_v1_id) FROM observacoes").fetchone()[0] or 0
        pendentes = con.execute(
            """
            SELECT o.id, o.observado_em, o.consulta_id, o.atributos_hit_json,
                   v.conteudo_json, v.tribunal, c.requisicao_json
            FROM observacoes_documento AS o
            JOIN versoes_documento AS v ON v.id = o.versao_id
            JOIN consultas AS c ON c.id = o.consulta_id
            WHERE o.id > ? ORDER BY o.id LIMIT ?
            """,
            (ultimo, lote),
        ).fetchall()
        if not pendentes:
            return migradas
        with _transacao(con):
            cache: _Cache = {}
            for v1_id, observado_em, consulta_id, atributos, conteudo, tribunal, requisicao in pendentes:
                hit = {**json.loads(atributos), **json.loads(conteudo)}
                projecao = RequisicaoBusca.model_validate(json.loads(requisicao)).source
                _observar(con, cache, consulta_id=consulta_id, observado_em=observado_em,
                          tribunal=tribunal, hit_bruto=hit, projecao=projecao,
                          observacao_v1_id=v1_id)
                migradas += 1


def migrar(*, banco: Path | None = None) -> ResultadoMigracao:
    """Decompoe o legado nas tabelas relacionais; idempotente e retomavel."""
    with _LOCK:
        con = _conexao(banco)
        try:
            migradas = _migrar_pendentes(con)
            legado = (con.execute("SELECT COUNT(*) FROM observacoes_documento").fetchone()[0]
                      if _legado_existe(con) else 0)
            return ResultadoMigracao(migradas=migradas, legado=legado)
        finally:
            con.close()


# ----------------------------------------------------------------------------
# Leitura
# ----------------------------------------------------------------------------
@contextmanager
def _leitura(banco: Path | None) -> Iterator[sqlite3.Connection]:
    with _LOCK:
        con = _conexao(banco)
        try:
            _migrar_pendentes(con)
            yield con
        finally:
            con.close()


def _limite_em(em: str | date | datetime | None) -> str:
    """Instante ISO em UTC; data sem hora vale ate o fim do dia (UTC)."""
    if em is None:
        return "9999"
    if isinstance(em, str):
        em = date.fromisoformat(em) if len(em) == 10 else datetime.fromisoformat(em)
    if not isinstance(em, datetime):
        em = datetime.combine(em, time.max, tzinfo=timezone.utc)
    if em.tzinfo is None:
        em = em.replace(tzinfo=timezone.utc)
    return em.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _digitos(numero: str) -> str:
    return "".join(c for c in numero if c.isdigit())


class ItemMudanca(BaseModel):
    tipo: Literal["movimento", "assunto"]
    evento: Literal["entrou", "saiu"]
    codigo: int | None = None
    nome: str | None = None
    data_hora: str | None = None
    """so movimento."""


class MudancaObservada(BaseModel):
    """Uma observacao em que o registro mudou."""

    observacao_id: int
    consulta_id: int
    observado_em: str
    primeira: bool
    capa_nova: bool
    entraram: int
    sairam: int
    itens: list[ItemMudanca] = Field(default_factory=list)
    """so com `detalhar`."""


class HistoricoRegistro(BaseModel):
    registro: LinhaRegistro
    observacoes: int
    primeira_vista: str
    ultima_vista: str
    mudancas: list[MudancaObservada]
    """as mais recentes primeiro, ate `limite`."""


class HistoricoProcesso(BaseModel):
    """Saida de `historico`."""

    numero: str
    registros: list[HistoricoRegistro] = Field(default_factory=list)


_ITENS_DA_OBSERVACAO = (
    ("movimento", """
        SELECT p.evento, t.codigo, t.nome, i.data_hora FROM presencas_movimento AS p
        JOIN movimentos AS i ON i.id = p.movimento_id
        JOIN tipos_movimento AS t ON t.id = i.tipo_id
        WHERE p.observacao_id = ? ORDER BY i.data_hora, i.id"""),
    ("assunto", """
        SELECT p.evento, i.codigo, i.nome, NULL FROM presencas_assunto AS p
        JOIN assuntos AS i ON i.id = p.assunto_id
        WHERE p.observacao_id = ? ORDER BY i.id"""),
)


def historico(numero: str, *, limite: int = 100, detalhar: bool = False,
              banco: Path | None = None) -> HistoricoProcesso:
    """As mudancas de cada registro do processo, sem consultar a API."""
    digitos = _digitos(numero)
    limite = max(1, min(limite, 10000))
    saida = HistoricoProcesso(numero=digitos)
    with _leitura(banco) as con:
        for registro in _ler(con, LinhaRegistro, "numero_processo = ?", (digitos,),
                             sufixo="ORDER BY id"):
            n, primeira_id, primeira, ultima = con.execute(
                "SELECT COUNT(*), MIN(id), MIN(observado_em), MAX(observado_em) "
                "FROM observacoes WHERE registro_id = ?", (registro.id,),
            ).fetchone()
            if not n:
                continue
            mudancas = []
            for obs in _ler(con, LinhaObservacao, "registro_id = ? AND mudou = 1",
                            (registro.id,), sufixo=f"ORDER BY id DESC LIMIT {limite}"):
                itens = [
                    ItemMudanca(tipo=tipo, evento=evento, codigo=codigo, nome=nome,
                                data_hora=data_hora)
                    for tipo, sql in _ITENS_DA_OBSERVACAO
                    for evento, codigo, nome, data_hora in con.execute(sql, (obs.id,))
                ]
                capa_anterior = con.execute(
                    "SELECT capa_id FROM observacoes WHERE registro_id = ? AND id < ? "
                    "AND capa_id IS NOT NULL ORDER BY id DESC LIMIT 1", (registro.id, obs.id),
                ).fetchone()
                eh_primeira = obs.id == primeira_id
                mudancas.append(MudancaObservada(
                    observacao_id=obs.id, consulta_id=obs.consulta_id,
                    observado_em=obs.observado_em, primeira=eh_primeira,
                    capa_nova=(not eh_primeira and obs.capa_id is not None
                               and (capa_anterior is None or capa_anterior[0] != obs.capa_id)),
                    entraram=sum(i.evento == "entrou" for i in itens),
                    sairam=sum(i.evento == "saiu" for i in itens),
                    itens=itens if detalhar else [],
                ))
            saida.registros.append(HistoricoRegistro(
                registro=registro, observacoes=n, primeira_vista=primeira,
                ultima_vista=ultima, mudancas=mudancas,
            ))
    return saida


class CapaVigente(BaseModel):
    capa: LinhaCapa
    orgao: LinhaOrgao | None = None


class MovimentoVigente(BaseModel):
    movimento: LinhaMovimento
    tipo: LinhaTipoMovimento
    orgao: LinhaOrgao | None = None
    complementos: list[LinhaComplemento] = Field(default_factory=list)
    desde: str
    """observacao em que entrou (a ultima entrada, se saiu e voltou)."""


class EstadoRegistro(BaseModel):
    registro: LinhaRegistro
    observado_em: str
    """ultima observacao ate a data pedida."""
    capa: CapaVigente | None
    assuntos: list[LinhaAssunto]
    movimentos: list[MovimentoVigente]
    """em ordem de `data_hora`."""


class EstadoProcesso(BaseModel):
    """Saida de `estado`: o processo como o acervo o conhecia numa data."""

    numero: str
    em: str | None
    registros: list[EstadoRegistro] = Field(default_factory=list)


def _vigentes(con: sqlite3.Connection, tabela: str, presenca: str, coluna: str,
              registro_id: int, limite: str) -> dict[int, str]:
    """id -> data da entrada, dos itens cuja ultima presenca ate `limite` foi entrada."""
    linhas = con.execute(
        f"""
        SELECT ult.item_id, ult.evento, ult.observado_em FROM (
            SELECT p.{coluna} AS item_id, p.evento, o.observado_em,
                   ROW_NUMBER() OVER (PARTITION BY p.{coluna}
                                      ORDER BY o.observado_em DESC, p.observacao_id DESC) AS n
            FROM {presenca} AS p JOIN observacoes AS o ON o.id = p.observacao_id
            WHERE o.registro_id = ? AND o.observado_em <= ?
        ) AS ult WHERE ult.n = 1
        """,
        (registro_id, limite),
    ).fetchall()
    return {item_id: desde for item_id, evento, desde in linhas if evento == "entrou"}


def _por_id(con: sqlite3.Connection, modelo: type[LinhaComId], ids: set[int]) -> dict[int, Any]:
    if not ids:
        return {}
    marcas = ", ".join("?" for _ in ids)
    return {x.id: x for x in _ler(con, modelo, f"id IN ({marcas})", tuple(ids))}


def estado(numero: str, *, em: str | date | datetime | None = None,
           banco: Path | None = None) -> EstadoProcesso:
    """Capa, assuntos e movimentos vigentes de cada registro, sem consultar a API."""
    digitos = _digitos(numero)
    limite = _limite_em(em)
    saida = EstadoProcesso(numero=digitos, em=None if em is None else limite)
    with _leitura(banco) as con:
        for registro in _ler(con, LinhaRegistro, "numero_processo = ?", (digitos,),
                             sufixo="ORDER BY id"):
            ultima = con.execute(
                "SELECT MAX(observado_em) FROM observacoes "
                "WHERE registro_id = ? AND observado_em <= ?", (registro.id, limite),
            ).fetchone()[0]
            if ultima is None:
                continue
            capa_id = con.execute(
                "SELECT capa_id FROM observacoes WHERE registro_id = ? AND observado_em <= ? "
                "AND capa_id IS NOT NULL ORDER BY observado_em DESC, id DESC LIMIT 1",
                (registro.id, limite),
            ).fetchone()
            capa = _ler(con, LinhaCapa, "id = ?", (capa_id[0],))[0] if capa_id else None
            assuntos = _vigentes(con, "assuntos", "presencas_assunto", "assunto_id",
                                 registro.id, limite)
            entradas = _vigentes(con, "movimentos", "presencas_movimento", "movimento_id",
                                 registro.id, limite)
            movimentos = [m for m in _ler(con, LinhaMovimento, "registro_id = ?", (registro.id,),
                                          sufixo="ORDER BY data_hora, id") if m.id in entradas]
            tipos = _por_id(con, LinhaTipoMovimento, {m.tipo_id for m in movimentos})
            orgaos = _por_id(con, LinhaOrgao, {m.orgao_id for m in movimentos if m.orgao_id}
                             | ({capa.orgao_id} if capa and capa.orgao_id else set()))
            ligacoes: dict[int, list[int]] = {}
            if movimentos:
                for movimento_id, complemento_id in con.execute(
                    "SELECT mc.movimento_id, mc.complemento_id FROM movimento_complementos AS mc "
                    "JOIN movimentos AS m ON m.id = mc.movimento_id WHERE m.registro_id = ? "
                    "ORDER BY mc.movimento_id, mc.ordem", (registro.id,),
                ):
                    ligacoes.setdefault(movimento_id, []).append(complemento_id)
            complementos = _por_id(con, LinhaComplemento,
                                   {c for ids in ligacoes.values() for c in ids})
            saida.registros.append(EstadoRegistro(
                registro=registro, observado_em=ultima,
                capa=CapaVigente(capa=capa, orgao=orgaos.get(capa.orgao_id)) if capa else None,
                assuntos=[a for a in _ler(con, LinhaAssunto, "registro_id = ?", (registro.id,),
                                          sufixo="ORDER BY id") if a.id in assuntos],
                movimentos=[
                    MovimentoVigente(
                        movimento=m, tipo=tipos[m.tipo_id], orgao=orgaos.get(m.orgao_id),
                        complementos=[complementos[c] for c in ligacoes.get(m.id, [])],
                        desde=entradas[m.id],
                    )
                    for m in movimentos
                ],
            ))
    return saida


class Estatisticas(BaseModel):
    """Saida de `estatisticas`: linhas por tabela, sem consultar a API."""

    banco: str
    tabelas: dict[str, int]
    """linhas de cada tabela do acervo (inclusive as do legado, se existirem)."""
    consultas_com_erro: int
    observacoes_com_mudanca: int

    def __getitem__(self, tabela: str) -> int:
        return self.tabelas[tabela]


def estatisticas(*, banco: Path | None = None) -> Estatisticas:
    """Resumo para inspecao do acervo local; nao consulta o DataJud."""
    with _leitura(banco) as con:
        existentes = _tabelas_existentes(con)
        return Estatisticas(
            banco=str(banco or caminho_banco()),
            tabelas={
                m.TABELA: con.execute(f"SELECT COUNT(*) FROM {m.TABELA}").fetchone()[0]
                for m in (*TABELAS, *LEGADO) if m.TABELA in existentes
            },
            consultas_com_erro=con.execute(
                "SELECT COUNT(*) FROM consultas WHERE resultado = 'erro'").fetchone()[0],
            observacoes_com_mudanca=con.execute(
                "SELECT COUNT(*) FROM observacoes WHERE mudou = 1").fetchone()[0],
        )
