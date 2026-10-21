#!/usr/bin/env -S uv run --script
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
"""Interface de linha de comando para o DESARQ/TJRO com autenticação OIDC/gov.br."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Permite importação dos módulos locais quando executado como script isolado
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from auth import AuthService  # noqa: E402
from client import DesarqClient  # noqa: E402
from credentials import CredentialStore  # noqa: E402
from errors import (  # noqa: E402
    DesarqAuthError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)

console = Console()

app = App(
    name="desarq",
    help="CLI para consulta e operações no DESARQ/TJRO com autenticação segura.",
    result_action=lambda x: x,
)
auth_app = App(name="auth", help="Gerenciamento de autenticação e sessão.", result_action=lambda x: x)
usuario_app = App(name="usuario", help="Consultas sobre o usuário autenticado.", result_action=lambda x: x)
solicitacoes_app = App(
    name="solicitacoes", help="Consultas de solicitações de desarquivamento.", result_action=lambda x: x
)

app.command(auth_app)
app.command(usuario_app)
app.command(solicitacoes_app)


@auth_app.command(name="login")
def auth_login(
    force: Annotated[bool, Parameter(help="Forçar novo login mesmo se já houver sessão ativa.")] = False,
    timeout: Annotated[int, Parameter(help="Tempo limite (segundos) aguardando autenticação no navegador.")] = 180,
    no_browser: Annotated[bool, Parameter(help="Não abrir o navegador automaticamente.")] = False,
    idp: Annotated[str, Parameter(help="Provedor de identidade inicial ('govbr' ou 'cnj').")] = "govbr",
) -> None:
    """Inicia autenticação interativa via gov.br com PKCE no navegador."""
    store = CredentialStore()
    auth = AuthService(credential_store=store)
    client = DesarqClient(auth_service=auth)

    if not force:
        try:
            auth.ensure_valid_tokens()
            # Valida chamando me
            me = client.get_me()
            console.print("[green]Sessão ativa e válida no keyring.[/green]")
            console.print(f"Usuário: [bold]{me.nome}[/bold] (CPF: {me.cpf_mascarado()})")
            return
        except (SessionExpiredError, RefreshTokenRevokedError):
            pass
        except Exception as exc:
            console.print(f"[yellow]Sessão anterior não pôde ser reaproveitada: {exc}[/yellow]")

    console.print(
        Panel(
            f"[bold cyan]Autenticação DESARQ/TJRO[/bold cyan]\n\n"
            f"1. Uma janela do seu navegador padrão será aberta na página oficial de login ({idp}).\n"
            f"2. Digite sua senha gov.br e confirme MFA caso solicitado diretamente na página oficial.\n"
            f"3. Nenhuma credencial ou senha é compartilhada com o terminal ou agente.\n"
            f"4. Aguardando retorno na porta local de callback por até {timeout}s...",
            title="Login Interativo",
            border_style="cyan",
        )
    )

    try:
        auth.login(
            open_browser=not no_browser,
            timeout=float(timeout),
            force=True,
            idp_hint=idp,
        )
        me = client.get_me()
        console.print("[bold green]Autenticação concluída com sucesso![/bold green]")
        console.print(f"Bem-vindo(a), [bold]{me.nome}[/bold] (CPF: {me.cpf_mascarado()})")
    except TimeoutError as exc:
        console.print(f"[bold red]Tempo esgotado:[/bold red] {exc}")
        sys.exit(1)
    except DesarqAuthError as exc:
        console.print(f"[bold red]Falha na autenticação:[/bold red] {exc}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Erro inesperado:[/bold red] {exc}")
        sys.exit(1)


@auth_app.command(name="status")
def auth_status() -> None:
    """Verifica a situação da sessão atual no keyring."""
    store = CredentialStore()
    tokens = store.load_tokens()

    if not tokens:
        console.print("[yellow]Status: Não autenticado.[/yellow] (Nenhuma sessão encontrada no keyring)")
        return

    table = Table(title="Status da Sessão DESARQ", border_style="cyan")
    table.add_column("Propriedade", style="bold")
    table.add_column("Valor")

    table.add_row("Keyring", "Conectado (Windows Credential Manager)")

    now = time.time()
    at_remaining = int((tokens.created_at + tokens.expires_in) - now)
    if at_remaining > 0:
        table.add_row("Access Token", f"[green]Válido ({at_remaining}s restantes)[/green]")
    else:
        table.add_row("Access Token", f"[yellow]Expirado há {abs(at_remaining)}s (renovável via refresh)[/yellow]")

    if tokens.refresh_token:
        if tokens.refresh_expires_in:
            rt_remaining = int((tokens.created_at + tokens.refresh_expires_in) - now)
            if rt_remaining > 0:
                table.add_row("Refresh Token", f"[green]Ativo ({rt_remaining // 60} min restantes)[/green]")
            else:
                table.add_row("Refresh Token", "[red]Expirado[/red]")
        else:
            table.add_row("Refresh Token", "[green]Ativo[/green]")
    else:
        table.add_row("Refresh Token", "[red]Ausente[/red]")

    auth = AuthService(credential_store=store)
    client = DesarqClient(auth_service=auth)
    try:
        me = client.get_me()
        table.add_row("Estado", "[bold green]Sessão Ativa e Operacional[/bold green]")
        table.add_row("Usuário", f"{me.nome} ({me.cpf_mascarado()})")
        table.add_row("Login", me.login)
    except Exception as exc:
        table.add_row("Estado", f"[yellow]Atenção ao validar API: {exc}[/yellow]")

    console.print(table)


@auth_app.command(name="refresh")
def auth_refresh() -> None:
    """Renova manualmente a sessão utilizando o refresh token."""
    store = CredentialStore()
    auth = AuthService(credential_store=store)
    try:
        tokens = auth.refresh()
        console.print("[bold green]Sessão renovada com sucesso![/bold green]")
        console.print(f"Novo access token emitido com validade de {tokens.expires_in}s.")
    except Exception as exc:
        console.print(f"[bold red]Falha ao renovar sessão:[/bold red] {exc}")
        sys.exit(1)


@auth_app.command(name="logout")
def auth_logout() -> None:
    """Encerra a sessão local e revoga tokens no Keycloak."""
    store = CredentialStore()
    auth = AuthService(credential_store=store)
    auth.logout()
    console.print("[bold green]Sessão encerrada com sucesso.[/bold green] Credenciais removidas do keyring.")


@usuario_app.command(name="obter")
def usuario_obter() -> None:
    """Consulta os dados cadastrais do usuário autenticado."""
    client = DesarqClient()
    try:
        me = client.get_me()
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar usuário:[/bold red] {exc}")
        sys.exit(1)

    table = Table(title="Dados do Usuário - DESARQ", border_style="green")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")

    table.add_row("Nome", me.nome)
    table.add_row("Login", me.login)
    table.add_row("CPF / CNPJ", me.cpf_mascarado())
    table.add_row("E-mail", me.email or "-")
    table.add_row("Origem", me.origemAutenticacao or "-")
    table.add_row("Administrador?", "Sim" if me.admin else "Não")
    if isinstance(me.permissoes, dict):
        perm_str = (
            ", ".join(f"{k} ({len(v) if isinstance(v, list) else v})" for k, v in me.permissoes.items()) or "Padrão"
        )
    elif isinstance(me.permissoes, list):
        perm_str = ", ".join(me.permissoes) if me.permissoes else "Padrão"
    else:
        perm_str = "Padrão"
    table.add_row("Permissões", perm_str)

    console.print(table)


@solicitacoes_app.command(name="listar")
def solicitacoes_listar(
    page: Annotated[int, Parameter(help="Número da página (inicia em 0).")] = 0,
    size: Annotated[int, Parameter(help="Quantidade de itens por página.")] = 10,
    processo: Annotated[str, Parameter(help="Filtrar por número do processo.")] = "",
    modo: Annotated[str, Parameter(help="Filtrar por modo ('Físico' ou 'Digitalizado').")] = "",
    andamento: Annotated[str, Parameter(help="Filtrar por andamento ('pendentes' ou 'solicitados').")] = "",
) -> None:
    """Lista solicitações de desarquivamento cadastradas no sistema."""
    client = DesarqClient()
    try:
        busca = client.buscar_solicitacoes(
            page=page,
            size=size,
            processo=processo,
            modo=modo,
            andamento=andamento,
        )
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar solicitações:[/bold red] {exc}")
        sys.exit(1)

    if not busca.content:
        console.print("[yellow]Nenhuma solicitação encontrada para os filtros informados.[/yellow]")
        return

    table = Table(title=f"Solicitações de Desarquivamento (Página {page})", border_style="blue")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Processo", style="bold", no_wrap=True)
    table.add_column("Estado")
    table.add_column("Tipo")
    table.add_column("Criado em")
    table.add_column("Caixa")

    for item in busca.content:
        data_str = item.dataCriacao or item.dataUltimoEstado or "-"
        if len(data_str) >= 10 and "T" in data_str:
            data_str = data_str.split("T")[0]
        caixa_str = item.caixa.strip() if item.caixa else "-"
        table.add_row(
            str(item.id),
            item.numeroProcesso,
            item.estado or "-",
            item.tipoDesarquivamento or "-",
            data_str,
            caixa_str,
        )

    console.print(table)
    total_elem = busca.page.get("totalElements", len(busca.content))
    total_pages = busca.page.get("totalPages", 1)
    console.print(f"[dim]Página {page + 1} de {total_pages} (Total de itens: {total_elem})[/dim]")


if __name__ == "__main__":
    app()
