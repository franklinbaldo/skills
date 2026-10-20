# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.6"]
# ///
"""Acervo relacional e append-only das observacoes da API publica DataJud (SQLite).

Por que assim
-------------

A primeira versao (franklinbaldo/skills#125) guardava cada documento inteiro
como uma versao: um andamento novo copiava o historico inteiro, e a
reindexacao do CNJ tambem criava versao (100 MB numa passada sobre 3.448
processos). A segunda (#128) decompos o documento em tabelas (60 MB), mas
ainda gravava uma presenca "entrou" para cada um dos 406 mil movimentos, o hit
cru comprimido e uma linha de observacao por processo visto, mudasse ou nao:
cerca de 1,6 MB por passada diaria, quase tudo "visto, sem mudanca". Medido em
2026-10-20, das 2.373 observacoes de uma passada, 2.367 nao tinham mudanca.

Esta versao (3) guarda so o que nao se deduz:

- `registros`: a identidade de um documento (indice + `_id`);
- `capas`: classe, orgao, sistema, formato, sigilo, ajuizamento; linha nova so
  quando a capa muda;
- `movimentos` e `assuntos`: um item por linha, identificado pelo hash do
  proprio conteudo e pela ocorrencia (o mesmo movimento identico aparece
  repetido no mesmo documento). O item guarda a observacao em que entrou: a
  entrada nao precisa de linha propria. A data do movimento vai em segundos
  (`instante`); o texto so se guarda quando foge do formato da API;
- catalogos do que se repete: `tipos_movimento`, `orgaos`, `complementos`
  (ligados ao movimento por `movimento_complementos`);
- `observacoes`: so as que trouxeram mudanca (primeira vez, capa nova, item
  que entrou ou saiu), com os campos volateis da reindexacao e o `_score`;
- `vistas`: o registro visto sem mudanca numa consulta, numa linha de dois
  inteiros;
- `presencas_movimento` e `presencas_assunto`: so a saida e a reentrada de um
  item (retificacao na fonte), que sao raras;
- `consultas`: cada requisicao, com o corpo comprimido e o recorte `_source`
  em coluna propria, porque e ele que diz o que a consulta observou.

O hit cru deixou de ser guardado: a migracao da versao 2 reconstruiu os 4.820
documentos identicos a partir das tabelas, e a copia so repetia o que elas ja
dizem.

O estado em qualquer data se reconstroi: capa vigente e os itens que entraram
ate ali e cuja ultima presenca nao foi "saiu".

Contrato
--------

Cada tabela tem um modelo Pydantic (`Linha*`), e o DDL e gerado a partir dele.
Toda funcao publica recebe e devolve modelos (`RespostaRegistrada`,
`HistoricoProcesso`, `EstadoProcesso`, `Novidades`, `Estatisticas`,
`ResultadoMigracao`). Triggers proibem UPDATE e DELETE em todas as tabelas.

Recorte por `_source` nao e ausencia: campo fora do recorte nao foi observado,
nao gera "saiu" nem capa nova, e o `estado` diz quando cada colecao foi vista
pela ultima vez (ou que nunca foi).

Banco de versao anterior (a #125, a #128, ou as duas no mesmo arquivo) e
migrado por arquivo na primeira abertura: o novo sai das tabelas antigas, sem
consultar a API, e o antigo fica ao lado como `<nome>-antes-v3-<instante>.sqlite`.

Nao armazena cabecalhos HTTP nem credenciais.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time as relogio
import types
import uuid
import zlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, ClassVar, Literal, Union, get_args, get_origin

from datajud_modelos import Fonte, Hit, OrgaoJulgador, RequisicaoBusca, RespostaBusca
from pydantic import BaseModel, ConfigDict, Field, computed_field

_LOCK = threading.Lock()
VERSAO = 3
EM_TROCA = -1
"""`user_version` do arquivo antigo depois de copiado e antes de ceder o nome ao novo."""
ESPERA_TROCA = 60.0


class _ArquivoTrocado(Exception):
    """O arquivo aberto deixou de ser o acervo atual (conversao em curso ou concluida)."""


# ----------------------------------------------------------------------------
# Tabelas: um modelo por tabela, e o DDL sai dele
# ----------------------------------------------------------------------------
def _ref(tabela: str, *, nulo: bool = False) -> Any:
    extra = {"sql": f"REFERENCES {tabela}(id)"}
    return Field(default=None, json_schema_extra=extra) if nulo else Field(json_schema_extra=extra)


class Linha(BaseModel):
    """Linha de uma tabela do acervo.

    `CHAVE` vazia: a tabela tem `id` autoincremento. Preenchida: a chave e
    composta e a tabela e WITHOUT ROWID (ligacoes, vistas e presencas, que so se
    buscam pela chave).
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
    requisicao_zlib: bytes
    """o corpo da requisicao em JSON canonico, comprimido (o lote leva 100 numeros)."""
    projecao_json: str | None = None
    """o `_source` da requisicao; nulo e documento completo."""
    resultado: Literal["ok", "erro"]
    resposta_meta_json: str | None = None
    """a resposta sem `hits.hits` (total, agregacoes, erro do Elasticsearch)."""
    erro: str | None = None

    def requisicao(self) -> dict[str, Any]:
        return json.loads(zlib.decompress(self.requisicao_zlib))


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


class LinhaObservacao(LinhaComId):
    """Um registro visto numa consulta, quando algo nele mudou."""

    TABELA = "observacoes"

    consulta_id: int = _ref("consultas")
    registro_id: int = _ref("registros")
    observado_em: str
    capa_id: int | None = _ref("capas", nulo=True)
    """nulo quando o recorte (`_source`) nao trouxe a capa inteira."""
    volateis_json: str
    """`@timestamp`, `dataHoraUltimaAtualizacao`, `_score` e demais atributos do hit."""


class LinhaVista(Linha):
    """Um registro visto numa consulta sem mudanca nenhuma."""

    TABELA = "vistas"
    CHAVE = ("registro_id", "consulta_id")

    registro_id: int = _ref("registros")
    consulta_id: int = _ref("consultas")


class LinhaAssunto(LinhaComId):
    TABELA = "assuntos"
    RESTRICOES = ("UNIQUE(registro_id, hash64, ocorrencia)",)

    registro_id: int = _ref("registros")
    hash64: int
    ocorrencia: int
    """0 para o primeiro item com este conteudo no registro, 1 para a repeticao..."""
    observacao_id: int = _ref("observacoes")
    """a observacao em que o item entrou."""
    codigo: int | None = None
    nome: str | None = None
    extras_json: str | None = None


_EPOCA = datetime(1970, 1, 1, tzinfo=timezone.utc)
_DATA_DA_API = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.000Z")


def _instante(data_hora: str | None) -> tuple[int | None, str | None]:
    """(segundos UTC, texto a guardar): o texto so quando a forma nao e a da API.

    Em 2026-10-20 as 406 mil datas do acervo tinham a forma `2024-01-10T10:00:00.000Z`,
    que se refaz exata dos segundos: guardadas como inteiro, custam 4 bytes e nao 24.
    """
    if data_hora is None:
        return None, None
    if _DATA_DA_API.fullmatch(data_hora):
        momento = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
        return int(momento.timestamp()), None
    try:
        momento = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        return int(momento.timestamp()), data_hora
    except ValueError:
        return None, data_hora


def _data_hora(instante: int | None, texto: str | None) -> str | None:
    if texto is not None or instante is None:
        return texto
    # Soma a 1970 em vez de `fromtimestamp`, que no Windows recusa instante negativo
    # (o acervo tem movimento datado de antes de 1970).
    return (_EPOCA + timedelta(seconds=instante)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class LinhaMovimento(LinhaComId):
    TABELA = "movimentos"
    RESTRICOES = ("UNIQUE(registro_id, hash64, ocorrencia)",)

    registro_id: int = _ref("registros")
    hash64: int
    """do movimento inteiro, inclusive orgao e complementos."""
    ocorrencia: int
    observacao_id: int = _ref("observacoes")
    """a observacao em que o item entrou."""
    tipo_id: int = _ref("tipos_movimento")
    instante: int | None = None
    """`dataHora` em segundos UTC."""
    data_hora_texto: str | None = None
    """`dataHora` como veio, so quando nao tem a forma `AAAA-MM-DDTHH:MM:SS.000Z`."""
    orgao_id: int | None = _ref("orgaos", nulo=True)
    extras_json: str | None = None

    @computed_field
    @property
    def data_hora(self) -> str | None:
        """`dataHora` como a API a mandou."""
        return _data_hora(self.instante, self.data_hora_texto)


class LinhaMovimentoComplemento(Linha):
    TABELA = "movimento_complementos"
    CHAVE = ("movimento_id", "ordem")

    movimento_id: int = _ref("movimentos")
    ordem: int
    complemento_id: int = _ref("complementos")


class LinhaPresencaMovimento(Linha):
    """Saida ou reentrada de um movimento; a entrada esta no proprio movimento."""

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


TABELAS: tuple[type[Linha], ...] = (
    LinhaConsulta, LinhaRegistro, LinhaOrgao, LinhaTipoMovimento, LinhaComplemento,
    LinhaCapa, LinhaObservacao, LinhaVista, LinhaAssunto, LinhaMovimento,
    LinhaMovimentoComplemento, LinhaPresencaMovimento, LinhaPresencaAssunto,
)

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
    dados = linha.model_dump(include=set(type(linha).model_fields) - {"id"})
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


def _por_id(con: sqlite3.Connection, modelo: type[LinhaComId], ids: set[int]) -> dict[int, Any]:
    if not ids:
        return {}
    marcas = ", ".join("?" for _ in ids)
    return {x.id: x for x in _ler(con, modelo, f"id IN ({marcas})", tuple(ids))}


# ----------------------------------------------------------------------------
# Conexao e migracao de arquivo
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
    milhares de itens: colisao na casa de 1 em 10^8).
    """
    digest = hashlib.sha256(_json(valor).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _tabelas_existentes(con: sqlite3.Connection, esquema: str = "main") -> set[str]:
    return {x[0] for x in con.execute(f"SELECT name FROM {esquema}.sqlite_master WHERE type = 'table'")}


@contextmanager
def _transacao(con: sqlite3.Connection, modo: str = "IMMEDIATE") -> Iterator[None]:
    con.execute(f"BEGIN {modo}")
    try:
        yield
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def _conferir_versao(con: sqlite3.Connection) -> None:
    """Dentro da transacao: o arquivo ainda e o acervo atual, e nao o antigo em troca."""
    versao = con.execute("PRAGMA user_version").fetchone()[0]
    if versao == EM_TROCA or (versao != VERSAO and _tabelas_existentes(con) - {"sqlite_sequence"}):
        raise _ArquivoTrocado(versao)


def _abrir(caminho: Path, *, novo: bool = False) -> sqlite3.Connection:
    """Abre (e cria, se preciso) um banco na versao atual.

    Recusa (`_ArquivoTrocado`) o arquivo de versao anterior ou em troca: criar as
    tabelas nele, ou carimbar a versao, faria um processo que esperava a trava da
    conversao gravar no arquivo que virou backup.
    """
    # Transacoes explicitas (BEGIN IMMEDIATE): o calculo de presencas le o
    # estado atual antes de escrever, e dois processos nao podem intercalar.
    con = sqlite3.connect(caminho, timeout=30, isolation_level=None)
    try:
        con.execute("PRAGMA busy_timeout = 30000")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA foreign_keys = ON")
        with _transacao(con):
            if not novo:
                _conferir_versao(con)
            for modelo in TABELAS:
                con.execute(ddl(modelo))
            for indice in _INDICES:
                con.execute(indice)
            for modelo in TABELAS:
                for acao in ("UPDATE", "DELETE"):
                    con.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {modelo.TABELA}_sem_{acao.lower()} "
                        f"BEFORE {acao} ON {modelo.TABELA} BEGIN "
                        f"SELECT RAISE(ABORT, 'DataJud append-only: {acao} proibido'); END"
                    )
            con.execute(f"PRAGMA user_version = {VERSAO}")
        return con
    except BaseException:
        con.close()
        raise


class ResultadoMigracao(BaseModel):
    """Saida de `migrar`: o que a abertura do banco converteu."""

    origem: Literal["nada", "v2", "legado", "v2+legado"]
    """`v2`: tabelas da #128; `legado`: documento inteiro por versao (#125)."""
    observacoes: int = 0
    """observacoes de origem convertidas (com e sem mudanca)."""
    backup: str | None = None
    """o arquivo anterior, preservado ao lado do novo."""


_ULTIMA_MIGRACAO: ResultadoMigracao | None = None


def _versao(caminho: Path) -> int | None:
    """`user_version` do arquivo, ou None se ainda nao ha acervo nele."""
    if not caminho.exists() or caminho.stat().st_size == 0:
        return None
    con = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        if not _tabelas_existentes(con) - {"sqlite_sequence"}:
            return None
        return con.execute("PRAGMA user_version").fetchone()[0]
    finally:
        con.close()


def _conexao(banco: Path | None = None) -> sqlite3.Connection:
    """Conexao com o acervo atual, convertendo antes o de versao anterior.

    Arquivo em troca (`EM_TROCA`) e de outro processo que acabou de copia-lo:
    espera o novo assumir o nome. Passado o prazo, a troca morreu no meio, e o
    antigo, que nao foi alterado alem do carimbo, e convertido de novo.
    """
    global _ULTIMA_MIGRACAO
    caminho = banco or caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    prazo = relogio.monotonic() + ESPERA_TROCA
    while True:
        versao = _versao(caminho)
        if versao == EM_TROCA and relogio.monotonic() < prazo:
            relogio.sleep(0.2)
            continue
        try:
            if versao is not None and versao != VERSAO:
                _ULTIMA_MIGRACAO = _migrar_arquivo(caminho, troca_morta=versao == EM_TROCA)
            return _abrir(caminho)
        except _ArquivoTrocado:
            if relogio.monotonic() >= prazo:
                raise RuntimeError(f"{caminho} continua em conversao depois de {ESPERA_TROCA:.0f} s") from None
            relogio.sleep(0.2)


def _migrar_arquivo(caminho: Path, *, troca_morta: bool = False) -> ResultadoMigracao:
    """Constroi o banco v3 num arquivo novo a partir do antigo, e troca os dois.

    Nada se apaga: o antigo fica ao lado. A conversao le as tabelas antigas, sem
    consultar a API; o arquivo novo so assume o nome depois de completo.

    Da copia ate a troca, nenhuma escrita pode cair no antigo, senao ela iria
    para o backup e faltaria no novo (achado em pge-iperon/judicial#659). A
    trava de escrita do antigo fica com a conversao durante a copia; antes de
    solta-la, o antigo e carimbado `EM_TROCA`, e quem o abrir depois (inclusive
    quem esperava a trava) recusa e espera o novo.

    Dois processos podem decidir converter ao mesmo tempo: a trava vem antes
    de qualquer arquivo ser tocado, a versao e conferida de novo sob ela, e cada
    conversao constroi num temporario so seu (achado em pge-iperon/judicial#659).
    `troca_morta`: o antigo ficou `EM_TROCA` alem do prazo, e se converte de novo.
    """
    trava = sqlite3.connect(caminho, timeout=30, isolation_level=None)
    trava.execute("PRAGMA busy_timeout = 30000")
    trava.execute("BEGIN IMMEDIATE")
    original = trava.execute("PRAGMA user_version").fetchone()[0]
    tabelas = _tabelas_existentes(trava) - {"sqlite_sequence"}
    if original == VERSAO or not tabelas or (original == EM_TROCA and not troca_morta):
        # Outro processo converteu (ou esta trocando) enquanto esperavamos a trava.
        trava.execute("ROLLBACK")
        trava.close()
        raise _ArquivoTrocado(original)
    if original == EM_TROCA:
        original = 0
    temporario = caminho.with_name(f"{caminho.stem}.v3-em-construcao-{uuid.uuid4().hex[:12]}.sqlite")
    try:
        resultado = _construir(caminho, temporario)
        trava.execute(f"PRAGMA user_version = {EM_TROCA}")
        trava.execute("COMMIT")
    except BaseException:
        trava.execute("ROLLBACK")
        trava.close()
        for resto in (temporario, Path(f"{temporario}-wal"), Path(f"{temporario}-shm")):
            resto.unlink(missing_ok=True)
        raise
    trava.close()
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = caminho.with_name(f"{caminho.stem}-antes-v3-{carimbo}{caminho.suffix}")
    try:
        # No Windows, quem esperava a trava ainda segura o arquivo por um instante:
        # ao ver `EM_TROCA` ele o solta, e a troca tenta de novo.
        prazo = relogio.monotonic() + 10
        while True:
            try:
                caminho.replace(backup)
                break
            except PermissionError:
                if relogio.monotonic() >= prazo:
                    raise
                relogio.sleep(0.2)
    except PermissionError as erro:
        # No Windows, arquivo aberto noutro processo nao se renomeia: o antigo volta
        # a versao que tinha, e a conversao se repete na proxima abertura.
        restaura = sqlite3.connect(caminho, timeout=30)
        restaura.execute(f"PRAGMA user_version = {original}")
        restaura.commit()
        restaura.close()
        temporario.unlink(missing_ok=True)
        raise RuntimeError(
            f"{caminho} esta aberto noutro processo; feche-o para converter o acervo para a versao "
            f"{VERSAO} (uv run scripts/datajud.py migrar)") from erro
    for sufixo in ("-wal", "-shm"):
        anexo = Path(f"{caminho}{sufixo}")
        if anexo.exists():
            anexo.replace(Path(f"{backup}{sufixo}"))
    temporario.replace(caminho)
    for sufixo in ("-wal", "-shm"):
        Path(f"{temporario}{sufixo}").unlink(missing_ok=True)
    return resultado.model_copy(update={"backup": str(backup)})


def _construir(caminho: Path, temporario: Path) -> ResultadoMigracao:
    """O banco v3 em `temporario`, a partir das tabelas de `caminho`."""
    novo = _abrir(temporario, novo=True)
    try:
        novo.execute("ATTACH DATABASE ? AS antigo", (f"file:{caminho.as_posix()}?mode=ro",))
    except sqlite3.OperationalError:
        novo.execute("ATTACH DATABASE ? AS antigo", (str(caminho),))
    try:
        antigas = _tabelas_existentes(novo, "antigo")
        tem_v2 = "presencas_movimento" in antigas
        tem_legado = {"versoes_documento", "observacoes_documento"} <= antigas
        convertidas = 0
        # DEFERRED: so o arquivo novo recebe trava de escrita; o antigo, anexado, e so
        # lido, e a trava de escrita dele e da conversao (`_migrar_arquivo`).
        with _transacao(novo, "DEFERRED"):
            if "consultas" in antigas:
                _copiar_consultas(novo)
            if tem_v2:
                convertidas += _converter_v2(novo)
            if tem_legado:
                convertidas += _reproduzir_legado(novo, desde_v2=tem_v2)
        novo.execute("DETACH DATABASE antigo")
    finally:
        novo.close()
    origem = "v2+legado" if tem_v2 and tem_legado else "v2" if tem_v2 else "legado" if tem_legado else "nada"
    return ResultadoMigracao(origem=origem, observacoes=convertidas)


def _copiar_consultas(con: sqlite3.Connection) -> None:
    for linha in con.execute(
        "SELECT id, observado_em, tribunal, requisicao_json, resultado, resposta_meta_json, erro "
        "FROM antigo.consultas ORDER BY id"
    ).fetchall():
        id_, observado_em, tribunal, requisicao, resultado, meta, erro = linha
        corpo = json.loads(requisicao)
        projecao = RequisicaoBusca.model_validate(corpo).source
        con.execute(
            "INSERT INTO consultas (id, observado_em, tribunal, requisicao_zlib, projecao_json, "
            "resultado, resposta_meta_json, erro) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (id_, observado_em, tribunal, zlib.compress(_json(corpo).encode("utf-8"), 9),
             None if projecao is None else _json(projecao), resultado, meta, erro),
        )


def _converter_v2(con: sqlite3.Connection) -> int:
    """Tabelas da #128 para a v3, preservando os ids."""
    for tabela in ("registros", "orgaos", "tipos_movimento", "complementos", "capas"):
        colunas = ", ".join(next(m for m in TABELAS if m.TABELA == tabela).model_fields)
        con.execute(f"INSERT INTO {tabela} ({colunas}) SELECT {colunas} FROM antigo.{tabela}")
    con.execute(
        "INSERT INTO observacoes (id, consulta_id, registro_id, observado_em, capa_id, volateis_json) "
        "SELECT id, consulta_id, registro_id, observado_em, capa_id, volateis_json "
        "FROM antigo.observacoes WHERE mudou = 1"
    )
    con.execute(
        "INSERT OR IGNORE INTO vistas (registro_id, consulta_id) "
        "SELECT registro_id, consulta_id FROM antigo.observacoes WHERE mudou = 0"
    )
    for tabela, presenca, coluna in (("assuntos", "presencas_assunto", "assunto_id"),
                                     ("movimentos", "presencas_movimento", "movimento_id")):
        entrada = dict(con.execute(
            f"SELECT {coluna}, MIN(observacao_id) FROM antigo.{presenca} "
            f"WHERE evento = 'entrou' GROUP BY {coluna}"
        ).fetchall())
        if tabela == "assuntos":
            linhas = con.execute(
                "SELECT id, registro_id, hash64, ocorrencia, codigo, nome, extras_json "
                "FROM antigo.assuntos ORDER BY id").fetchall()
            con.executemany(
                "INSERT INTO assuntos (id, registro_id, hash64, ocorrencia, observacao_id, codigo, "
                "nome, extras_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(i, r, h, o, entrada[i], c, n, e) for i, r, h, o, c, n, e in linhas],
            )
        else:
            linhas = con.execute(
                "SELECT id, registro_id, hash64, ocorrencia, tipo_id, data_hora, orgao_id, extras_json "
                "FROM antigo.movimentos ORDER BY id").fetchall()
            con.executemany(
                "INSERT INTO movimentos (id, registro_id, hash64, ocorrencia, observacao_id, tipo_id, "
                "instante, data_hora_texto, orgao_id, extras_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(i, r, h, o, entrada[i], t, *_instante(d), og, e) for i, r, h, o, t, d, og, e in linhas],
            )
        con.execute(
            f"INSERT INTO {presenca} ({coluna}, observacao_id, evento) "
            f"SELECT p.{coluna}, p.observacao_id, p.evento FROM antigo.{presenca} AS p "
            f"WHERE NOT (p.evento = 'entrou' AND p.observacao_id = ("
            f"SELECT MIN(q.observacao_id) FROM antigo.{presenca} AS q "
            f"WHERE q.{coluna} = p.{coluna} AND q.evento = 'entrou'))"
        )
    con.execute(
        "INSERT INTO movimento_complementos (movimento_id, ordem, complemento_id) "
        "SELECT movimento_id, ordem, complemento_id FROM antigo.movimento_complementos"
    )
    return con.execute("SELECT COUNT(*) FROM antigo.observacoes").fetchone()[0]


def _reproduzir_legado(con: sqlite3.Connection, *, desde_v2: bool) -> int:
    """Observacoes da #125 que a v2 nao chegou a decompor, em ordem."""
    ultimo = 0
    if desde_v2:
        colunas = {x[1] for x in con.execute("PRAGMA antigo.table_info(observacoes)")}
        if "observacao_v1_id" in colunas:
            ultimo = con.execute(
                "SELECT COALESCE(MAX(observacao_v1_id), 0) FROM antigo.observacoes").fetchone()[0]
    pendentes = con.execute(
        """
        SELECT o.observado_em, o.consulta_id, o.atributos_hit_json, v.conteudo_json, v.tribunal,
               c.projecao_json
        FROM antigo.observacoes_documento AS o
        JOIN antigo.versoes_documento AS v ON v.id = o.versao_id
        JOIN consultas AS c ON c.id = o.consulta_id
        WHERE o.id > ? ORDER BY o.id
        """,
        (ultimo,),
    ).fetchall()
    cache: _Cache = {}
    for observado_em, consulta_id, atributos, conteudo, tribunal, projecao in pendentes:
        _observar(con, cache, consulta_id=consulta_id, observado_em=observado_em,
                  tribunal=tribunal, hit_bruto={**json.loads(atributos), **json.loads(conteudo)},
                  projecao=None if projecao is None else json.loads(projecao))
    return len(pendentes)


def migrar(*, banco: Path | None = None) -> ResultadoMigracao:
    """Converte para a versao atual o banco de versao anterior; sem nada a fazer, `nada`."""
    global _ULTIMA_MIGRACAO
    with _LOCK:
        _ULTIMA_MIGRACAO = None
        _conexao(banco).close()
        resultado, _ULTIMA_MIGRACAO = _ULTIMA_MIGRACAO, None
        return resultado or ResultadoMigracao(origem="nada")


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
    """(hash64, ocorrencia) -> (id, presente agora): sem presenca registrada, segue a entrada."""
    linhas = con.execute(
        f"""
        SELECT i.id, i.hash64, i.ocorrencia,
               (SELECT p.evento FROM {tabela_presenca} AS p
                WHERE p.{coluna} = i.id ORDER BY p.observacao_id DESC LIMIT 1) AS ultimo
        FROM {tabela_item} AS i WHERE i.registro_id = ?
        """,
        (registro_id,),
    ).fetchall()
    return {(h, oc): (item_id, ultimo != "saiu") for item_id, h, oc, ultimo in linhas}


class ObservacaoRegistrada(BaseModel):
    """Saida por hit de `registrar_resposta`."""

    registro_id: int
    observacao_id: int | None
    """nulo quando nada mudou: o registro ficou so em `vistas`."""
    identidade: str
    primeira: bool
    capa_nova: bool
    movimentos_entraram: int
    movimentos_sairam: int
    assuntos_entraram: int
    assuntos_sairam: int

    @property
    def mudou(self) -> bool:
        return self.observacao_id is not None


def _novo_item(con: sqlite3.Connection, cache: _Cache, colecao: str, registro_id: int,
               observacao_id: int, h: int, ocorrencia: int, item: Any) -> None:
    if colecao == "assuntos":
        _inserir(con, LinhaAssunto(
            registro_id=registro_id, hash64=h, ocorrencia=ocorrencia, observacao_id=observacao_id,
            codigo=item.codigo, nome=item.nome, extras_json=_extras(item),
        ))
        return
    tipo = {k: v for k, v in item.bruto().items() if k in ("codigo", "nome")}
    instante, texto = _instante(item.data_hora)
    movimento_id = _inserir(con, LinhaMovimento(
        registro_id=registro_id, hash64=h, ocorrencia=ocorrencia, observacao_id=observacao_id,
        tipo_id=_catalogo(con, cache, LinhaTipoMovimento(
            hash64=_hash64(tipo), codigo=item.codigo, nome=item.nome)),
        instante=instante, data_hora_texto=texto,
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


def _observar(con: sqlite3.Connection, cache: _Cache, *, consulta_id: int, observado_em: str,
              tribunal: str, hit_bruto: dict[str, Any], projecao: Any) -> ObservacaoRegistrada:
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

    novos: dict[str, list[tuple[int, int, Any]]] = {}
    reentradas: dict[str, list[int]] = {}
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
                item_id, presente = conhecidos[(h, ocorrencia)]
                agora.add(item_id)
                if not presente:
                    reentradas.setdefault(presenca, []).append(item_id)
            else:
                novos.setdefault(colecao, []).append((h, ocorrencia, item))
        saidas[presenca] = sorted(
            item_id for item_id, presente in conhecidos.values() if presente and item_id not in agora)

    resultado = ObservacaoRegistrada(
        registro_id=registro_id, observacao_id=None, identidade=identidade,
        primeira=primeira, capa_nova=capa_nova,
        movimentos_entraram=len(novos.get("movimentos", [])) + len(reentradas.get("presencas_movimento", [])),
        movimentos_sairam=len(saidas.get("presencas_movimento", [])),
        assuntos_entraram=len(novos.get("assuntos", [])) + len(reentradas.get("presencas_assunto", [])),
        assuntos_sairam=len(saidas.get("presencas_assunto", [])),
    )
    if not (primeira or capa_nova or resultado.movimentos_entraram or resultado.movimentos_sairam
            or resultado.assuntos_entraram or resultado.assuntos_sairam):
        _inserir(con, LinhaVista(registro_id=registro_id, consulta_id=consulta_id), ignorar=True)
        return resultado

    fonte_bruta = hit_bruto.get("_source") or {}
    volateis = {k: v for k, v in hit_bruto.items() if k not in ("_index", "_id", "_source")}
    volateis.update({k: fonte_bruta[k] for k in VOLATEIS if k in fonte_bruta})
    observacao_id = _inserir(con, LinhaObservacao(
        consulta_id=consulta_id, registro_id=registro_id, observado_em=observado_em,
        capa_id=capa_id, volateis_json=_json(volateis),
    ))
    for colecao, itens in novos.items():
        for h, ocorrencia, item in itens:
            _novo_item(con, cache, colecao, registro_id, observacao_id, h, ocorrencia, item)
    for presenca, coluna, modelo in (
        ("presencas_movimento", "movimento_id", LinhaPresencaMovimento),
        ("presencas_assunto", "assunto_id", LinhaPresencaAssunto),
    ):
        for evento, ids in (("entrou", reentradas.get(presenca, [])),
                            ("saiu", saidas.get(presenca, []))):
            for item_id in ids:
                _inserir(con, modelo(**{coluna: item_id}, observacao_id=observacao_id, evento=evento))
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
    """Acrescenta a consulta e, por hit, uma observacao (se mudou) ou uma vista.

    `requisicao` e `resposta` sao validados por `RequisicaoBusca` e
    `RespostaBusca`. Nao faz UPDATE nem DELETE.
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
        prazo = relogio.monotonic() + ESPERA_TROCA
        while True:
            try:
                return _gravar(banco, tribunal, requisicao, resposta, hits, projecao, observado_em,
                               resultado, erro)
            except _ArquivoTrocado:
                # A conexao abriu o arquivo antigo pouco antes da troca: reabre o novo.
                if relogio.monotonic() >= prazo:
                    raise RuntimeError("o acervo continua em conversao") from None
                relogio.sleep(0.2)


def _gravar(banco: Path | None, tribunal: str, requisicao: dict[str, Any], resposta: dict[str, Any],
            hits: list[dict[str, Any]], projecao: Any, observado_em: str,
            resultado: str, erro: str | None) -> RespostaRegistrada:
    con = _conexao(banco)
    try:
        with _transacao(con):
            _conferir_versao(con)
            consulta_id = _inserir(con, LinhaConsulta(
                observado_em=observado_em, tribunal=tribunal,
                requisicao_zlib=zlib.compress(_json(requisicao).encode("utf-8"), 9),
                projecao_json=None if projecao is None else _json(projecao),
                resultado=resultado, resposta_meta_json=_json(_envelope(resposta)), erro=erro,
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
# Leitura
# ----------------------------------------------------------------------------
@contextmanager
def _leitura(banco: Path | None) -> Iterator[sqlite3.Connection]:
    with _LOCK:
        con = _conexao(banco)
        try:
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


def _inicio(desde: str | date | datetime) -> str:
    """Instante ISO em UTC; data sem hora vale desde o inicio do dia (UTC)."""
    if isinstance(desde, str):
        desde = date.fromisoformat(desde) if len(desde) == 10 else datetime.fromisoformat(desde)
    if not isinstance(desde, datetime):
        desde = datetime.combine(desde, time.min, tzinfo=timezone.utc)
    if desde.tzinfo is None:
        desde = desde.replace(tzinfo=timezone.utc)
    return desde.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _digitos(numero: str) -> str:
    return "".join(c for c in numero if c.isdigit())


def _avistamentos(con: sqlite3.Connection, registro_id: int, limite: str) -> list[tuple[str, Any]]:
    """(instante, projecao) de cada vez que o registro foi visto ate `limite`, com ou sem mudanca."""
    linhas = con.execute(
        """
        SELECT o.observado_em, c.projecao_json FROM observacoes AS o
        JOIN consultas AS c ON c.id = o.consulta_id
        WHERE o.registro_id = ? AND o.observado_em <= ?
        UNION ALL
        SELECT c.observado_em, c.projecao_json FROM vistas AS v
        JOIN consultas AS c ON c.id = v.consulta_id
        WHERE v.registro_id = ? AND c.observado_em <= ?
        """,
        (registro_id, limite, registro_id, limite),
    ).fetchall()
    return [(quando, None if p is None else json.loads(p)) for quando, p in linhas]


_ITENS_DA_OBSERVACAO = {
    "movimento": """
        SELECT 'entrou', t.codigo, t.nome, m.instante, m.data_hora_texto, m.id FROM movimentos AS m
        JOIN tipos_movimento AS t ON t.id = m.tipo_id
        WHERE m.registro_id = :registro AND m.observacao_id = :obs
        UNION ALL
        SELECT p.evento, t.codigo, t.nome, m.instante, m.data_hora_texto, m.id
        FROM presencas_movimento AS p
        JOIN movimentos AS m ON m.id = p.movimento_id
        JOIN tipos_movimento AS t ON t.id = m.tipo_id
        WHERE p.observacao_id = :obs
        ORDER BY 4, 6""",
    "assunto": """
        SELECT 'entrou', a.codigo, a.nome, NULL, NULL, a.id FROM assuntos AS a
        WHERE a.registro_id = :registro AND a.observacao_id = :obs
        UNION ALL
        SELECT p.evento, a.codigo, a.nome, NULL, NULL, a.id FROM presencas_assunto AS p
        JOIN assuntos AS a ON a.id = p.assunto_id
        WHERE p.observacao_id = :obs
        ORDER BY 6""",
}


def _itens(con: sqlite3.Connection, tipo: str, registro_id: int, observacao_id: int) -> list[tuple]:
    """(evento, codigo, nome, data_hora) dos itens que entraram ou sairam naquela observacao."""
    return [
        (evento, codigo, nome, _data_hora(instante, texto))
        for evento, codigo, nome, instante, texto, _ in con.execute(
            _ITENS_DA_OBSERVACAO[tipo], {"registro": registro_id, "obs": observacao_id})
    ]


def _capa_anterior(con: sqlite3.Connection, registro_id: int, observacao_id: int) -> int | None:
    linha = con.execute(
        "SELECT capa_id FROM observacoes WHERE registro_id = ? AND id < ? "
        "AND capa_id IS NOT NULL ORDER BY id DESC LIMIT 1", (registro_id, observacao_id),
    ).fetchone()
    return linha[0] if linha else None


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
    """vezes que o registro foi visto, com ou sem mudanca."""
    primeira_vista: str
    ultima_vista: str
    mudancas: list[MudancaObservada]
    """as mais recentes primeiro, ate `limite`."""


class HistoricoProcesso(BaseModel):
    """Saida de `historico`."""

    numero: str
    registros: list[HistoricoRegistro] = Field(default_factory=list)


def historico(numero: str, *, limite: int = 100, detalhar: bool = False,
              banco: Path | None = None) -> HistoricoProcesso:
    """As mudancas de cada registro do processo, sem consultar a API."""
    digitos = _digitos(numero)
    limite = max(1, min(limite, 10000))
    saida = HistoricoProcesso(numero=digitos)
    with _leitura(banco) as con:
        for registro in _ler(con, LinhaRegistro, "numero_processo = ?", (digitos,),
                             sufixo="ORDER BY id"):
            vezes = sorted(quando for quando, _ in _avistamentos(con, registro.id, "9999"))
            if not vezes:
                continue
            primeira_id = con.execute(
                "SELECT MIN(id) FROM observacoes WHERE registro_id = ?", (registro.id,)).fetchone()[0]
            mudancas = []
            for obs in _ler(con, LinhaObservacao, "registro_id = ?", (registro.id,),
                            sufixo=f"ORDER BY id DESC LIMIT {limite}"):
                itens = [
                    ItemMudanca(tipo=tipo, evento=evento, codigo=codigo, nome=nome, data_hora=data_hora)
                    for tipo in ("movimento", "assunto")
                    for evento, codigo, nome, data_hora in _itens(con, tipo, registro.id, obs.id)
                ]
                anterior = _capa_anterior(con, registro.id, obs.id)
                eh_primeira = obs.id == primeira_id
                mudancas.append(MudancaObservada(
                    observacao_id=obs.id, consulta_id=obs.consulta_id,
                    observado_em=obs.observado_em, primeira=eh_primeira,
                    capa_nova=(not eh_primeira and obs.capa_id is not None
                               and anterior != obs.capa_id),
                    entraram=sum(i.evento == "entrou" for i in itens),
                    sairam=sum(i.evento == "saiu" for i in itens),
                    itens=itens if detalhar else [],
                ))
            saida.registros.append(HistoricoRegistro(
                registro=registro, observacoes=len(vezes), primeira_vista=vezes[0],
                ultima_vista=vezes[-1], mudancas=mudancas,
            ))
    return saida


class MovimentoNovo(BaseModel):
    evento: Literal["entrou", "saiu"]
    """"saiu" e retificacao ou remocao na fonte."""
    data_hora: str | None = None
    """quando o tribunal registrou o movimento."""
    codigo: int | None = None
    nome: str | None = None
    observado_em: str
    """quando a skill viu a mudanca."""
    marco: bool
    """o codigo nao esta no `ruido` passado a `novidades`."""


class RegistroNovidade(BaseModel):
    registro: LinhaRegistro
    registro_novo: bool
    """visto pela primeira vez no periodo: o processo apareceu noutro tribunal ou grau."""
    capa_nova: bool
    movimentos_iniciais: int = 0
    """movimentos que o registro novo ja trazia: contagem, e nao novidade."""
    movimentos: list[MovimentoNovo] = Field(default_factory=list)


class ProcessoNovidade(BaseModel):
    numero: str
    processo_novo: bool
    """nenhum registro do numero tinha sido observado antes do periodo (linha de base)."""
    registros: list[RegistroNovidade]


class Novidades(BaseModel):
    """Saida de `novidades`: o que mudou nos processos observados desde um instante."""

    desde: str
    ate: str
    processos: list[ProcessoNovidade] = Field(default_factory=list)


def novidades(desde: str | date | datetime, *, numeros: list[str] | None = None,
              ruido: set[int] | frozenset[int] = frozenset(),
              banco: Path | None = None) -> Novidades:
    """Movimentos que entraram ou sairam, capas novas e registros novos desde `desde`.

    Feita para a rotina que reconsulta um acervo inteiro todo dia: o que ela
    precisa saber e o que a passada trouxe de diferente, e nao o estado. A
    primeira observacao de um registro e linha de base, e nao novidade: os
    movimentos que ele ja trazia viram contagem (`movimentos_iniciais`), senao
    a primeira passada sobre 3.448 processos listaria 406 mil "novidades".
    """
    inicio = _inicio(desde)
    filtro = {_digitos(n) for n in numeros} if numeros is not None else None
    with _leitura(banco) as con:
        ate = con.execute("SELECT MAX(observado_em) FROM consultas").fetchone()[0] or inicio
        saida = Novidades(desde=inicio, ate=ate)
        por_registro: dict[int, list[LinhaObservacao]] = {}
        for obs in _ler(con, LinhaObservacao, "observado_em >= ?", (inicio,),
                        sufixo="ORDER BY registro_id, id"):
            por_registro.setdefault(obs.registro_id, []).append(obs)
        registros = _por_id(con, LinhaRegistro, set(por_registro))
        por_numero: dict[str, list[RegistroNovidade]] = {}
        for registro_id, lista in por_registro.items():
            registro = registros[registro_id]
            if filtro is not None and registro.numero_processo not in filtro:
                continue
            primeira_id = con.execute(
                "SELECT MIN(id) FROM observacoes WHERE registro_id = ?", (registro_id,)
            ).fetchone()[0]
            novo = lista[0].id == primeira_id
            capa_nova, iniciais = False, 0
            movimentos: list[MovimentoNovo] = []
            for obs in lista:
                if obs.id == primeira_id:
                    iniciais = len(_itens(con, "movimento", registro_id, obs.id))
                    continue
                anterior = _capa_anterior(con, registro_id, obs.id)
                if obs.capa_id is not None and anterior != obs.capa_id:
                    capa_nova = True
                for evento, codigo, nome, data_hora in _itens(con, "movimento", registro_id, obs.id):
                    movimentos.append(MovimentoNovo(
                        evento=evento, data_hora=data_hora, codigo=codigo, nome=nome,
                        observado_em=obs.observado_em, marco=codigo not in ruido,
                    ))
            if not (novo or capa_nova or movimentos):
                continue  # so assuntos mudaram
            movimentos.sort(key=lambda m: (m.data_hora or "", m.evento))
            por_numero.setdefault(registro.numero_processo, []).append(RegistroNovidade(
                registro=registro, registro_novo=novo, capa_nova=capa_nova,
                movimentos_iniciais=iniciais, movimentos=movimentos,
            ))
        for numero in sorted(por_numero):
            visto_antes = con.execute(
                "SELECT 1 FROM observacoes AS o JOIN registros AS r ON r.id = o.registro_id "
                "WHERE r.numero_processo = ? AND o.observado_em < ? LIMIT 1", (numero, inicio),
            ).fetchone()
            saida.processos.append(ProcessoNovidade(
                numero=numero, processo_novo=visto_antes is None, registros=por_numero[numero],
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
    """ultima vez que o registro foi visto ate a data pedida, com ou sem mudanca."""
    capa: CapaVigente | None
    capa_observada_em: str | None
    assuntos: list[LinhaAssunto] | None
    """nulo: nenhuma consulta ate a data trouxe os assuntos (recorte `_source`)."""
    assuntos_observados_em: str | None
    movimentos: list[MovimentoVigente] | None
    """em ordem de `data_hora`; nulo: nenhuma consulta ate a data trouxe os movimentos."""
    movimentos_observados_em: str | None
    """ultima vez que os movimentos vieram na resposta: o estado vale ate ali."""


class EstadoProcesso(BaseModel):
    """Saida de `estado`: o processo como o acervo o conhecia numa data."""

    numero: str
    em: str | None
    registros: list[EstadoRegistro] = Field(default_factory=list)


def _vigentes(con: sqlite3.Connection, tabela: str, presenca: str, coluna: str,
              registro_id: int, limite: str) -> dict[int, str]:
    """id -> data da entrada, dos itens que entraram ate `limite` e nao sairam."""
    linhas = con.execute(
        f"""
        SELECT i.id, o.observado_em,
               (SELECT p.evento || '|' || q.observado_em FROM {presenca} AS p
                JOIN observacoes AS q ON q.id = p.observacao_id
                WHERE p.{coluna} = i.id AND q.observado_em <= :limite
                ORDER BY p.observacao_id DESC LIMIT 1)
        FROM {tabela} AS i JOIN observacoes AS o ON o.id = i.observacao_id
        WHERE i.registro_id = :registro AND o.observado_em <= :limite
        """,
        {"registro": registro_id, "limite": limite},
    ).fetchall()
    vigentes = {}
    for item_id, entrada, ultimo in linhas:
        if ultimo is None:
            vigentes[item_id] = entrada
        elif ultimo.startswith("entrou|"):
            vigentes[item_id] = ultimo.split("|", 1)[1]
    return vigentes


def estado(numero: str, *, em: str | date | datetime | None = None,
           banco: Path | None = None) -> EstadoProcesso:
    """Capa, assuntos e movimentos vigentes de cada registro, sem consultar a API."""
    digitos = _digitos(numero)
    limite = _limite_em(em)
    saida = EstadoProcesso(numero=digitos, em=None if em is None else limite)
    with _leitura(banco) as con:
        for registro in _ler(con, LinhaRegistro, "numero_processo = ?", (digitos,),
                             sufixo="ORDER BY id"):
            vezes = _avistamentos(con, registro.id, limite)
            if not vezes:
                continue

            def ultima_com(campos: tuple[str, ...]) -> str | None:
                return max((q for q, p in vezes if all(_observado(c, p) for c in campos)), default=None)

            capa_linha = con.execute(
                "SELECT capa_id FROM observacoes WHERE registro_id = ? AND observado_em <= ? "
                "AND capa_id IS NOT NULL ORDER BY observado_em DESC, id DESC LIMIT 1",
                (registro.id, limite),
            ).fetchone()
            capa = _ler(con, LinhaCapa, "id = ?", (capa_linha[0],))[0] if capa_linha else None
            movimentos_em = ultima_com(("movimentos",))
            assuntos_em = ultima_com(("assuntos",))

            movimentos = None
            orgaos = _por_id(con, LinhaOrgao, {capa.orgao_id} if capa and capa.orgao_id else set())
            if movimentos_em is not None:
                entradas = _vigentes(con, "movimentos", "presencas_movimento", "movimento_id",
                                     registro.id, limite)
                linhas = [m for m in _ler(con, LinhaMovimento, "registro_id = ?", (registro.id,),
                                          sufixo="ORDER BY instante, id") if m.id in entradas]
                tipos = _por_id(con, LinhaTipoMovimento, {m.tipo_id for m in linhas})
                orgaos |= _por_id(con, LinhaOrgao, {m.orgao_id for m in linhas if m.orgao_id})
                ligacoes: dict[int, list[int]] = {}
                for movimento_id, complemento_id in con.execute(
                    "SELECT mc.movimento_id, mc.complemento_id FROM movimento_complementos AS mc "
                    "JOIN movimentos AS m ON m.id = mc.movimento_id WHERE m.registro_id = ? "
                    "ORDER BY mc.movimento_id, mc.ordem", (registro.id,),
                ):
                    ligacoes.setdefault(movimento_id, []).append(complemento_id)
                complementos = _por_id(con, LinhaComplemento,
                                       {c for ids in ligacoes.values() for c in ids})
                movimentos = [
                    MovimentoVigente(
                        movimento=m, tipo=tipos[m.tipo_id], orgao=orgaos.get(m.orgao_id),
                        complementos=[complementos[c] for c in ligacoes.get(m.id, [])],
                        desde=entradas[m.id],
                    )
                    for m in linhas
                ]
            assuntos = None
            if assuntos_em is not None:
                vigentes = _vigentes(con, "assuntos", "presencas_assunto", "assunto_id",
                                     registro.id, limite)
                assuntos = [a for a in _ler(con, LinhaAssunto, "registro_id = ?", (registro.id,),
                                            sufixo="ORDER BY id") if a.id in vigentes]
            saida.registros.append(EstadoRegistro(
                registro=registro, observado_em=max(q for q, _ in vezes),
                capa=CapaVigente(capa=capa, orgao=orgaos.get(capa.orgao_id)) if capa else None,
                capa_observada_em=ultima_com(CAMPOS_CAPA) if capa else None,
                assuntos=assuntos, assuntos_observados_em=assuntos_em,
                movimentos=movimentos, movimentos_observados_em=movimentos_em,
            ))
    return saida


class Estatisticas(BaseModel):
    """Saida de `estatisticas`: linhas por tabela, sem consultar a API."""

    banco: str
    versao: int
    tabelas: dict[str, int]
    """linhas de cada tabela do acervo."""
    consultas_com_erro: int

    def __getitem__(self, tabela: str) -> int:
        return self.tabelas[tabela]


def estatisticas(*, banco: Path | None = None) -> Estatisticas:
    """Resumo para inspecao do acervo local; nao consulta o DataJud."""
    with _leitura(banco) as con:
        return Estatisticas(
            banco=str(banco or caminho_banco()),
            versao=con.execute("PRAGMA user_version").fetchone()[0],
            tabelas={
                m.TABELA: con.execute(f"SELECT COUNT(*) FROM {m.TABELA}").fetchone()[0]
                for m in TABELAS
            },
            consultas_com_erro=con.execute(
                "SELECT COUNT(*) FROM consultas WHERE resultado = 'erro'").fetchone()[0],
        )
