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
"""Interface de linha de comando para o Jus.br e PDPJ/CNJ."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from auth import AuthService  # noqa: E402
from client import JusBrClient  # noqa: E402
from credentials import CredentialStore  # noqa: E402
from errors import (  # noqa: E402
    JusBrAuthError,
    RefreshTokenRevokedError,
    SessionExpiredError,
)

console = Console()

app = App(
    name="jusbr",
    help="CLI para operações no portal Jus.br e Plataforma Digital do Poder Judiciário (PDPJ-Br).",
    result_action=lambda x: x,
)
auth_app = App(name="auth", help="Gerenciamento de autenticação e sessão no CNJ.", result_action=lambda x: x)
usuario_app = App(name="usuario", help="Consultas sobre o perfil na PDPJ.", result_action=lambda x: x)
comunicacoes_app = App(
    name="comunicacoes", help="Consulta de intimações e comunicações oficiais.", result_action=lambda x: x
)
processo_app = App(name="processo", help="Consulta processual experimental (desabilitada).", result_action=lambda x: x)
peticionamento_app = App(
    name="peticionamento", help="Peticionamento experimental (desabilitado).", result_action=lambda x: x
)

app.command(auth_app)
app.command(usuario_app)
app.command(comunicacoes_app)
app.command(processo_app)
app.command(peticionamento_app)


def _obter_clipboard_texto() -> str:
    """Tenta ler texto da área de transferência do Windows de forma silenciosa e rápida."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def _aguardar_callback_url(expected_state: str, prompt_text: str) -> str:
    """Aguarda o usuário colar no terminal ou captura automaticamente do clipboard com Ctrl+C."""
    result_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    initial_clipboard = _obter_clipboard_texto()

    def _monitor_clipboard() -> None:
        last_seen = initial_clipboard
        while not stop_event.is_set():
            time.sleep(0.3)
            if stop_event.is_set():
                break
            text = _obter_clipboard_texto()
            if text and text != last_seen:
                last_seen = text
                # Caso 1: Token JWT direto ou payload do bookmarklet contendo eyJ
                if "eyJ" in text:
                    console.print(
                        "\n[bold green]✓ Token / Sessão PDPJ detectada na Área de Transferência![/bold green]"
                    )
                    result_queue.put(text)
                    return
                # Caso 2: URL de callback com state esperado
                if expected_state and expected_state in text and "code=" in text:
                    console.print(
                        "\n[bold green]✓ URL de callback com código detectada na Área de Transferência![/bold green]"
                    )
                    result_queue.put(text)
                    return

    t_clip = threading.Thread(target=_monitor_clipboard, daemon=True)
    t_clip.start()

    def _read_input() -> None:
        try:
            val = console.input(prompt_text).strip()
            if val:
                result_queue.put(val)
        except Exception:
            pass

    t_input = threading.Thread(target=_read_input, daemon=True)
    t_input.start()

    try:
        captured = result_queue.get()
        stop_event.set()
        return captured
    except Exception as exc:
        stop_event.set()
        raise JusBrAuthError(f"Falha ao obter URL de callback: {exc}") from exc


@auth_app.command(name="login")
def auth_login(
    force: Annotated[bool, Parameter(help="Forçar novo login mesmo se já houver sessão ativa.")] = False,
    callback_url: Annotated[str, Parameter(help="URL final redirecionada ou token JWT direto.")] = "",
    no_browser: Annotated[bool, Parameter(help="Não abrir o navegador automaticamente.")] = False,
    bookmarklet: Annotated[bool, Parameter(help="Abrir a página do Bookmarklet para captura via favoritos.")] = False,
) -> None:
    """Inicia autenticação com a conta gov.br / certificado digital no Keycloak da PDPJ/CNJ."""
    store = CredentialStore()
    auth = AuthService(credential_store=store)
    client = JusBrClient(auth_service=auth)

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
    bookmarklet_file = _root / "bookmarklet.html"
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

    store = CredentialStore()
    auth = AuthService(credential_store=store)
    client = JusBrClient(auth_service=auth)

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
) -> None:
    """Salva diretamente no keyring uma sessão ativa obtida via bookmarklet ou DevTools."""
    store = CredentialStore()
    auth = AuthService(credential_store=store)
    client = JusBrClient(auth_service=auth)

    raw_input = token
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
    store = CredentialStore()
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

    auth = AuthService(credential_store=store)
    client = JusBrClient(auth_service=auth)
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
    store = CredentialStore()
    auth = AuthService(credential_store=store)
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
    store = CredentialStore()
    auth = AuthService(credential_store=store)
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


@usuario_app.command(name="obter")
def usuario_obter() -> None:
    """Consulta dados cadastrais do usuário na PDPJ/Jus.br."""
    client = JusBrClient()
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
    client = JusBrClient()
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


@processo_app.command(name="consultar")
def processo_consultar(
    numero: Annotated[str, Parameter(help="Número único do processo (CNJ).")] = "",
) -> None:
    """Consulta experimental, ainda sem contrato de endpoint confirmado."""
    if not numero:
        console.print("[bold red]Informe o número do processo.[/bold red]")
        sys.exit(1)

    client = JusBrClient()
    try:
        proc = client.consultar_processo(numero)
    except Exception as exc:
        console.print(f"[bold red]Erro ao consultar processo:[/bold red] {exc}")
        sys.exit(1)

    table = Table(title=f"Processo Judicial: {proc.numero}", border_style="magenta")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")

    table.add_row("Número", proc.numero)
    table.add_row("Tribunal", proc.tribunal or "-")
    table.add_row("Órgão Julgador", proc.orgao_julgador or "-")
    table.add_row("Classe Processual", proc.classe or "-")

    console.print(table)


@peticionamento_app.command(name="intercorrente")
def peticionamento_intercorrente(
    processo: Annotated[str, Parameter(help="Número do processo de destino.")] = "",
    tribunal: Annotated[str, Parameter(help="Sigla do tribunal (ex: TJRO).")] = "",
    tipo: Annotated[str, Parameter(help="Tipo da petição (ex: Manifestação, Petição).")] = "Manifestação",
    arquivo: Annotated[str, Parameter(help="Caminho do arquivo PDF da petição.")] = "",
    descricao: Annotated[str, Parameter(help="Descrição sucinta da petição.")] = "",
) -> None:
    """Informa que o envio por API segue experimental e não transmite a peça."""
    console.print(
        "[bold yellow]Peticionamento por API não habilitado.[/bold yellow] "
        "O endpoint utilizado anteriormente não está confirmado em contrato oficial; "
        "nenhum arquivo foi lido ou transmitido e nenhum protocolo foi gerado. "
        "Use o Portal de Serviços oficial do CNJ."
    )
    sys.exit(2)


if __name__ == "__main__":
    app()
