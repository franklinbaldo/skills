# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Consultas sobre os datasets do Leizilla: buscar, norma, relacoes. (Texto: `legislacao_texto.py`.)"""

from __future__ import annotations

from typing import Any

from legislacao_citacao import SIGLA_TIPO, Citacao, parse_citacao, termos_busca
from legislacao_dados import Acervo

VERBOS = ("altera", "revoga", "acrescenta", "da-nova-redacao", "regulamenta", "prorroga", "outro")
SITUACOES = ("revogada", "retificada", "tem-compilada", "sem-indicacao-de-revogacao")

# verbo -> (a norma age, a norma sofre)
ROTULOS_VERBO = {
    "altera": ("altera", "alterada por"),
    "revoga": ("revoga", "revogada por"),
    "acrescenta": ("acrescenta dispositivos a", "recebeu dispositivos acrescentados por"),
    "da-nova-redacao": ("dá nova redação a", "teve redação dada por"),
    "regulamenta": ("regulamenta", "regulamentada por"),
    "prorroga": ("prorroga", "prorrogada por"),
    "outro": ("outro ato sobre", "objeto de outro ato de"),
}

LEITURA_SITUACAO = {
    "revogada": "o índice marca a norma como revogada (arquivo 'revogado' ou anotação 'REVOGADO PELO...' na ementa); "
    "confirme no texto oficial e em norma posterior",
    "retificada": "o índice lista um arquivo de retificação; não é marca de revogação nem de vigência",
    "tem-compilada": "o índice lista uma versão compilada (a norma pode ter sido alterada); não é marca de revogação "
    "nem de vigência",
    "sem-indicacao-de-revogacao": "o índice não marca revogação; isso NÃO significa que a norma esteja em vigor "
    "(pode haver revogação tácita, suspensão judicial ou superação sem marca)",
}

AVISO_RELACOES = (
    "relações extraídas automaticamente das ementas por regras (precisão medida em ~94%+ em amostras lidas à mão): "
    "são pistas a conferir, não o histórico completo de alterações (alterações citadas só no corpo da norma não "
    "aparecem); 'altera a composição de órgão nomeado pelo Decreto X' é registrado como alteração de X"
)


class UsoInvalido(Exception):
    """Argumento que não faz sentido (exit 2)."""


class NaoEncontrado(Exception):
    """Nada correspondente nos dados (exit 1); `detalhe` leva candidatos ou dicas."""

    def __init__(self, mensagem: str, detalhe: dict[str, Any] | None = None) -> None:
        super().__init__(mensagem)
        self.detalhe = detalhe or {}


def estagio_de(preservada: Any, legivel: Any, estruturada: Any) -> str:
    """Estagio mais avancado sabido. Flag NULL e 'nao medido', nunca falso."""
    if estruturada:
        return "estruturada"
    if legivel:
        return "legivel"
    if preservada:
        return "preservada"
    if preservada is None and legivel is None and estruturada is None:
        return "nao-medido"
    return "so-catalogada"


def aviso_rendicao(linha: dict[str, Any]) -> str | None:
    """Alerta quando o índice só lista versões não originais (o link oficial não é a publicação original)."""
    listadas = [r for r in (linha.get("rendicoes") or "").split(",") if r]
    if listadas and "original" not in listadas:
        return (
            f"o índice lista apenas arquivo(s) de rendição '{', '.join(listadas)}': o link oficial NÃO é a publicação "
            "original (compilação/versão anotada da Casa Civil); confirme a redação original no Diário Oficial"
        )
    return None


def link_de(linha: dict[str, Any]) -> str | None:
    return linha.get("link_publico") or linha.get("url_ia") or linha.get("url_oficial")


def citacao_curta(linha: dict[str, Any]) -> str:
    base = f"{SIGLA_TIPO.get(linha['tipo'], linha['tipo'])} {linha['numero']}{(linha.get('sufixo') or '').upper()}"
    return f"{base}/{linha['ano_ref']}" if linha.get("ano_ref") else base


def resumo_norma(linha: dict[str, Any]) -> dict[str, Any]:
    return {
        "norma_id": linha["norma_id"],
        "identificacao": linha["titulo"],
        "citacao_curta": citacao_curta(linha),
        "tipo": linha["tipo"],
        "numero": linha["numero"],
        "sufixo": linha["sufixo"] or "",
        "data": linha["data"],
        "ementa": linha["ementa"],
        "situacao_no_indice": linha["situacao_norma"],
        "estagio": estagio_de(linha["preservada"], linha["legivel"], linha["estruturada"]),
        "link": link_de(linha),
    }


def _condicoes_citacao(cit: Citacao) -> tuple[list[str], list[Any]]:
    onde, params = ["tipo = ?", "numero = ?"], [cit.tipo, cit.numero]
    if cit.sufixo:
        onde.append("lower(sufixo) = ?")
        params.append(cit.sufixo)
    if cit.ano is not None:
        onde.append("ano_ref = ?")
        params.append(cit.ano)
    return onde, params


def _numerico(termo: str) -> bool:
    return termo.isdigit() and len(termo) <= 9


def buscar(
    acervo: Acervo,
    consulta: str,
    *,
    tipo: str | None = None,
    ano: int | None = None,
    de: int | None = None,
    ate: int | None = None,
    situacao: str | None = None,
    limite: int = 20,
) -> dict[str, Any]:
    """Citacao direta ou busca por assunto (todos os termos, sem acento, inicio de palavra) sobre o catalogo."""
    acervo.exige("catalogo")
    if situacao and acervo.catalogo_antigo:
        raise UsoInvalido("--situacao exige catálogo com situacao_norma; o catálogo carregado está no formato 0.1")
    onde: list[str] = []
    params: list[Any] = []
    for coluna, operador, valor in (
        ("tipo", "=", tipo),
        ("ano_ref", "=", ano),
        ("ano_ref", ">=", de),
        ("ano_ref", "<=", ate),
        ("situacao_norma", "=", situacao),
    ):
        if valor is not None and valor != "":
            onde.append(f"{coluna} {operador} ?")
            params.append(valor)
    citacao = parse_citacao(consulta) if consulta.strip() else None
    numericos: list[int] = []
    modo = "filtros"
    if citacao:
        modo = "citacao"
        o2, p2 = _condicoes_citacao(citacao)
        onde += o2
        params += p2
    elif consulta.strip():
        modo = "texto"
        termos = termos_busca(consulta)
        numericos = [int(t) for t in termos if _numerico(t)]
        for termo in termos:
            if _numerico(termo):
                onde.append("(numero = ? OR (' ' || busca || ' ') LIKE ?)")
                params += [int(termo), f"% {termo} %"]
            else:
                onde.append("(' ' || busca) LIKE ?")
                params.append(f"% {termo}%")
    elif not onde:
        raise UsoInvalido("informe termos de busca, uma citação (ex.: 'LC 68/1992') ou algum filtro")
    clausula = ("WHERE " + " AND ".join(onde)) if onde else ""
    total = acervo.consulta(f"SELECT count(*) AS n FROM catalogo {clausula}", params)[0]["n"]
    # Ordem: numero exato primeiro (so se a consulta tem numeros), depois mais recentes.
    exato = f"CASE WHEN numero IN ({', '.join('?' for _ in numericos)}) THEN 0 ELSE 1 END, " if numericos else ""
    linhas = acervo.consulta(
        f"SELECT * FROM catalogo {clausula} ORDER BY {exato}data DESC NULLS LAST, numero DESC, norma_id LIMIT ?",
        [*params, *numericos, max(limite, 0)],
    )
    resultado: dict[str, Any] = {
        "consulta": consulta,
        "modo": modo,
        "citacao_reconhecida": citacao.curta() if citacao else None,
        "total": total,
        "retornados": len(linhas),
        "resultados": [resumo_norma(linha) for linha in linhas],
        "avisos": list(dict.fromkeys(acervo.avisos)),
    }
    if modo == "citacao" and not linhas:
        resultado["dica"] = "citação sem correspondência no catálogo: confira tipo, número e ano; não há busca textual"
    return resultado


def localizar(acervo: Acervo, referencia: str) -> dict[str, Any]:
    """Uma norma do catalogo por `norma_id` ou citacao; ambiguidade e ausencia sao NaoEncontrado/UsoInvalido."""
    acervo.exige("catalogo")
    referencia = referencia.strip()
    if referencia.startswith("leizilla-raw-"):
        linhas = acervo.consulta("SELECT * FROM catalogo WHERE norma_id = ?", [referencia])
        if not linhas:
            raise NaoEncontrado(f"norma_id não encontrado no catálogo: {referencia}")
        return linhas[0]
    citacao = parse_citacao(referencia)
    if citacao is None:
        raise UsoInvalido(
            f"'{referencia}' não parece uma citação (ex.: 'LC 68/1992', 'Lei 1.234', 'Decreto 12345') nem um norma_id"
        )
    onde, params = _condicoes_citacao(citacao)
    linhas = acervo.consulta(f"SELECT * FROM catalogo WHERE {' AND '.join(onde)} ORDER BY sufixo, data", params)
    if not citacao.sufixo and len(linhas) > 1:
        linhas = [x for x in linhas if not x["sufixo"]] or linhas
    if not linhas:
        if citacao.ano:
            o2, p2 = _condicoes_citacao(Citacao(citacao.tipo, citacao.numero, citacao.sufixo))
            outras = acervo.consulta(f"SELECT * FROM catalogo WHERE {' AND '.join(o2)}", p2)
            if outras:
                achadas = [resumo_norma(x) for x in outras]
                raise NaoEncontrado(
                    f"{citacao.curta()}: existe {citacao.tipo} {citacao.numero}, mas com data diferente do ano "
                    f"informado ({', '.join(str(x['data']) for x in achadas)}); confirme a citação",
                    {"candidatos": achadas},
                )
        raise NaoEncontrado(f"{citacao.curta()}: não consta do catálogo de normas listadas pela Casa Civil")
    if len(linhas) > 1:
        raise NaoEncontrado(
            f"{citacao.curta()} é ambígua ({len(linhas)} normas); use o norma_id",
            {"candidatos": [resumo_norma(x) for x in linhas]},
        )
    return linhas[0]


def _item_relacao(linha: dict[str, Any], lado_da_outra: str) -> dict[str, Any]:
    outra = None
    if linha.get("o_norma_id"):
        base = {k[2:]: v for k, v in linha.items() if k.startswith("o_")}
        outra = {
            "norma_id": base["norma_id"],
            "identificacao": base["titulo"],
            "citacao_curta": citacao_curta(base),
            "data": base["data"],
            "link": link_de(base),
        }
    return {
        "relacao_id": linha["relacao_id"],
        "verbo": linha["verbo"],
        "verbo_texto": linha["verbo_texto"],
        "parcial": bool(linha["parcial"]),
        "outra_norma": outra,
        "como_escrito": linha["alvo_texto"],
        "resolvida": linha["confianca"] == "resolvida" and outra is not None,
        "confianca": linha["confianca"],
        "nota": linha["nota"],
        "fonte_relacao": linha["fonte_relacao"],
        "trecho": linha["trecho"],
        "lado_da_outra": lado_da_outra,
    }


_COLUNAS_OUTRA = ", ".join(
    f"o.{c} AS o_{c}"
    for c in (
        "norma_id",
        "tipo",
        "numero",
        "sufixo",
        "titulo",
        "data",
        "ano_ref",
        "link_publico",
        "url_ia",
        "url_oficial",
    )
)


def relacoes_de(
    acervo: Acervo, norma_id: str, direcao: str = "ambas", verbo: str | None = None
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Relacoes da norma por verbo: `saida` (a norma age) e `entrada` (a norma e o alvo)."""
    acervo.exige("relacoes")
    extra = " AND r.verbo = ?" if verbo else ""
    pv = [verbo] if verbo else []
    ordem = "ORDER BY r.verbo, o.data DESC NULLS LAST, r.relacao_id"
    resultado: dict[str, dict[str, list[dict[str, Any]]]] = {"saida": {}, "entrada": {}}
    for lado, minha, outra in (("saida", "origem_id", "alvo_id"), ("entrada", "alvo_id", "origem_id")):
        if direcao not in ("ambas", lado):
            continue
        linhas = acervo.consulta(
            f"SELECT r.*, {_COLUNAS_OUTRA} FROM relacoes r LEFT JOIN catalogo o ON o.norma_id = r.{outra} "
            f"WHERE r.{minha} = ?{extra} {ordem}",
            [norma_id, *pv],
        )
        for linha in linhas:
            resultado[lado].setdefault(linha["verbo"], []).append(
                _item_relacao(linha, "alvo" if lado == "saida" else "origem")
            )
    return resultado


def _ou(verificado: bool | None, flag: Any) -> Any:
    """Presença verificada na tabela vale mais que a flag; ausência verificada só decide quando a flag é nula."""
    if verificado:
        return True
    return False if verificado is False and flag is None else flag


def _cobertura(acervo: Acervo, linha: dict[str, Any]) -> dict[str, Any]:
    flags = {k: linha[k] for k in ("preservada", "com_texto", "legivel", "estruturada")}
    tem_texto = tem_estrutura = None
    if acervo.opcional("textos"):
        tem_texto = bool(acervo.consulta("SELECT 1 FROM textos WHERE texto_id = ? LIMIT 1", [linha["texto_id"]]))
    if acervo.opcional("versoes"):
        padrao = f'%"{linha["texto_id"]}"%'
        tem_estrutura = bool(acervo.consulta("SELECT 1 FROM versoes WHERE fontes LIKE ? LIMIT 1", [padrao]))
    return {
        "estagio": estagio_de(
            linha["preservada"],
            _ou(tem_texto, linha["legivel"]),
            _ou(tem_estrutura, linha["estruturada"]),
        ),
        "flags_do_catalogo": flags,
        "texto_na_camada_textos": tem_texto,
        "estrutura_em_versoes": tem_estrutura,
        "leitura": "só catalogada < preservada (PDF no IA) < legível (OCR em `textos`) < estruturada (`versoes`); "
        "flag nula = não medido",
    }


def norma(acervo: Acervo, referencia: str) -> dict[str, Any]:
    linha = localizar(acervo, referencia)
    base = resumo_norma(linha)
    evidencias = [e for e in (linha["situacao_evidencias"] or "").split(",") if e]
    situacao: dict[str, Any] = {
        "valor": linha["situacao_norma"],
        "evidencias": evidencias,
        "leitura": LEITURA_SITUACAO.get(linha["situacao_norma"] or "", "situação não disponível neste catálogo"),
        "aviso": "marca do índice oficial da Casa Civil; não é parecer de vigência",
    }
    saida: dict[str, Any] = {
        "norma": {k: base[k] for k in ("norma_id", "identificacao", "citacao_curta", "tipo", "numero", "sufixo")}
        | {"data": linha["data"], "ano": linha["ano_ref"], "ementa": linha["ementa"], "coddoc": linha["coddoc"]},
        "situacao_no_indice": situacao,
        "links": {
            "oficial": linha["url_oficial"],
            "internet_archive": linha["url_ia"],
            "melhor": link_de(linha),
            "rendicoes_listadas": linha["rendicoes"],
            "aviso": aviso_rendicao(linha),
        },
        "identidade_incerta": linha["identidade_incerta"],
        "cobertura": _cobertura(acervo, linha),
    }
    if acervo.opcional("relacoes"):
        agrupado = relacoes_de(acervo, linha["norma_id"])
        saida["relacoes"] = {**agrupado, "aviso": AVISO_RELACOES}
        revogam = [i for i in agrupado["entrada"].get("revoga", []) if not i["parcial"]]
        if revogam and linha["situacao_norma"] != "revogada":
            situacao["nota_relacoes"] = (
                "há relação 'revogada por' (total) nas ementas, mas o índice não marca a norma como revogada"
            )
    else:
        saida["relacoes"] = None
    saida["avisos"] = list(dict.fromkeys(acervo.avisos))
    return saida


def relacoes(acervo: Acervo, referencia: str, direcao: str = "ambas", verbo: str | None = None) -> dict[str, Any]:
    if direcao not in ("ambas", "saida", "entrada"):
        raise UsoInvalido("--direcao deve ser ambas, saida ou entrada")
    if verbo and verbo not in VERBOS:
        raise UsoInvalido(f"--verbo deve ser um de: {', '.join(VERBOS)}")
    linha = localizar(acervo, referencia)
    agrupado = relacoes_de(acervo, linha["norma_id"], direcao, verbo)
    return {
        "norma": resumo_norma(linha),
        "relacoes": agrupado,
        "contagem": {lado: sum(len(v) for v in grupos.values()) for lado, grupos in agrupado.items()},
        "aviso": AVISO_RELACOES,
        "avisos": list(dict.fromkeys(acervo.avisos)),
    }
