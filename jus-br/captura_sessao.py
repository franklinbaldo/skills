# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "keyring>=25.0.0",
#     "pydantic>=2.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""Captura da URL de callback ou do token da PDPJ pelo terminal ou pela área de transferência."""

from __future__ import annotations

import os
import queue
import signal
import subprocess
import threading
import time

from cli_comum import console
from errors import JusBrAuthError


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

    def _sig_handler(sig: int, frame: object) -> None:
        stop_event.set()
        console.print("\n[yellow]Operação cancelada pelo usuário (Ctrl+C).[/yellow]")
        os._exit(130)

    try:
        orig_sig = signal.signal(signal.SIGINT, _sig_handler)
    except Exception:
        orig_sig = None

    try:
        while not stop_event.is_set():
            try:
                captured = result_queue.get(timeout=0.25)
                stop_event.set()
                return captured
            except queue.Empty:
                continue
    except (KeyboardInterrupt, SystemExit):
        stop_event.set()
        console.print("\n[yellow]Operação cancelada pelo usuário (Ctrl+C).[/yellow]")
        os._exit(130)
    except Exception as exc:
        stop_event.set()
        raise JusBrAuthError(f"Falha ao obter URL de callback: {exc}") from exc
    finally:
        if orig_sig is not None:
            try:
                signal.signal(signal.SIGINT, orig_sig)
            except Exception:
                pass
    return ""
