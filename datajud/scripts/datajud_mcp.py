#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.0",
#     "cyclopts>=3.0",
#     "rich>=13.0",
# ]
# ///
"""DataJud como servidor MCP — e como CLI, pelo mesmo código.

Por que existe, se `datajud.py` já consulta a API
-------------------------------------------------

O script resolve o transporte; este arquivo resolve a **superfície**. Três
defeitos medidos em uso real (2026-08-19), consultando o trânsito em julgado de
um mandado de segurança:

1. **A invocação não era adivinhável.** A skill documentava
   ``python scripts/datajud.py``, que pressupõe CWD na pasta da skill e as
   dependências já instaladas; de outro repositório era preciso remontar o
   comando à mão. Custou duas tentativas. Hoje o cabeçalho PEP 723 reduz isso
   a ``uv run datajud/scripts/datajud.py`` — e, como tool MCP, não há comando
   a montar.

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

A CLI mantém esse mesmo contrato, mas separa apresentação humana e saída de
máquina: por padrão Cyclopts + Rich exibem painéis e tabelas compactas; ``--json``
imprime o payload integral sem decoração.

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
    uv run datajud_mcp.py processo 7000667-67.2026.8.22.0000 --json
    uv run datajud_mcp.py processo 7000667-67.2026.8.22.0000 --incluir-movimentos
"""

from __future__ import annotations

import json as jsonlib
import sys
from pathlib import Path
from typing import Any

import cyclopts
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP  # noqa: E402

import datajud as dj  # noqa: E402  — o script vizinho traz search(), retry e formatação

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

MARCOS_VISIVEIS = 12


def _marcos(movimentos: list[dict]) -> list[dict]:
    """Movimentos que mudam o estado útil, em ordem cronológica.

    Cada marco carrega ``_ord``, o ``dataHora`` cru da API em ISO. **Esse campo
    é o único critério de ordenação válido, e sobrevive até o cálculo do último
    marco global** — só então é removido, por :func:`_publicar`.

    Duas armadilhas, ambas encontradas em revisão:

    1. Ordenar pela data formatada ``dd/mm/aaaa`` compara como texto e põe 30/04
       depois de 22/06.
    2. Mesmo corrigindo a ordenação dentro de cada grau, comparar a data
       formatada para achar o último marco **entre** graus perde segundos e
       fuso: ``fmt_data_iso`` corta em ``HH:MM``, de modo que 09:45:01 e
       09:45:59 empatam e o desempate cai na ordem de iteração.
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
    return saida


def _publicar(marcos: list[dict]) -> list[dict]:
    """Remove a chave interna de ordenação da saída pública."""
    return [{k: v for k, v in m.items() if k != "_ord"} for m in marcos]


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
    # último documento da lista, que vem ordenada por grau e não por data. A
    # comparação usa o timestamp cru; a data formatada perde segundos e fuso.
    todos = [m for d in documentos for m in d["marcos"]]
    ultimo = max(todos, key=lambda m: m["_ord"]) if todos else None

    # Só agora a chave interna sai: ela precisou sobreviver ao max() acima.
    for doc in documentos:
        doc["marcos"] = _publicar(doc["marcos"])
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


def _meta_table(doc: dict[str, Any]) -> Table:
    """Tabela vertical compacta da capa de um grau."""
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Campo", style="bold cyan", no_wrap=True)
    table.add_column("Valor")
    for label, key in (
        ("Classe", "classe"),
        ("Assunto", "assuntos"),
        ("Órgão", "orgao"),
        ("Ajuizamento", "ajuizamento"),
        ("Atualização", "ultima_atualizacao"),
    ):
        table.add_row(label, str(doc.get(key) or "-"))
    return table


def _movimentos_table(doc: dict[str, Any], incluir_movimentos: bool) -> Table:
    """Renderiza marcos recentes ou, quando solicitado, a movimentação completa."""
    if incluir_movimentos:
        itens = doc.get("movimentos") or []
        titulo = f"Movimentos ({len(itens)})"
    else:
        todos = doc.get("marcos") or []
        itens = todos[-MARCOS_VISIVEIS:]
        ocultos = max(0, len(todos) - len(itens))
        sufixo = f" · {ocultos} marco(s) anterior(es) oculto(s)" if ocultos else ""
        titulo = f"Marcos recentes ({len(itens)}/{len(todos)}){sufixo}"

    table = Table(title=titulo, box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Data", no_wrap=True)
    table.add_column("Código", justify="right", no_wrap=True)
    table.add_column("Movimento")
    for item in itens:
        table.add_row(str(item.get("data") or "-"), str(item.get("codigo") or "-"), str(item.get("nome") or "-"))
    return table


def _next_actions_panel(actions: list[dict[str, Any]]) -> Panel | None:
    """Transforma as continuações MCP em comandos CLI legíveis."""
    if not actions:
        return None
    body = Text()
    for idx, action in enumerate(actions, 1):
        args = action.get("args") or {}
        cmd_args = []
        for key, value in args.items():
            if key == "cnj":
                cmd_args.insert(0, str(value))
            elif value is True:
                cmd_args.append(f"--{key.replace('_', '-')}")
            else:
                cmd_args.append(f"--{key.replace('_', '-')} {value}")
        body.append(f"{idx}. ", style="dim")
        body.append("datajud-mcp processo " + " ".join(cmd_args), style="bold cyan")
        reason = action.get("reason")
        if reason:
            body.append(f"\n   {reason}", style="dim")
        if idx < len(actions):
            body.append("\n")
    return Panel(body, title="⏭️ Próximos passos", border_style="cyan", box=box.ROUNDED)


def _render_human(resultado: dict[str, Any], *, incluir_movimentos: bool) -> None:
    """Projeção humana da resposta MCP; nunca altera o payload retornado pela tool."""
    console = Console()
    encontrado = bool(resultado.get("encontrado"))
    titulo = f"⚖️ {resultado.get('processo', '-')} · {resultado.get('tribunal', '-')}"
    estilo = "green" if encontrado else "yellow"
    console.print(Panel(str(resultado.get("resumo") or ""), title=titulo, border_style=estilo, box=box.ROUNDED))

    if encontrado:
        for doc in resultado.get("documentos") or []:
            grau = str(doc.get("grau") or "Grau")
            console.print(Panel(_meta_table(doc), title=f"📁 {grau}", border_style="blue", box=box.ROUNDED))
            console.print(_movimentos_table(doc, incluir_movimentos))
            if not incluir_movimentos and doc.get("movimentos_omitidos"):
                console.print(
                    Text(
                        f"{doc['movimentos_omitidos']} movimento(s) de rotina omitido(s) dos marcos deste grau.",
                        style="dim",
                    )
                )

    next_panel = _next_actions_panel(resultado.get("next_actions") or [])
    if next_panel is not None:
        console.print(next_panel)


app = cyclopts.App(name="datajud-mcp", help=__doc__)


@app.command
def processo(
    numero: str,
    *,
    tribunal: str = "tjro",
    incluir_movimentos: bool = False,
    json: bool = False,
) -> int:
    """Estado do processo e seus marcos — a mesma função exposta como tool MCP.

    Parameters
    ----------
    numero
        número do processo (com ou sem máscara CNJ).
    tribunal
        sigla do índice (padrão tjro).
    incluir_movimentos
        inclui a linha completa de movimentação. Na visão humana, mostra a
        tabela integral; use apenas quando necessário.
    json
        imprime o payload MCP integral em JSON, sem decoração Rich.
    """
    resultado = datajud_processo(
        numero, tribunal=tribunal, incluir_movimentos=incluir_movimentos
    )
    if json:
        print(jsonlib.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        _render_human(resultado, incluir_movimentos=incluir_movimentos)
    return 0 if resultado.get("encontrado") else 1


@app.default
def serve() -> int:
    """Sobe o servidor MCP (comportamento padrão, sem argumentos)."""
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(app() or 0)
