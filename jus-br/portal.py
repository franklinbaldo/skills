# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Cliente da API do Portal de Serviços da PDPJ (portaldeservicos.pdpj.jus.br/api).

Contrato: Swagger de homologação (`/v2/api-docs?group=Interno`), conferido contra
a produção em 26/10/2026 com sessão real. A produção devolve 403 do servidor web a
quem não se apresenta como o navegador do próprio Portal, por isso as chamadas levam
os cabeçalhos dele (`CABECALHOS_NAVEGADOR`). É uma escolha consciente e frágil: o
caminho limpo é um cliente integrador cadastrado no CNJ.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
from auth import AuthService
from errors import JusBrApiError, JusBrUnauthorizedError

PORTAL_API = "https://portaldeservicos.pdpj.jus.br/api"
CABECALHOS_NAVEGADOR = {
    "accept": "application/json, text/plain, */*",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
    "referer": "https://portaldeservicos.pdpj.jus.br/consulta",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
}
PETICAO_INTERCORRENTE = "PETICAO_INTERCORRENTE"


def sha1_hex(conteudo: bytes) -> str:
    """O Portal identifica cada arquivo pelo SHA-1 (o `hash` dos documentos das petições)."""
    return hashlib.sha1(conteudo).hexdigest()


def desembrulhar(corpo: Any) -> Any:
    """Parte das rotas embrulha a resposta em `dadosResposta`; as paginadas, em `content`."""
    if isinstance(corpo, dict) and "dadosResposta" in corpo:
        corpo = corpo["dadosResposta"]
    if isinstance(corpo, dict) and "content" in corpo and "pageable" in corpo:
        corpo = corpo["content"]
    return corpo


class PortalClient:
    """Leitura de autos e peticionamento intercorrente pelo Portal de Serviços."""

    def __init__(self, auth_service: AuthService | None = None, http_client: httpx.Client | None = None) -> None:
        self.auth = auth_service or AuthService()
        self.http = http_client or httpx.Client(timeout=60.0)

    def _requisitar(self, metodo: str, caminho: str, **kwargs: Any) -> httpx.Response:
        url = f"{PORTAL_API}/{caminho.lstrip('/')}"
        cabecalhos = {**CABECALHOS_NAVEGADOR, **kwargs.pop("headers", {})}
        cabecalhos["authorization"] = f"Bearer {self.auth.ensure_valid_tokens().access_token}"
        resp = self.http.request(metodo, url, headers=cabecalhos, **kwargs)
        if resp.status_code == 401:
            cabecalhos["authorization"] = f"Bearer {self.auth.refresh().access_token}"
            resp = self.http.request(metodo, url, headers=cabecalhos, **kwargs)
            if resp.status_code == 401:
                raise JusBrUnauthorizedError("Sessão recusada pelo Portal (401). Rode `jusbr auth bookmarklet`.")
        if resp.status_code >= 400:
            raise JusBrApiError(
                f"Portal respondeu {resp.status_code} em {metodo} /{caminho.lstrip('/')}: {_motivo(resp)}"
            )
        return resp

    def _json(self, metodo: str, caminho: str, **kwargs: Any) -> Any:
        resp = self._requisitar(metodo, caminho, **kwargs)
        if not resp.content:
            return None
        return desembrulhar(resp.json())

    def get(self, caminho: str, **params: Any) -> Any:
        """GET livre, para explorar rotas do Swagger ainda sem comando próprio."""
        resp = self._requisitar("GET", caminho, params=params or None)
        return desembrulhar(resp.json()) if "json" in resp.headers.get("content-type", "") else resp.text

    # Leitura de autos e comunicações

    def processo(self, cnj: str) -> dict[str, Any]:
        """Capa, partes, movimentos e documentos pela base nacional (Codex), de qualquer tribunal."""
        itens = self._json("GET", f"v2/processos/{cnj}")
        if not itens:
            raise JusBrApiError(f"Processo {cnj} não encontrado na base nacional da PDPJ.")
        return itens[0] if isinstance(itens, list) else itens

    def documento(self, cnj: str, id_documento: str) -> tuple[bytes, str]:
        resp = self._requisitar("GET", f"v2/processos/{cnj}/documentos/{id_documento}/binario")
        return resp.content, resp.headers.get("content-type", "")

    def comunicacoes(self, numero_processo: str = "", inicio: str = "", fim: str = "", **filtros: str) -> dict:
        """Publicações no DJEN; datas em AAAA-MM-DD; o número vai só com dígitos."""
        params = {
            "numeroProcesso": "".join(c for c in numero_processo if c.isdigit()),
            "dataDisponibilizacaoInicio": inicio,
            "dataDisponibilizacaoFim": fim,
            **filtros,
        }
        return self._json("GET", "v1/comunicacao", params={k: v for k, v in params.items() if v})

    def domicilio(self, inicio: str, fim: str, pagina: int = 0, tamanho: int = 50) -> list[dict]:
        """Domicílio Judicial Eletrônico do usuário; janela de no máximo 7 dias (ISO 8601 com Z)."""
        params = {"dataInicio": inicio, "dataFim": fim, "page": pagina, "size": tamanho}
        return self._json("GET", "v1/domicilio-eletronico/comunicacao", params=params) or []

    # Cadastro dos tribunais

    def tribunais(self) -> list[dict]:
        return self._json("GET", "v1/tribunal/listar") or []

    def tribunal(self, jtr: str) -> dict | None:
        """Cadastro de peticionamento; None quando o tribunal não recebe petição pelo Portal."""
        try:
            return self._json("GET", f"v1/tribunais/{jtr}")
        except JusBrApiError as exc:
            if " 404 " in str(exc):
                return None
            raise

    def tipos_documento(self, sigla_tribunal: str) -> list[dict]:
        return self._json("GET", "v1/tipo/documento/tribunal", params={"tribunal": sigla_tribunal}) or []

    # Petições

    def peticoes(self) -> list[dict]:
        return self._json("GET", "v1/peticoes/minhas-peticoes") or []

    def peticao(self, id_peticao: int) -> dict:
        return self._json("GET", f"v1/peticoes/{id_peticao}")

    def recibo(self, id_peticao: int) -> dict:
        return self._json("GET", f"v1/peticoes/{id_peticao}/recibo")

    def consultar_protocolo(self, protocolo: str) -> dict:
        return self._json("GET", f"v1/consulta-protocolo/{protocolo}")

    def criar_rascunho(self, peticao: dict) -> dict:
        return self._json("POST", "v1/peticoes", json=peticao)

    def anexar(self, documento: dict, conteudo: bytes) -> dict:
        """Registra o documento na petição e envia o arquivo à URL pré-assinada que o Portal devolve."""
        resposta = self._json("POST", "v1/peticoes/documentos", json=documento)
        url = (resposta or {}).get("url")
        if not url:
            raise JusBrApiError("O Portal registrou o documento mas não devolveu a URL de envio.")
        envio = self.http.put(url, content=conteudo)  # S3: sem o Bearer da PDPJ
        if envio.status_code >= 400:
            raise JusBrApiError(f"Envio do arquivo recusado pelo repositório ({envio.status_code}).")
        return resposta.get("documentoSalvo") or resposta

    def protocolar(self, id_peticao: int) -> dict:
        return self._json("POST", f"v1/peticoes/{id_peticao}/protocolo")

    def excluir(self, id_peticao: int) -> None:
        self._requisitar("DELETE", f"v1/peticoes/{id_peticao}")

    def close(self) -> None:
        self.http.close()


def _motivo(resp: httpx.Response) -> str:
    try:
        corpo = resp.json()
    except ValueError:
        return "resposta não JSON (bloqueio do servidor web?)" if resp.status_code == 403 else resp.text[:200]
    if isinstance(corpo, dict):
        return str(corpo.get("message") or corpo.get("mensagem") or corpo)[:300]
    return str(corpo)[:300]
