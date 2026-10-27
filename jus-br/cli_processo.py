# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""Comandos `jusbr processo`: autos de qualquer tribunal pela base nacional da PDPJ (Codex)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cli_comum as comum
from cli_comum import console
from cyclopts import App, Parameter
from errors import JusBrError
from rich.table import Table

processo_app = App(
    name="processo",
    help="Autos pela base nacional da PDPJ (capa, partes, movimentos, peças).",
    result_action=lambda x: x,
)


def id_documento(documento: dict) -> str:
    """O id que a rota de binário aceita é o UUID dentro de `hrefBinario`, não o `idCodex`."""
    href = documento.get("hrefBinario") or ""
    partes = href.strip("/").split("/")
    return partes[-2] if len(partes) >= 2 else str(documento.get("idCodex", ""))


@processo_app.command(name="consultar")
def processo_consultar(
    cnj: Annotated[str, Parameter(help="Número do processo no formato CNJ.")],
    movimentos: Annotated[int, Parameter(help="Quantos movimentos recentes mostrar.")] = 10,
    json_: Annotated[bool, Parameter(name="--json", help="Imprime a resposta integral em JSON.")] = False,
) -> None:
    """Capa, partes, movimentos e lista de peças do processo."""
    portal = comum.PortalClient()
    try:
        proc = portal.processo(cnj)
    except JusBrError as exc:
        console.print(f"[bold red]Erro ao consultar o processo:[/bold red] {exc}")
        sys.exit(1)
    if json_:
        print(json.dumps(proc, ensure_ascii=False, indent=1))
        return

    tram = proc.get("tramitacaoAtual") or {}
    orgao = ((tram.get("distribuicao") or [{}])[0].get("orgaoJulgador") or [{}])[0]
    capa = Table(title=f"Processo {proc.get('numeroProcesso')}", border_style="magenta", show_header=False)
    capa.add_row("Tribunal", f"{proc.get('siglaTribunal')} (JTR {(tram.get('tribunal') or {}).get('jtr', '-')})")
    capa.add_row("Órgão julgador", f"{orgao.get('nome', '-')} (id {orgao.get('id', '-')})")
    capa.add_row("Classe", ", ".join(c.get("descricao", "") for c in tram.get("classe", [])) or "-")
    capa.add_row("Assunto", ", ".join(a.get("descricao", "") for a in tram.get("assunto", [])) or "-")
    capa.add_row("Ajuizamento", str(tram.get("dataHoraAjuizamento", "-")))
    capa.add_row("Valor da causa", str(tram.get("valorAcao", "-")))
    capa.add_row("Aceita petição pelo Portal", {True: "sim", False: "não"}.get(tram.get("permitePeticionar"), "-"))
    for parte in tram.get("partes", []):
        advs = ", ".join(r["nome"] for r in parte.get("representantes", []))
        capa.add_row(f"Polo {parte.get('polo', '').lower()}", parte["nome"] + (f" — {advs}" if advs else ""))
    console.print(capa)

    movs = Table(title="Movimentos recentes", border_style="blue")
    movs.add_column("Data", style="bold")
    movs.add_column("Descrição")
    for mov in tram.get("movimentos", [])[:movimentos]:
        movs.add_row(mov.get("dataHora", "-"), mov.get("descricao", "-"))
    console.print(movs)

    pecas = Table(title="Peças (use o id em `processo baixar`)", border_style="green")
    for coluna in ("Seq.", "Juntada", "Tipo", "Nome", "Id"):
        pecas.add_column(coluna)
    for doc in tram.get("documentos") or proc.get("documentos") or []:
        pecas.add_row(
            str(doc.get("sequencia", "")),
            str(doc.get("dataHoraJuntada", "")),
            (doc.get("tipo") or {}).get("nome", "-"),
            doc.get("nome", "-"),
            id_documento(doc),
        )
    console.print(pecas)


@processo_app.command(name="baixar")
def processo_baixar(
    cnj: Annotated[str, Parameter(help="Número do processo no formato CNJ.")],
    documento: Annotated[str, Parameter(help="Id da peça, como `processo consultar` mostra.")],
    saida: Annotated[Path, Parameter(name=["--saida", "-o"], help="Arquivo de destino.")],
) -> None:
    """Grava o arquivo original de uma peça dos autos."""
    portal = comum.PortalClient()
    try:
        conteudo, tipo = portal.documento(cnj, documento)
    except JusBrError as exc:
        console.print(f"[bold red]Erro ao baixar a peça:[/bold red] {exc}")
        sys.exit(1)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_bytes(conteudo)
    console.print(f"Peça gravada em [bold]{saida}[/bold] ({len(conteudo):,} bytes, {tipo or 'tipo não informado'}).")
