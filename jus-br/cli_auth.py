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
"""Comandos `jusbr auth`: login, favorito (bookmarklet), importação, status, renovação e saída."""

from __future__ import annotations

import sys
import time
import webbrowser
from typing import Annotated

import cli_comum as comum
from captura_sessao import _aguardar_callback_url
from cli_comum import RAIZ, console
from cyclopts import App, Parameter
from errors import JusBrAuthError, RefreshTokenRevokedError, SessionExpiredError
from rich.panel import Panel
from rich.table import Table

auth_app = App(name="auth", help="Gerenciamento de autenticação e sessão no CNJ.", result_action=lambda x: x)


@auth_app.command(name="login")
def auth_login(
    force: Annotated[bool, Parameter(help="Forçar novo login mesmo se já houver sessão ativa.")] = False,
    callback_url: Annotated[str, Parameter(help="URL final redirecionada ou token JWT direto.")] = "",
    no_browser: Annotated[bool, Parameter(help="Não abrir o navegador automaticamente.")] = False,
    bookmarklet: Annotated[bool, Parameter(help="Abrir a página do Bookmarklet para captura via favoritos.")] = False,
) -> None:
    """Inicia autenticação com a conta gov.br / certificado digital no Keycloak da PDPJ/CNJ."""
    store = comum.CredentialStore()
    auth = comum.AuthService(credential_store=store)
    client = comum.JusBrClient(auth_service=auth)

    if not force:
        try:
            auth.ensure_valid_tokens()
            perfil = client.obter_perfil()
            console.print("[green]Sessão ativa e válida no keyring da PDPJ/CNJ.[/green]")
            console.print(
                f"Usuário: [bold]{perfil.name or perfil.preferred_username}[/bold] (CPF: {perfil.cpf_mascarado()})"
            )
            return
        except (SessionExpiredError, RefreshTokenRevokedError):
            pass
        except Exception as exc:
            console.print(f"[yellow]Sessão anterior da PDPJ não pôde ser reaproveitada: {exc}[/yellow]")

    if bookmarklet:
        auth_bookmarklet()

    auth_url, verifier, state = auth.start_login()

    console.print(
        Panel(
            "[bold cyan]Autenticação Jus.br (PDPJ/CNJ)[/bold cyan]\n\n"
            "• [bold green]OPÇÃO A (Recomendada - Bookmarklet):[/bold green]\n"
            "  Acesse [bold green]https://portaldeservicos.pdpj.jus.br/consulta[/bold green] e clique no favorito.\n"
            "  (Para instalar o favorito, execute [yellow]jusbr auth bookmarklet[/yellow]).\n\n"
            "• [bold blue]OPÇÃO B (Navegador SSO CNJ):[/bold blue]\n"
            "  O navegador abrirá a autenticação Gov.br / Certificado no Keycloak.\n"
            "  Ao redirecionar para [cyan]www.jus.br[/cyan], dê [bold]Ctrl+C[/bold] na URL.\n\n"
            "✓ [dim]A CLI detectará automaticamente tanto o Token do Bookmarklet quanto a URL de callback![/dim]",
            title="Login Único Jus.br",
            border_style="cyan",
        )
    )

    if not no_browser and not bookmarklet:
        webbrowser.open(auth_url)

    target_input = callback_url
    if not target_input:
        try:
            target_input = _aguardar_callback_url(
                expected_state=state,
                prompt_text="\n[bold yellow]Cole a URL redirecionada ou o Token aqui (ou acione o favorito/Ctrl+C): [/bold yellow]",
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            sys.exit(130)

    while True:
        try:
            if (
                "eyJ" in target_input
                or target_input.strip().lower().startswith("bearer ")
                or (target_input.startswith("{") and "eyJ" in target_input)
            ):
                tokens = auth.import_session(target_input)
            else:
                tokens = auth.complete_login(target_input, code_verifier=verifier, state=state)

            perfil = client.obter_perfil()
            console.print("[bold green]✓ Autenticação concluída com sucesso![/bold green]")
            console.print(
                f"Bem-vindo(a), [bold]{perfil.name or perfil.preferred_username}[/bold] (CPF: {perfil.cpf_mascarado()})"
            )
            if perfil.oab:
                console.print(f"Inscrição OAB: [bold cyan]{perfil.oab}[/bold cyan]")
            console.print(
                f"[dim]Sessão armazenada com segurança no Windows Credential Manager. Validade: {tokens.expires_in}s[/dim]"
            )
            break
        except JusBrAuthError as exc:
            console.print(f"[yellow]⚠️ {exc}[/yellow]")
            try:
                target_input = _aguardar_callback_url(
                    expected_state=state,
                    prompt_text="\n[bold yellow]Cole novamente o token ou URL aqui (Ctrl+C para sair): [/bold yellow]",
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
                sys.exit(130)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            sys.exit(130)
        except Exception as exc:
            console.print(f"[bold red]Erro inesperado:[/bold red] {exc}")
            sys.exit(1)


@auth_app.command(name="bookmarklet")
def auth_bookmarklet(
    no_wait: Annotated[bool, Parameter(help="Apenas abrir a página do bookmarklet sem aguardar a captura.")] = False,
) -> None:
    """Abre no navegador a página do Bookmarklet e aguarda a captura instantânea de sessão."""
    bookmarklet_file = RAIZ / "bookmarklet.html"
    if not bookmarklet_file.exists():
        console.print("[bold red]Arquivo bookmarklet.html não encontrado.[/bold red]")
        sys.exit(1)

    url = bookmarklet_file.resolve().as_uri()
    console.print(
        Panel(
            "[bold cyan]Conector Bookmarklet Jus.br / PDPJ[/bold cyan]\n\n"
            "1. Arraste o botão [bold]⭐ ⚖️ Conectar Sessão PDPJ[/bold] da página para seus [bold]Favoritos[/bold].\n"
            "2. Certifique-se de estar na página oficial correta com login Gov.br / Certificado ativo:\n"
            "   👉 [bold green]https://portaldeservicos.pdpj.jus.br/consulta[/bold green]\n"
            "3. Na aba da PDPJ, clique no favorito criado: a sessão será copiada instantaneamente.\n\n"
            "⏳ [bold yellow]Aguardando você acionar o favorito na aba da PDPJ...[/bold yellow]\n"
            "[dim](A detecção no terminal é automática. Pressione Ctrl+C para cancelar)[/dim]",
            title="Conector de Sessão PDPJ",
            border_style="cyan",
        )
    )
    webbrowser.open(url)

    if no_wait:
        return

    store = comum.CredentialStore()
    auth = comum.AuthService(credential_store=store)
    client = comum.JusBrClient(auth_service=auth)

    try:
        raw_input = _aguardar_callback_url(
            expected_state="",
            prompt_text="\n[bold yellow]Cole o token ou aguarde a detecção automática do favorito: [/bold yellow]",
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
        sys.exit(130)

    while True:
        try:
            tokens = auth.import_session(raw_input)
            perfil = client.obter_perfil()
            console.print("\n[bold green]✓ Sessão importada e salva com sucesso no Keyring![/bold green]")
            console.print(
                f"Usuário: [bold]{perfil.name or perfil.preferred_username}[/bold] (CPF: {perfil.cpf_mascarado()})"
            )
            if perfil.oab:
                console.print(f"Inscrição OAB: [bold cyan]{perfil.oab}[/bold cyan]")
            console.print(
                f"[dim]Token Bearer armazenado com segurança no Windows Credential Manager. Validade: {tokens.expires_in}s[/dim]"
            )
            break
        except JusBrAuthError as exc:
            console.print(f"[yellow]⚠️ {exc}[/yellow]")
            try:
                raw_input = _aguardar_callback_url(
                    expected_state="",
                    prompt_text="\n[bold yellow]Cole o token ou acione o favorito novamente (Ctrl+C para sair): [/bold yellow]",
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
                sys.exit(130)


@auth_app.command(name="set-token")
def auth_set_token(
    token: Annotated[str, Parameter(help="Token Bearer (JWT) ou JSON exportado do bookmarklet.")] = "",
    access: Annotated[str, Parameter(help="Access Token (JWT) opcional.")] = "",
    refresh: Annotated[str, Parameter(help="Refresh Token (JWT) opcional.")] = "",
) -> None:
    """Salva diretamente no keyring uma sessão ativa obtida via bookmarklet ou DevTools."""
    store = comum.CredentialStore()
    auth = comum.AuthService(credential_store=store)
    client = comum.JusBrClient(auth_service=auth)

    raw_input = access or token
    refresh_token = refresh or None
    if not raw_input:
        try:
            raw_input = _aguardar_callback_url(
                expected_state="",
                prompt_text="\n[bold yellow]Cole o token Bearer (JWT) ou export do bookmarklet aqui: [/bold yellow]",
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            sys.exit(130)

    while True:
        try:
            if refresh_token:
                tokens = auth.import_session(raw_input, refresh_token=refresh_token)
            else:
                tokens = auth.import_session(raw_input)
            perfil = client.obter_perfil()
            console.print("\n[bold green]✓ Sessão importada e salva com sucesso no Keyring![/bold green]")
            console.print(
                f"Usuário: [bold]{perfil.name or perfil.preferred_username}[/bold] (CPF: {perfil.cpf_mascarado()})"
            )
            if perfil.oab:
                console.print(f"Inscrição OAB: [bold cyan]{perfil.oab}[/bold cyan]")
            console.print(
                f"[dim]Token Bearer armazenado com segurança no Windows Credential Manager. Validade: {tokens.expires_in}s[/dim]"
            )
            break
        except JusBrAuthError as exc:
            console.print(f"[yellow]⚠️ {exc}[/yellow]")
            try:
                raw_input = _aguardar_callback_url(
                    expected_state="",
                    prompt_text="\n[bold yellow]Cole o token novamente (Ctrl+C para sair): [/bold yellow]",
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
                sys.exit(130)


@auth_app.command(name="status")
def auth_status() -> None:
    """Verifica a situação da sessão atual da PDPJ no keyring."""
    store = comum.CredentialStore()
    tokens = store.load_tokens()

    if not tokens:
        console.print("[yellow]Status: Não autenticado.[/yellow] (Nenhuma sessão encontrada no keyring)")
        return

    table = Table(title="Status da Sessão Jus.br / PDPJ", border_style="cyan")
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

    auth = comum.AuthService(credential_store=store)
    client = comum.JusBrClient(auth_service=auth)
    try:
        perfil = client.obter_perfil()
        table.add_row("Estado", "[bold green]Sessão Ativa e Operacional[/bold green]")
        user_desc = f"{perfil.name or perfil.preferred_username} ({perfil.cpf_mascarado()})"
        if perfil.oab:
            user_desc += f" [cyan]OAB {perfil.oab}[/cyan]"
        table.add_row("Usuário", user_desc)
        if perfil.email:
            table.add_row("E-mail", perfil.email)
    except Exception as exc:
        table.add_row("Estado", f"[yellow]Atenção ao validar perfil: {exc}[/yellow]")

    console.print(table)


@auth_app.command(name="refresh")
def auth_refresh() -> None:
    """Renova manualmente a sessão utilizando o refresh token."""
    store = comum.CredentialStore()
    auth = comum.AuthService(credential_store=store)
    try:
        tokens = auth.refresh()
        console.print("[bold green]Sessão da PDPJ renovada com sucesso![/bold green]")
        console.print(f"Novo access token emitido com validade de {tokens.expires_in}s.")
    except Exception as exc:
        console.print(f"[bold red]Falha ao renovar sessão:[/bold red] {exc}")
        sys.exit(1)


@auth_app.command(name="logout")
def auth_logout() -> None:
    """Encerra a sessão local e revoga tokens no Keycloak do CNJ."""
    store = comum.CredentialStore()
    auth = comum.AuthService(credential_store=store)
    remoto_ok = auth.logout()
    if remoto_ok:
        console.print(
            "[bold green]Sessão encerrada com sucesso.[/bold green] "
            "Tokens revogados no Keycloak do CNJ e removidos do keyring local."
        )
    else:
        console.print(
            "[yellow]Sessão local removida do keyring.[/yellow] "
            "[dim](Aviso: Revogação remota no Keycloak não confirmada ou sem conexão)[/dim]"
        )
