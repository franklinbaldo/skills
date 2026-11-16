# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Citacoes de normas e normalizacao de busca (stdlib pura).

Reconhece "LC 68/1992", "Lei 1.234", "Decreto 12345", "Lei Complementar nº 68, de 09-12-1992" e
variantes. O texto de busca e normalizado como o Leizilla normaliza a coluna `busca` do catalogo
(`leizilla.catalogo.normalizar_busca`): minusculas, sem acento, tudo que nao e a-z0-9 vira espaco.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

TIPOS = ("lei", "lc", "decreto", "decreto-lei")

ROTULO_TIPO = {
    "lei": "Lei",
    "lc": "Lei Complementar",
    "decreto": "Decreto",
    "decreto-lei": "Decreto-Lei",
}

SIGLA_TIPO = {"lei": "Lei", "lc": "LC", "decreto": "Decreto", "decreto-lei": "Decreto-Lei"}

# Apelidos aceitos (ja normalizados: minusculas, sem acento, separadores como espaco).
_APELIDOS = {
    "lei": "lei",
    "lei ordinaria": "lei",
    "lei estadual": "lei",
    "l": "lei",
    "lc": "lc",
    "l c": "lc",
    "lcp": "lc",
    "lei complementar": "lc",
    "lei complementar estadual": "lc",
    "decreto": "decreto",
    "decreto estadual": "decreto",
    "dec": "decreto",
    "decreto lei": "decreto-lei",
    "dec lei": "decreto-lei",
    "dl": "decreto-lei",
}

_NUMERO = r"(?P<numero>\d{1,3}(?:\.\d{3})+|\d+)"
_PADRAO = re.compile(
    r"^(?P<tipo>[a-z][a-z .\-]*?)\s*"  # tipo (ja sem acento)
    r"(?:n\s*[o.]*\s*|numero\s+)?"  # "n", "no", "n.", "numero" (apos remover º e °)
    + _NUMERO
    + r"(?:\s*-?\s*(?P<sufixo>[a-z])(?![a-z]))?"  # 9A, 9-A
    r"(?P<resto>.*)$"
)


def sem_acento(texto: str) -> str:
    """Remove marcas diacriticas (NFD)."""
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if not unicodedata.category(c).startswith("M"))


def normalizar_busca(texto: str) -> str:
    """Mesmo algoritmo da coluna `busca` do catalogo."""
    return re.sub(r"[^a-z0-9]+", " ", sem_acento(texto.lower())).strip()


def termos_busca(consulta: str) -> list[str]:
    """Termos normalizados de uma consulta; "1.234" vira o termo unico "1234"."""
    junto = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", consulta)
    return normalizar_busca(junto).split()


def normalizar_tipo(valor: str) -> str | None:
    """`lc`, `Lei Complementar`, `decreto_lei`... -> tipo canonico, ou None."""
    chave = normalizar_busca(valor.replace("_", " "))
    return _APELIDOS.get(chave)


def expandir_ano(texto: str) -> int | None:
    """Ano de 4 digitos, ou de 2 digitos (81-99 -> 19xx; 00-80 -> 20xx; o catalogo comeca em 1981)."""
    if not texto.isdigit():
        return None
    if len(texto) == 4:
        return int(texto)
    if len(texto) == 2:
        valor = int(texto)
        return 1900 + valor if valor >= 81 else 2000 + valor
    return None


@dataclass(frozen=True)
class Citacao:
    tipo: str
    numero: int
    sufixo: str = ""
    ano: int | None = None

    def curta(self) -> str:
        base = f"{SIGLA_TIPO[self.tipo]} {self.numero}{self.sufixo.upper()}"
        return f"{base}/{self.ano}" if self.ano else base


def _ano_do_resto(resto: str) -> tuple[bool, int | None]:
    """Le o complemento depois do numero. Devolve (valido, ano)."""
    resto = resto.strip(" ,;.")
    if not resto:
        return True, None
    if resto.startswith("/"):
        ano = expandir_ano(resto[1:].strip())
        return ano is not None, ano
    if resto.startswith("de ") or resto.startswith("de-"):
        numeros = re.findall(r"\d+", resto)
        if not numeros:
            return False, None
        ano = expandir_ano(numeros[-1])
        return ano is not None, ano
    return False, None


def parse_citacao(texto: str) -> Citacao | None:
    """Interpreta o texto INTEIRO como citacao; None se nao for uma (ex.: busca por assunto)."""
    limpo = sem_acento(texto.lower()).replace("º", "").replace("°", "").replace("ª", "")
    limpo = re.sub(r"\s+", " ", limpo).strip()
    achado = _PADRAO.match(limpo)
    if not achado:
        return None
    tipo_txt = re.sub(r"[^a-z]+", " ", achado.group("tipo")).strip()
    tipo = _APELIDOS.get(tipo_txt)
    if tipo is None:
        return None
    valido, ano = _ano_do_resto(achado.group("resto"))
    if not valido:
        return None
    numero = int(achado.group("numero").replace(".", ""))
    return Citacao(tipo, numero, (achado.group("sufixo") or "").lower(), ano)


def parse_artigo(texto: str) -> tuple[int, str] | None:
    """ "5", "5º", "art. 5", "5-A", "5A" -> (5, "a"); None se nao for numero de artigo."""
    limpo = sem_acento(texto.lower()).replace("º", "").replace("°", "")
    achado = re.fullmatch(r"\s*(?:art\w*\.?\s*)?(\d+)\s*-?\s*([a-z])?\s*", limpo)
    if not achado:
        return None
    return int(achado.group(1)), achado.group(2) or ""
