# /// script
# requires-python = ">=3.11"
# ///
"""Monta a petição intercorrente a partir dos autos da PDPJ, sem rede.

Os nomes dos campos vêm do `PeticaoDTO` do Swagger; os valores de cada um foram
conferidos contra petições reais do usuário (`GET /v1/peticoes/{id}`). Tudo o que
o Portal precisa sai de `GET /v2/processos/{cnj}`: nada aqui é digitado à mão.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from portal import PETICAO_INTERCORRENTE, sha1_hex

SEGMENTOS = {
    "JUSTICA_FEDERAL": "JCF",
    "JUSTICA_ESTADUAL": "JCE",
    "JUSTICA_DO_TRABALHO": "JTU",
    "JUSTICA_ELEITORAL": "JEU",
    "JUSTICA_MILITAR_UNIAO": "JMU",
    "JUSTICA_MILITAR_ESTADUAL": "JME",
}
POLOS = {"ATIVO": "AT", "PASSIVO": "PA"}


class MontagemError(ValueError):
    """Os autos ou o cadastro do tribunal não permitem montar a petição com segurança."""


def conferir_tribunal(cadastro: dict | None, sigla: str) -> None:
    """Para antes de qualquer escrita se o tribunal não recebe petição intercorrente pelo Portal."""
    if not cadastro:
        raise MontagemError(
            f"{sigla} não está no cadastro de peticionamento do Portal: peticione no sistema do tribunal."
        )
    if not cadastro.get("ativo") or PETICAO_INTERCORRENTE not in cadastro.get("funcionalidadesHabilitadas", []):
        raise MontagemError(f"{sigla} não habilita petição intercorrente pelo Portal.")


def conferir_arquivo(cadastro: dict, caminho: Path) -> bytes:
    extensao = caminho.suffix.lower().lstrip(".")
    aceitos = {t["extensao"]: t["tamanhoMaximoMB"] for t in cadastro.get("tiposArquivosAceitos", [])}
    if extensao not in aceitos:
        raise MontagemError(f"{caminho.name}: o tribunal não aceita .{extensao} (aceita {', '.join(sorted(aceitos))}).")
    conteudo = caminho.read_bytes()
    if len(conteudo) > aceitos[extensao] * 1024 * 1024:
        raise MontagemError(
            f"{caminho.name}: {len(conteudo) / 1048576:.1f} MB passa do limite de {aceitos[extensao]} MB."
        )
    return conteudo


def _parte(parte: dict) -> dict[str, Any]:
    documento = (parte.get("documentosPrincipais") or [{}])[0]
    advogados = [
        {"pessoa": {"nome": r["nome"]}, "modalidadeParticipacao": "ADVOGADO"}
        for r in parte.get("representantes", [])
        if r.get("tipoRepresentacao") == "ADVOGADO"
    ]
    return {
        "pessoa": {
            "nome": parte["nome"],
            "modalidadeDocumentoIdentificador": documento.get("tipo"),
            "numeroDocumentoPrincipal": documento.get("numero"),
        },
        "modalidadePolo": POLOS.get(parte.get("polo", ""), parte.get("polo")),
        "assistenciaJudiciaria": bool(parte.get("assistenciaJudiciariaGratuita")),
        "advogados": advogados,
        "participantes": [],
        "representantes": [],
    }


def montar_rascunho(processo: dict, id_tipo_documento: int) -> dict[str, Any]:
    """Petição intercorrente (`tipo` A) ainda sem documentos, a partir de `GET /v2/processos/{cnj}`."""
    tramitacao = processo.get("tramitacaoAtual") or {}
    distribuicao = (tramitacao.get("distribuicao") or [{}])[0]
    orgao = (distribuicao.get("orgaoJulgador") or [{}])[0]
    tribunal = tramitacao.get("tribunal") or orgao.get("tribunal") or {}
    classe = (tramitacao.get("classe") or [{}])[0]
    grau = tramitacao.get("grau") or {}
    if tramitacao.get("permitePeticionar") is False:
        raise MontagemError(
            "O processo não aceita petição pelo Portal (permitePeticionar=false): use o sistema do tribunal."
        )
    if not orgao.get("id") or not distribuicao.get("dataHora"):
        raise MontagemError("Os autos não trazem órgão julgador e data de distribuição: confira o processo no Portal.")
    return {
        "tipo": "A",
        "sigiloso": "NAO",
        "numeroProcesso": processo["numeroProcesso"],
        "idFonteDadosCodex": tramitacao.get("idFonteDadosCodex"),
        "siglaTribunal": tribunal.get("sigla") or processo.get("siglaTribunal"),
        "jtrTribunal": tribunal.get("jtr"),
        "siglaSegmentoJustica": SEGMENTOS.get(tribunal.get("segmento", ""), tribunal.get("segmento")),
        "numeroGrau": str(grau.get("numero", "")),
        "siglaGrau": grau.get("sigla"),
        "codOrgaoJulgadorCorporativo": orgao["id"],
        "nomeOrgaoJulgadorCorporativo": orgao.get("nome"),
        "distribuidoEm": distribuicao["dataHora"].replace("T", " "),
        "codClasseSgt": classe.get("codigo"),
        "codigoClasseProcessual": classe.get("codigo"),
        "nomeClasseSgt": classe.get("descricao"),
        "valorCausa": tramitacao.get("valorAcao"),
        "idTipoDocumento": id_tipo_documento,
        "peticaoAssuntos": [{"codigo": a["codigo"], "nome": a["descricao"]} for a in tramitacao.get("assunto", [])],
        "peticaoPartes": [_parte(p) for p in tramitacao.get("partes", [])],
        "peticaoDocumentos": [],
        "avisosExpedientes": [],
    }


def montar_documento(
    id_peticao: int, caminho: Path, conteudo: bytes, id_tipo_documento: int, ordem: int, principal: bool
) -> dict[str, Any]:
    return {
        "idPeticao": id_peticao,
        "nome": caminho.name,
        "descricao": caminho.stem,
        "mimeType": "application/pdf" if caminho.suffix.lower() == ".pdf" else "application/octet-stream",
        "tamanho": len(conteudo),
        "hash": sha1_hex(conteudo),
        "idTipoDocumento": id_tipo_documento,
        "ordem": ordem,
        "principal": principal,
        "sigiloso": "NAO",
    }


def escolher_tipo(tipos: list[dict], termo: str) -> dict:
    """Aceita o id exato ou um trecho único da descrição; ambiguidade é erro, nunca palpite."""
    if termo.isdigit():
        achados = [t for t in tipos if str(t.get("id")) == termo]
    else:
        achados = [t for t in tipos if termo.casefold() == str(t.get("descricao", "")).casefold()]
        achados = achados or [t for t in tipos if termo.casefold() in str(t.get("descricao", "")).casefold()]
    if len(achados) != 1:
        opcoes = "; ".join(f"{t['id']} {t['descricao']}" for t in achados[:8]) or "nenhum"
        raise MontagemError(f"Tipo de documento '{termo}' não identifica um só tipo ({opcoes}). Use o id.")
    return achados[0]
