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
"""Comandos `jusbr peticao`: petição intercorrente pelo Portal de Serviços da PDPJ.

Escrita segue o padrão do `todos`: sem `--confirmar` o comando só mostra o plano.
O rascunho pode ser apagado (`peticao excluir`); o protocolo não se desfaz.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cli_comum as comum
from cli_comum import console
from cyclopts import App, Parameter
from errors import JusBrError
from peticao_montagem import (
    MontagemError,
    conferir_arquivo,
    conferir_tribunal,
    escolher_tipo,
    montar_documento,
    montar_rascunho,
    tipos_do_tribunal,
)
from rich.table import Table

peticao_app = App(name="peticao", help="Petição intercorrente pelo Portal de Serviços.", result_action=lambda x: x)


def _falhar(contexto: str, exc: Exception) -> None:
    console.print(f"[bold red]{contexto}:[/bold red] {exc}")
    sys.exit(1)


@peticao_app.command(name="tribunal")
def peticao_tribunal(sigla: Annotated[str, Parameter(help="Sigla do tribunal (ex.: TJRO, TRF1).")]) -> None:
    """Diz se o tribunal recebe petição intercorrente pelo Portal, e com que arquivos."""
    portal = comum.PortalClient()
    try:
        cadastro = next((t for t in portal.tribunais() if t.get("siglaTribunal") == sigla.upper()), None)
        detalhe = portal.tribunal(cadastro["jtrTribunal"]) if cadastro else None
        conferir_tribunal(detalhe, sigla.upper())
    except (JusBrError, MontagemError) as exc:
        _falhar("Sem peticionamento pelo Portal", exc)
    arquivos = ", ".join(f"{t['extensao']} até {t['tamanhoMaximoMB']} MB" for t in detalhe["tiposArquivosAceitos"])
    console.print(f"[green]{sigla.upper()} (JTR {detalhe['codigoJTR']}) recebe petição intercorrente.[/green]")
    console.print(f"Arquivos: {arquivos}")


@peticao_app.command(name="tipos")
def peticao_tipos(
    sigla: Annotated[str, Parameter(help="Sigla do tribunal.")],
    busca: Annotated[str, Parameter(help="Trecho da descrição para filtrar.")] = "",
) -> None:
    """Tipos de documento do tribunal (TPU do CNJ ou lista própria); o `id` é o que `--tipo` aceita."""
    portal = comum.PortalClient()
    try:
        cadastro = next((t for t in portal.tribunais() if t.get("siglaTribunal") == sigla.upper()), None)
        if not cadastro:
            raise MontagemError(f"{sigla.upper()} não está no cadastro de tribunais do Portal.")
        tipos, _ = tipos_do_tribunal(portal, cadastro["jtrTribunal"], sigla.upper())
    except (JusBrError, MontagemError) as exc:
        _falhar("Erro ao listar tipos", exc)
    tabela = Table(title=f"Tipos de documento — {sigla.upper()}")
    tabela.add_column("Id", justify="right")
    tabela.add_column("Código TPU")
    tabela.add_column("Descrição")
    for tipo in tipos:
        if busca.casefold() in str(tipo.get("descricao", "")).casefold():
            tabela.add_row(str(tipo["id"]), str(tipo.get("codigo", "")), str(tipo.get("descricao", "")))
    console.print(tabela)


@peticao_app.command(name="listar")
def peticao_listar() -> None:
    """Suas petições no Portal, com situação e recibo."""
    try:
        peticoes = comum.PortalClient().peticoes()
    except JusBrError as exc:
        _falhar("Erro ao listar petições", exc)
    tabela = Table(title="Minhas petições")
    for coluna in ("Id", "Tribunal", "Processo", "Situação", "Criada", "Recibo CNJ"):
        tabela.add_column(coluna)
    for p in peticoes:
        tabela.add_row(
            str(p["id"]),
            str(p.get("siglaTribunal", "")),
            str(p.get("numeroProcesso", "")),
            (p.get("situacao") or {}).get("descricao", "-"),
            str(p.get("dataCriacao", "")),
            str(p.get("numeroReciboCnj") or "-"),
        )
    console.print(tabela)


@peticao_app.command(name="ver")
def peticao_ver(id_peticao: Annotated[int, Parameter(help="Id da petição.")]) -> None:
    """A petição completa em JSON, como o Portal guarda."""
    try:
        print(json.dumps(comum.PortalClient().peticao(id_peticao), ensure_ascii=False, indent=1))
    except JusBrError as exc:
        _falhar("Erro ao ler a petição", exc)


@peticao_app.command(name="conferir")
def peticao_conferir(protocolo: Annotated[str, Parameter(help="Número do recibo CNJ.")]) -> None:
    """Situação de um protocolo no Portal (juntada, aguardando, recusada)."""
    try:
        console.print_json(data=comum.PortalClient().consultar_protocolo(protocolo))
    except JusBrError as exc:
        _falhar("Erro ao conferir o protocolo", exc)


@peticao_app.command(name="rascunho")
def peticao_rascunho(
    cnj: Annotated[str, Parameter(help="Processo de destino (formato CNJ).")],
    principal: Annotated[Path, Parameter(help="PDF da peça principal (PDF/A).")],
    tipo: Annotated[str, Parameter(help="Id ou descrição exata do tipo da peça principal (`peticao tipos`).")],
    anexo: Annotated[list[Path] | None, Parameter(help="PDF anexo; repita a opção para vários, na ordem.")] = None,
    tipo_anexo: Annotated[str, Parameter(help="Id ou descrição do tipo dos anexos.")] = "",
    confirmar: Annotated[bool, Parameter(help="Cria de fato o rascunho e envia os arquivos.")] = False,
) -> None:
    """Cria o rascunho da petição intercorrente com a peça e os anexos; não protocola."""
    portal = comum.PortalClient()
    anexos = anexo or []
    try:
        proc = portal.processo(cnj)
        sigla = proc["siglaTribunal"]
        jtr = proc["tramitacaoAtual"]["tribunal"]["jtr"]
        cadastro = portal.tribunal(jtr)
        conferir_tribunal(cadastro, sigla)
        tipos, origem = tipos_do_tribunal(portal, jtr, sigla)
        tipo_principal = escolher_tipo(tipos, tipo)
        tipo_dos_anexos = escolher_tipo(tipos, tipo_anexo) if anexos else None
        arquivos = [(principal, conferir_arquivo(cadastro, principal))]
        arquivos += [(a, conferir_arquivo(cadastro, a)) for a in anexos]
        rascunho = montar_rascunho(proc, tipo_principal["id"])
    except (JusBrError, MontagemError, KeyError, OSError) as exc:
        _falhar("Rascunho não montado", exc)

    console.print(f"[bold]Plano[/bold]: {sigla} {cnj} — {rascunho['nomeOrgaoJulgadorCorporativo']}")
    for ordem, (caminho, conteudo) in enumerate(arquivos):
        rotulo = tipo_principal if ordem == 0 else tipo_dos_anexos
        console.print(f"  {ordem}. {caminho.name} ({len(conteudo):,} bytes) como {rotulo['descricao']}")
    if not confirmar:
        console.print("[yellow]Nada foi criado. Repita com --confirmar para criar o rascunho.[/yellow]")
        return

    # Como o formulário do Portal: cada arquivo vai antes ao repositório do processo, e a petição
    # só referencia os documentos (`{"documento": ...}`), sem conteúdo no corpo.
    documentos = [
        montar_documento(
            caminho, conteudo, tipo_principal if ordem == 0 else tipo_dos_anexos, origem, ordem, ordem == 0
        )
        for ordem, (caminho, conteudo) in enumerate(arquivos)
    ]
    try:
        for documento, (_, conteudo) in zip(documentos, arquivos, strict=True):
            portal.enviar_documento(rascunho["numeroProcesso"], documento, conteudo)
    except JusBrError as exc:
        _falhar("Arquivo não enviado; nenhum rascunho foi criado", exc)
    rascunho["peticaoDocumentos"] = [{"documento": d} for d in documentos]
    try:
        id_peticao = portal.criar_rascunho(rascunho)["id"]
    except (JusBrError, KeyError) as exc:
        _falhar("Falha ao criar o rascunho (confira em `peticao listar` e apague o que sobrou)", exc)
    console.print(f"[green]Rascunho {id_peticao} criado.[/green] Confira no Portal em Minhas petições.")
    console.print(f"Para protocolar: jusbr peticao protocolar {id_peticao} --confirmar")


@peticao_app.command(name="protocolar")
def peticao_protocolar(
    id_peticao: Annotated[int, Parameter(help="Id do rascunho.")],
    confirmar: Annotated[bool, Parameter(help="Protocola de fato. Não se desfaz.")] = False,
) -> None:
    """Protocola um rascunho já conferido. Sem --confirmar, só mostra o que seria enviado."""
    portal = comum.PortalClient()
    try:
        pet = portal.peticao(id_peticao)
    except JusBrError as exc:
        _falhar("Erro ao ler o rascunho", exc)
    docs = [(d.get("documento") or d) for d in pet.get("peticaoDocumentos", [])]
    console.print(f"[bold]Protocolo[/bold]: {pet.get('siglaTribunal')} {pet.get('numeroProcesso')}")
    for d in docs:
        console.print(f"  {d.get('ordem')}. {d.get('nome')} — {d.get('nomeTipoDocumento')}")
    if not docs:
        _falhar("Rascunho sem documentos", ValueError("nada a protocolar"))
    if not confirmar:
        console.print("[yellow]Nada foi protocolado. Repita com --confirmar para protocolar.[/yellow]")
        return
    try:
        protocolo = portal.protocolar(pet)
    except JusBrError as exc:
        _falhar("Protocolo não confirmado (confira em `peticao listar` antes de repetir)", exc)
    console.print(
        f"[green]Protocolado.[/green] Recibo CNJ {protocolo.get('numeroReciboCnj')}, {protocolo.get('status')}"
    )


@peticao_app.command(name="excluir")
def peticao_excluir(
    id_peticao: Annotated[int, Parameter(help="Id do rascunho.")],
    confirmar: Annotated[bool, Parameter(help="Apaga de fato o rascunho.")] = False,
) -> None:
    """Apaga um rascunho que não será protocolado."""
    if not confirmar:
        console.print(f"[yellow]Nada foi apagado. Repita com --confirmar para apagar o rascunho {id_peticao}.[/yellow]")
        return
    try:
        comum.PortalClient().excluir(id_peticao)
    except JusBrError as exc:
        _falhar("Erro ao apagar o rascunho", exc)
    console.print(f"Rascunho {id_peticao} apagado.")
