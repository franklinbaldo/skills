# /// script
# requires-python = ">=3.12"
# dependencies = ["fastmcp>=2.0", "requests"]
# ///
"""DataJud como servidor MCP — e como CLI, pelo mesmo código.

Por que existe, se `datajud.py` já consulta a API
-------------------------------------------------

O script resolve o transporte; este arquivo resolve a **superfície**. Três
defeitos medidos em uso real (2026-08-19), consultando o trânsito em julgado de
um mandado de segurança:

1. **A invocação não era adivinhável.** A skill documenta
   ``python scripts/datajud.py``, que pressupõe CWD na pasta da skill e
   ``requests`` instalado. De outro repositório, o comando que funciona é
   ``uv run --no-project --with requests python datajud/scripts/datajud.py``.
   Custou duas tentativas. Como tool MCP, não há comando a montar.

2. **A saída não aplicava o conselho da própria skill.** O SKILL.md manda
   destacar "apenas eventos que mudam o estado útil"; `--movimentos` despeja
   tudo. Dos cerca de trinta movimentos daquele processo, **oito eram "Decurso
   de Prazo"**. A orientação existia só como instrução ao agente.

3. **Faltava o caso de uso mais comum.** A pergunta era uma — *transitou?* —
   e nenhum dos verbos (`processo`, `buscar`, `contar`, `codigos`) a respondia
   direto.

Desenho da resposta
-------------------

Segue a regra da skill `mcp-coding`: **resumo primeiro, itens depois**, nunca
lista ilimitada, e o payload cru atrás de flag explícita. `datajud_processo`
devolve o estado do processo em poucas linhas e os **marcos**; a lista completa
de movimentos só com ``incluir_movimentos=True``.

**Marcos por exclusão, não por enumeração.** Listar todos os códigos que
importam é lista longa, instável e que envelhece a cada atualização das Tabelas
Processuais Unificadas do CNJ. O ruído, ao contrário, é pequeno e estável:
decurso de prazo, publicação, disponibilização no DJE, expedição de documento.
Excluir o ruído mantém o filtro correto mesmo quando surge um código de decisão
que ninguém previu — que é justamente o caso em que errar dói.

Uso
---

Como MCP, aponte o cliente para este arquivo. Como CLI::

    uv run datajud_mcp.py processo 7000667-67.2026.8.22.0000
    uv run datajud_mcp.py processo 7000667-67.2026.8.22.0000 --incluir-movimentos
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import datajud as dj  # noqa: E402  — o script vizinho traz search(), retry e formatação

from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("datajud")

# Códigos de movimento que não mudam o estado útil do processo. Ver a docstring
# do módulo: filtra-se o ruído, que é estável, e não os marcos, que não são.
RUIDO = {
    1051,  # Decurso de Prazo
    92,    # Publicação
    1061,  # Disponibilização no Diário da Justiça Eletrônico
    60,    # Expedição de documento
    581,   # Juntada
}


def _marcos(movimentos: list[dict]) -> list[dict]:
    """Movimentos que mudam o estado útil, em ordem cronológica.

    Ordena pelo ``dataHora`` cru da API, em ISO, e não pela data formatada:
    ``dd/mm/aaaa`` ordenado como texto põe 30/04 depois de 22/06. O bug
    apareceu no primeiro teste, no resumo de um processo cujo último marco era
    a baixa definitiva e que anunciava uma petição de dois meses antes.
    """
    saida = []
    for m in movimentos or []:
        codigo = m.get("codigo")
        if codigo in RUIDO:
            continue
        saida.append(
            {
                "data": dj.fmt_data_iso(m.get("dataHora")),
                "_ord": m.get("dataHora") or "",
                "codigo": codigo,
                "nome": m.get("nome"),
            }
        )
    saida.sort(key=lambda x: x["_ord"])
    for x in saida:
        del x["_ord"]
    return saida


@mcp.tool
def datajud_processo(
    cnj: str,
    tribunal: str = "tjro",
    incluir_movimentos: bool = False,
) -> dict[str, Any]:
    """Estado atual de um processo no DataJud: capa, marcos e último ato.

    Responde "onde este processo está" sem despejar a lista inteira de
    movimentos. Um processo pode ter mais de um registro (um por grau); todos
    voltam, cada um com seus próprios marcos.

    - ``cnj``: número do processo, com ou sem pontuação.
    - ``tribunal``: sigla do acervo (``tjro``, ``tjsp``, ``stj``...).
    - ``incluir_movimentos``: quando ``True``, acrescenta a lista completa de
      movimentos, inclusive o ruído. Use só quando o marco procurado não
      aparecer entre os marcos — é payload grande.

    Marcos são todos os movimentos **menos** decurso de prazo, publicação,
    disponibilização no DJE, expedição de documento e juntada.
    """
    numero = dj.so_digitos(cnj)
    body = {
        "size": 50,
        "query": {"match": {"numeroProcesso": numero}},
        "sort": [{"grau.keyword": "asc"}],
    }
    bruto = dj.search(body, tribunal=tribunal)
    hits = bruto.get("hits", {}).get("hits", [])
    if not hits:
        return {
            "processo": dj.cnj(numero),
            "tribunal": tribunal.upper(),
            "encontrado": False,
            "resumo": f"Nenhum registro de {dj.cnj(numero)} no acervo {tribunal.upper()}.",
            "next_actions": [
                {
                    "tool": "datajud_processo",
                    "args": {"cnj": cnj, "tribunal": "<outra sigla>"},
                    "reason": "O processo pode estar no acervo de outro tribunal.",
                }
            ],
        }

    documentos = []
    for h in hits:
        src = h["_source"]
        movimentos = src.get("movimentos") or []
        marcos = _marcos(movimentos)
        doc = {
            "grau": dj.grau_label(src.get("grau")),
            "classe": dj.classe_str(src),
            "assuntos": dj.assuntos_str(src),
            "orgao": dj.orgao_str(src),
            "ajuizamento": dj.fmt_data_ajuiz(src.get("dataAjuizamento")),
            "ultima_atualizacao": dj.fmt_data_iso(src.get("dataHoraUltimaAtualizacao")),
            "marcos": marcos,
            "total_movimentos": len(movimentos),
            "movimentos_omitidos": len(movimentos) - len(marcos),
        }
        if incluir_movimentos:
            doc["movimentos"] = [
                {
                    "data": dj.fmt_data_iso(m.get("dataHora")),
                    "codigo": m.get("codigo"),
                    "nome": m.get("nome"),
                }
                for m in movimentos
            ]
        documentos.append(doc)

    # O último marco do processo é o mais recente entre TODOS os graus — não o
    # último documento da lista, que vem ordenada por grau e não por data.
    def _chave(marco: dict) -> str:
        d = (marco.get("data") or "")  # dd/mm/aaaa hh:mm
        return f"{d[6:10]}{d[3:5]}{d[0:2]}{d[11:]}" if len(d) >= 10 else ""

    todos = [m for d in documentos for m in d["marcos"]]
    ultimo = max(todos, key=_chave) if todos else None
    resumo = (
        f"{dj.cnj(numero)} — {tribunal.upper()} — {len(documentos)} registro(s) de grau. "
        f"Último marco: {ultimo['data']} {ultimo['nome']}." if ultimo
        else f"{dj.cnj(numero)} — {tribunal.upper()} — sem marcos registrados."
    )

    saida: dict[str, Any] = {
        "processo": dj.cnj(numero),
        "tribunal": tribunal.upper(),
        "encontrado": True,
        "resumo": resumo,
        "documentos": documentos,
    }
    if not incluir_movimentos and any(d["movimentos_omitidos"] for d in documentos):
        saida["next_actions"] = [
            {
                "tool": "datajud_processo",
                "args": {"cnj": cnj, "tribunal": tribunal, "incluir_movimentos": True},
                "reason": "Ver também os movimentos de rotina omitidos dos marcos.",
            }
        ]
    return saida


def _cli(argv: list[str]) -> int:
    """CLI mínima sobre as mesmas funções — o padrão do `pink` neste workspace.

    Existe para que o "CLI primeiro" do CLAUDE.md continue valendo sem manter
    duas implementações: a tool é a função, e a CLI só a chama.
    """
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    if argv[0] != "processo":
        sys.stderr.write("Uso: datajud_mcp.py processo <cnj> [--tribunal X] [--incluir-movimentos]\n")
        return 2
    if len(argv) < 2:
        sys.stderr.write("ERRO: informe o número do processo.\n")
        return 2
    tribunal = "tjro"
    if "--tribunal" in argv:
        tribunal = argv[argv.index("--tribunal") + 1]
    resultado = datajud_processo(
        argv[1], tribunal=tribunal, incluir_movimentos="--incluir-movimentos" in argv
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("encontrado") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(_cli(sys.argv[1:]))
    mcp.run()
