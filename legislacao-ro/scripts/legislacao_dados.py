# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Acesso aos datasets publicados pelo Leizilla: resolucao de fonte, cache local com checagem de frescor e DuckDB.

Cada dataset e pequeno (0,4 a 3,2 MB em 2026-11-16), entao o caminho padrao e baixar o Parquet para um cache
local e consulta-lo com DuckDB, sem httpfs. O espelho do portal e tentado primeiro; o Internet Archive e o reserva.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PORTAL = "https://franklinbaldo.github.io/leizilla/data/ro"
IA_DATASET = "https://archive.org/download/leizilla-dataset-ro-v0-latest"
IA_TEXTOS = "https://archive.org/download/leizilla-textos-ro-v0-latest"
UA = "legislacao-ro skill (leitura publica)"

NOMES = ("catalogo", "relacoes", "textos", "versoes")

PADROES: dict[str, list[str]] = {
    "catalogo": [f"{PORTAL}/catalogo.parquet", f"{IA_DATASET}/completeness.parquet"],
    "relacoes": [f"{PORTAL}/relacoes.parquet", f"{IA_DATASET}/relacoes.parquet"],
    "textos": [f"{PORTAL}/textos.parquet", f"{IA_TEXTOS}/textos.parquet"],
    "versoes": [f"{PORTAL}/versoes.parquet", f"{IA_DATASET}/versoes.parquet"],
}

TTL_PADRAO_HORAS = 24.0


class DatasetIndisponivel(Exception):
    """Dataset exigido que não pode ser lido; a mensagem nomeia o dataset e o que foi tentado."""

    def __init__(self, nome: str, tentativas: list[str]) -> None:
        self.nome = nome
        self.tentativas = tentativas
        detalhe = "; ".join(tentativas) if tentativas else "nenhuma fonte configurada"
        super().__init__(f"dataset '{nome}' indisponível ({detalhe})")


@dataclass
class Origens:
    """De onde ler cada dataset. Valores de dataset: caminho local ou URL; `base_url`: URL ou diretorio."""

    base_url: str | None = None
    catalogo: str | None = None
    relacoes: str | None = None
    textos: str | None = None
    versoes: str | None = None
    atualizar: bool = False
    offline: bool = False
    cache_dir: str | None = None
    ttl_horas: float = TTL_PADRAO_HORAS

    def explicito(self, nome: str) -> str | None:
        return getattr(self, nome)


@dataclass
class Fonte:
    nome: str
    caminho: Path
    origem: str
    avisos: list[str] = field(default_factory=list)


def _e_url(valor: str) -> bool:
    return valor.startswith(("http://", "https://"))


def diretorio_cache(origens: Origens) -> Path:
    bruto = origens.cache_dir or os.environ.get("LEGISLACAO_RO_CACHE")
    if bruto:
        return Path(bruto).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "legislacao-ro"


def _abrir(pedido: urllib.request.Request, timeout: float) -> Any:
    """Unico ponto de rede (os testes o substituem)."""
    return urllib.request.urlopen(pedido, timeout=timeout)  # noqa: S310


def _ler_meta(meta: Path) -> dict[str, Any]:
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _baixar(url: str, destino: Path, meta: Path) -> None:
    """Baixa `url` para `destino` com GET condicional (304 mantem o arquivo). Levanta OSError/URLError."""
    anterior = _ler_meta(meta) if destino.exists() else {}
    cabecalhos = {"User-Agent": UA}
    if anterior.get("url") == url:
        if anterior.get("etag"):
            cabecalhos["If-None-Match"] = anterior["etag"]
        if anterior.get("last_modified"):
            cabecalhos["If-Modified-Since"] = anterior["last_modified"]
    agora = time.time()
    try:
        with _abrir(urllib.request.Request(url, headers=cabecalhos), 60) as resposta:
            corpo = resposta.read()
            etag = resposta.headers.get("ETag")
            modificado = resposta.headers.get("Last-Modified")
    except urllib.error.HTTPError as erro:
        if erro.code != 304:
            raise
        meta.write_text(json.dumps({**anterior, "verificado_em": agora}), encoding="utf-8")
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(corpo)
    temporario.replace(destino)
    meta.write_text(
        json.dumps(
            {"url": url, "etag": etag, "last_modified": modificado, "verificado_em": agora, "bytes": len(corpo)}
        ),
        encoding="utf-8",
    )


def _de_cache_ou_rede(nome: str, urls: list[str], origens: Origens) -> Fonte:
    pasta = diretorio_cache(origens)
    destino = pasta / f"{nome}.parquet"
    meta = pasta / f"{nome}.json"
    existe = destino.exists()
    info = _ler_meta(meta) if existe else {}
    idade_h = (time.time() - float(info.get("verificado_em", 0))) / 3600 if existe else None
    fresco = existe and idade_h is not None and idade_h < origens.ttl_horas and info.get("url") in urls
    if existe and (origens.offline or (fresco and not origens.atualizar)):
        return Fonte(nome, destino, info.get("url", "cache"))
    if origens.offline:
        raise DatasetIndisponivel(nome, ["modo --offline e não há cópia no cache"])
    tentativas: list[str] = []
    pasta.mkdir(parents=True, exist_ok=True)
    for url in urls:
        try:
            _baixar(url, destino, meta)
        except urllib.error.HTTPError as erro:
            tentativas.append(f"{url}: HTTP {erro.code}")
        except (urllib.error.URLError, OSError, TimeoutError) as erro:
            tentativas.append(f"{url}: {getattr(erro, 'reason', erro)}")
        else:
            return Fonte(nome, destino, url)
    if existe:
        aviso = (
            f"cópia local de '{nome}' pode estar desatualizada: não foi possível revalidar ({'; '.join(tentativas)})"
        )
        return Fonte(nome, destino, info.get("url", "cache"), [aviso])
    raise DatasetIndisponivel(nome, tentativas)


def resolver_fonte(nome: str, origens: Origens) -> Fonte:
    """Escolhe e materializa o Parquet de `nome`, ou levanta DatasetIndisponivel."""
    explicito = origens.explicito(nome) or os.environ.get(f"LEGISLACAO_RO_{nome.upper()}")
    base = origens.base_url or os.environ.get("LEGISLACAO_RO_BASE_URL")
    if explicito:
        if _e_url(explicito):
            return _de_cache_ou_rede(nome, [explicito], origens)
        caminho = Path(explicito).expanduser()
        if not caminho.is_file():
            raise DatasetIndisponivel(nome, [f"arquivo local não encontrado: {caminho}"])
        return Fonte(nome, caminho, str(caminho))
    if base:
        if _e_url(base):
            return _de_cache_ou_rede(nome, [f"{base.rstrip('/')}/{nome}.parquet"], origens)
        caminho = Path(base).expanduser() / f"{nome}.parquet"
        if not caminho.is_file():
            raise DatasetIndisponivel(nome, [f"arquivo não encontrado em {base}: {caminho.name}"])
        return Fonte(nome, caminho, str(caminho))
    return _de_cache_ou_rede(nome, PADROES[nome], origens)


def _literal(caminho: Path) -> str:
    return "'" + str(caminho).replace("'", "''") + "'"


# Colunas do catalogo v0.2 (ADR-0017) que o catalogo publicado antes de 2026-11-16 ainda nao tem.
_VAZIO = "NULL::VARCHAR"
_BUSCA_RESERVA = (
    "trim(regexp_replace(strip_accents(lower(coalesce(titulo, '') || ' ' || coalesce(ementa, ''))), "
    "'[^a-z0-9]+', ' ', 'g'))"
)
_URL_OFICIAL_RESERVA = 'nullif(regexp_extract(arquivos, \'"url": ?"([^"]+)"\', 1), \'\')'
_RENDICOES_RESERVA = (
    'array_to_string(list_sort(list_distinct(regexp_extract_all(arquivos, \'"rendicao": ?"([^"]+)"\', 1))), \',\')'
)
_CATALOGO_OPCIONAIS = {
    "situacao_norma": _VAZIO,
    "situacao_evidencias": _VAZIO,
    "busca": _BUSCA_RESERVA,
    "url_oficial": _URL_OFICIAL_RESERVA,
    "url_ia": _VAZIO,
    "link_publico": _VAZIO,
    "rendicoes": _RENDICOES_RESERVA,
    "coddoc": "NULL::INTEGER",
    "identidade_incerta": "NULL::BOOLEAN",
}
CATALOGO_OBRIGATORIAS = (
    "norma_id", "tipo", "numero", "sufixo", "situacao", "titulo", "data", "ano", "ementa", "arquivos",
    "preservada", "com_texto", "legivel", "estruturada", "texto_id", "ia_item",
)  # fmt: skip


class Acervo:
    """Conexao DuckDB com views sob demanda para cada dataset; guarda avisos para a saida."""

    def __init__(self, origens: Origens) -> None:
        import duckdb

        self.origens = origens
        self.con = duckdb.connect()
        self.avisos: list[str] = []
        self.fontes: dict[str, Fonte] = {}
        self.ausentes: dict[str, str] = {}
        self.catalogo_antigo = False

    def exige(self, nome: str) -> Fonte:
        if nome in self.fontes:
            return self.fontes[nome]
        fonte = resolver_fonte(nome, self.origens)
        self.avisos.extend(fonte.avisos)
        self._registrar(nome, fonte)
        self.fontes[nome] = fonte
        return fonte

    def opcional(self, nome: str) -> Fonte | None:
        """Como `exige`, mas dataset ausente vira aviso (e `ausentes[nome]`), nao erro."""
        if nome in self.ausentes:
            return None
        try:
            return self.exige(nome)
        except DatasetIndisponivel as erro:
            self.ausentes[nome] = str(erro)
            self.avisos.append(f"{erro}; o que depende dele não foi consultado")
            return None

    def _registrar(self, nome: str, fonte: Fonte) -> None:
        origem = f"read_parquet({_literal(fonte.caminho)})"
        if nome != "catalogo":
            self.con.execute(f"CREATE OR REPLACE VIEW {nome} AS SELECT * FROM {origem}")
            return
        colunas = {linha[0] for linha in self.con.execute(f"DESCRIBE SELECT * FROM {origem}").fetchall()}
        faltam = [c for c in CATALOGO_OBRIGATORIAS if c not in colunas]
        if faltam:
            raise DatasetIndisponivel(nome, [f"{fonte.origem}: faltam colunas {', '.join(faltam)}"])
        extras = [f"{c if c in colunas else expr} AS {c}" for c, expr in _CATALOGO_OPCIONAIS.items()]
        self.catalogo_antigo = "situacao_norma" not in colunas
        basicas = ", ".join(c for c in CATALOGO_OBRIGATORIAS if c != "situacao")
        self.con.execute(
            f"CREATE OR REPLACE VIEW catalogo AS SELECT {basicas}, {', '.join(extras)}, "
            f"coalesce(ano, try_cast(left(data, 4) AS INTEGER)) AS ano_ref FROM {origem} WHERE situacao = 'listada'"
        )
        if self.catalogo_antigo:
            primeiro, ultimo = self.con.execute("SELECT min(ano_ref), max(ano_ref) FROM catalogo").fetchone()
            self.avisos.append(
                "catálogo no formato 0.1 (sem situacao_norma, busca e links): a situação no índice não está "
                f"disponível e a busca usa título+ementa calculados localmente; cobre só os anos {primeiro} a "
                f"{ultimo}, então ausência aqui NÃO prova que a norma não exista"
            )

    def consulta(self, sql: str, parametros: list[Any] | None = None) -> list[dict[str, Any]]:
        cursor = self.con.execute(sql, parametros or [])
        nomes = [d[0] for d in cursor.description]
        return [dict(zip(nomes, linha, strict=True)) for linha in cursor.fetchall()]
