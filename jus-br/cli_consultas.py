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
"""Comandos de consulta: perfil, comunicações (ComunicaAPI e Portal), Domicílio Eletrônico e GET livre."""

from __future__ import annotations

import sys
from typing import Annotated

import cli_comum as comum
from cli_comum import console
from cyclopts import App, Parameter
from rich.table import Table

usuario_app = App(name="usuario", help="Consultas sobre o perfil na PDPJ.", result_action=lambda x: x)
comunicacoes_app = App(
    name="comunicacoes", help="Consulta de intimações e comunicações oficiais.", result_action=lambda x: x
)
api_app = App(name="api", help="Exploração direta de endpoints da API PDPJ.", result_action=lambda x: x)


@usuario_app.command(name="obter")
def usuario_obter() -> None:
    """Consulta dados cadastrais do usuário na PDPJ/Jus.br."""
    client = comum.JusBrClient()
    try:
        perfil = client.obter_perfil()
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar perfil na PDPJ:[/bold red] {exc}")
        sys.exit(1)

    table = Table(title="Perfil do Usuário - PDPJ / Jus.br", border_style="green")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")

    table.add_row("Nome", perfil.name or "-")
    table.add_row("Login / Usuário", perfil.preferred_username or "-")
    table.add_row("CPF", perfil.cpf_mascarado())
    if perfil.oab:
        table.add_row("OAB", perfil.oab)
    table.add_row("E-mail", perfil.email or "-")
    table.add_row("Perfis / Papéis", ", ".join(perfil.roles) if perfil.roles else "Padrão")

    console.print(table)


@comunicacoes_app.command(name="buscar")
def comunicacoes_buscar(
    processo: Annotated[str, Parameter(help="Filtrar por número do processo (só dígitos ou CNJ).")] = "",
    tribunal: Annotated[str, Parameter(help="Filtrar por sigla do tribunal (ex: TJRO, TRF1, STJ).")] = "",
    data: Annotated[str, Parameter(help="Filtrar por data de disponibilização (YYYY-MM-DD).")] = "",
    pagina: Annotated[int, Parameter(help="Número da página (inicia em 1).")] = 1,
    itens: Annotated[int, Parameter(help="Quantidade de itens por página.")] = 10,
) -> None:
    """Consulta intimações, editais e publicações oficiais em tempo real (ComunicaAPI/PJe)."""
    client = comum.JusBrClient()
    try:
        resp = client.buscar_comunicacoes(
            numero_processo=processo,
            sigla_tribunal=tribunal,
            data_disponibilizacao=data,
            pagina=pagina,
            itens_por_pagina=itens,
        )
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar comunicações:[/bold red] {exc}")
        sys.exit(1)

    if not resp.items:
        console.print("[yellow]Nenhuma comunicação encontrada para os filtros informados.[/yellow]")
        return

    table = Table(title=f"Comunicações e Publicações Oficiais (Página {pagina})", border_style="blue")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Data", style="bold")
    table.add_column("Tribunal", style="green")
    table.add_column("Tipo")
    table.add_column("Processo", style="bold", no_wrap=True)
    table.add_column("Órgão Julgador")

    for item in resp.items:
        table.add_row(
            str(item.id),
            item.data_disponibilizacao or "-",
            item.siglaTribunal or "-",
            item.tipoComunicacao or "-",
            item.numero_processo or "-",
            item.nomeOrgao or "-",
        )

    console.print(table)
    console.print(f"[dim]Total de registros encontrados na base nacional: {resp.count}[/dim]")


@api_app.command(name="get")
def api_get(
    path: Annotated[str, Parameter(help="Caminho relativo a /api do Portal (ex.: v1/usuario).")],
) -> None:
    """GET autenticado no Portal de Serviços, para rotas do Swagger ainda sem comando próprio."""
    portal = comum.PortalClient()
    try:
        data = portal.get(path)
        if isinstance(data, (dict, list)):
            console.print_json(data=data)
        else:
            console.print(data)
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar API PDPJ:[/bold red] {exc}")
        sys.exit(1)


@comunicacoes_app.command(name="domicilio")
def comunicacoes_domicilio(
    inicio: Annotated[str, Parameter(help="Início da janela (AAAA-MM-DD).")],
    fim: Annotated[str, Parameter(help="Fim da janela (AAAA-MM-DD), no máximo 7 dias depois.")],
) -> None:
    """Comunicações do usuário no Domicílio Judicial Eletrônico, pelo Portal de Serviços."""
    try:
        itens = comum.PortalClient().domicilio(f"{inicio}T00:00:00Z", f"{fim}T23:59:59Z")
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar o Domicílio Eletrônico:[/bold red] {exc}")
        sys.exit(1)
    if not itens:
        console.print(f"[yellow]Nenhuma comunicação no Domicílio Eletrônico entre {inicio} e {fim}.[/yellow]")
        return
    console.print_json(data=itens)
