#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4>=4.12.0",
#     "cyclopts>=3.0",
#     "httpx>=0.27.0",
#     "rich>=13.0.0",
# ]
# ///
"""Consulta e extração de comprovantes de pagamento de DARE na SEFIN/RO.

Permite consultar guias individuais ou em lote no portal da SEFIN/RO,
extraindo todos os campos da certidão de arrecadação: contribuinte, endereço,
detalhamento financeiro, código de receita, número do documento e autenticação.
O endpoint de impressão oficial é público e dispensa autenticação ou captcha.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Annotated

import httpx
from bs4 import BeautifulSoup
from cyclopts import App, Parameter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = App(
    name="consultar-dare",
    help=__doc__,
)
console = Console()

BASE_URL = "https://dare.sefin.ro.gov.br"
IMPRIMIR_URL = f"{BASE_URL}/situacao-dare/imprimir"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class ResultadoDare:
    # Identificação da Consulta
    parcela: str
    vencimento: str
    codigo: str
    situacao: str

    # Dados Financeiros / Valores
    valor_total: str
    valor_principal: str
    valor_multa: str
    valor_juros: str
    outros_acrescimos: str
    data_pagamento: str

    # Dados do Contribuinte
    contribuinte: str
    cpf_cnpj: str
    telefone: str
    endereco: str
    municipio: str
    cep: str
    uf: str

    # Dados da Arrecadação
    numero_documento: str
    numero_processo: str
    numero_parcela: str
    codigo_receita: str
    tipo_dare: str
    sequencial: str
    mes_ano_referencia: str
    complemento: str
    unidade_gestora: str
    gestao: str
    nome_servidor: str
    cpf_servidor: str
    restituicao: str
    valor_restituido: str

    # Código de barras e metadados
    codigo_barras_formatado: str
    versao_sefin: str
    arquivo_comprovante: str
    observacao: str


def _extrair_campo_regex(padrao: str, texto: str, default: str = "") -> str:
    m = re.search(padrao, texto, re.I)
    return m.group(1).strip() if m else default


def extrair_dados_comprovante(
    html: str,
    codigo: str,
    parcela: str = "",
    vencimento: str = "",
    caminho_salvo: str = "",
) -> ResultadoDare:
    """Extrai exaustivamente todos os campos estruturados do HTML do comprovante da SEFIN."""
    soup = BeautifulSoup(html, "html.parser")

    texto_geral = soup.get_text()
    titulo_el = soup.find(class_=re.compile(r"legacy-title", re.I))

    situacao = "pago" if (titulo_el or "COMPROVANTE DE PAGAMENTO DE DARE" in texto_geral) else "nao_encontrado"

    # 1. Dados do Contribuinte
    contribuinte = _extrair_campo_regex(r"Nome\s*/\s*Contribuinte:</b>\s*([^<]+)", html)
    cpf_cnpj = _extrair_campo_regex(r"Inscricao Estadual\s*/\s*CPF\s*/\s*CNPJ:</b>\s*([^<]+)", html)
    telefone = _extrair_campo_regex(r"DDD\s*/\s*TELEFONE:</b>\s*([^<]*)", html)
    endereco = _extrair_campo_regex(r"Endereço:</b>\s*([^<]+)", html)
    municipio = _extrair_campo_regex(r"Municipio/Distrito:</b>\s*([^<]+)", html)
    cep = _extrair_campo_regex(r"CEP:</b>\s*([^<]+)", html)
    uf = _extrair_campo_regex(r"UF:</b>\s*([^<]+)", html)

    # 2. Dados da Arrecadação
    numero_processo = _extrair_campo_regex(r"Nº\s*Processo:</b>\s*<span>([^<]*)</span>", html)
    numero_doc = _extrair_campo_regex(r"Nº\s*do\s*Documento:</b>\s*<span>([^<]*)</span>", html)
    numero_parcela = _extrair_campo_regex(r"Nº\s*da\s*Parcela:</b>\s*<span>([^<]*)</span>", html)
    complemento = _extrair_campo_regex(r"Complemento:</b>\s*<span>([^<]*)</span>", html)
    mes_ano_ref = _extrair_campo_regex(r"Mes\s*/\s*Ano\s*referência:</b>\s*<span>([^<]*)</span>", html)
    nome_servidor = _extrair_campo_regex(r"Nome\s*do\s*Servidor:</b>\s*<span>([^<]*)</span>", html)
    cpf_servidor = _extrair_campo_regex(r"CPF\s*do\s*Servidor:</b>\s*<span>([^<]*)</span>", html)
    tipo_dare = _extrair_campo_regex(r"Tipo\s*de\s*Dare:</b>\s*<span>([^<]*)</span>", html)
    sequencial = _extrair_campo_regex(r"Sequencial:</b>\s*<span>([^<]*)</span>", html)
    codigo_receita = _extrair_campo_regex(r"Cod\.\s*Receita:</b>\s*<span>([^<]*)</span>", html)
    data_pagamento = _extrair_campo_regex(r"Data\s*Pagamento:</b>\s*<span>([^<]*)</span>", html)
    unidade_gestora = _extrair_campo_regex(r"Unidade\s*Gestora:</b>\s*<span>([^<]*)</span>", html)
    gestao = _extrair_campo_regex(r"Gestão:</b>\s*<span>([^<]*)</span>", html)
    restituicao = _extrair_campo_regex(r"Restituição:</b>\s*<span>([^<]*)</span>", html)
    valor_restituido = _extrair_campo_regex(r"Valor\s*Restituído:</b>\s*<span>([^<]*)</span>", html)

    # 3. Valores da Arrecadação
    valor_principal = _extrair_campo_regex(r"Valor\s*Principal</b>\s*<span[^>]*>\s*([^<]+)</span>", html)
    valor_multa = _extrair_campo_regex(r"Valor\s*da\s*Multa</b>\s*<span[^>]*>\s*([^<]+)</span>", html)
    valor_juros = _extrair_campo_regex(r"Valor\s*dos\s*Juros</b>\s*<span[^>]*>\s*([^<]+)</span>", html)
    outros_acrescimos = _extrair_campo_regex(r"Outros\s*Acréscimos</b>\s*<span[^>]*>\s*([^<]+)</span>", html)
    valor_total = _extrair_campo_regex(r"Valor\s*Total</b>\s*<span[^>]*>\s*([^<]+)</span>", html)

    # 4. Código de barras formatado e versão
    codigo_barras_formatado = _extrair_campo_regex(r'<div class="legacy-barcode">([^<]+)</div>', html)
    versao_sefin = _extrair_campo_regex(r"Versão\s*([^<\n]+)", html)

    obs = f"Doc: {numero_doc}" if numero_doc else ("Quitado" if situacao == "pago" else "")

    return ResultadoDare(
        parcela=parcela,
        vencimento=vencimento,
        codigo=codigo,
        situacao=situacao,
        valor_total=valor_total,
        valor_principal=valor_principal,
        valor_multa=valor_multa,
        valor_juros=valor_juros,
        outros_acrescimos=outros_acrescimos,
        data_pagamento=data_pagamento,
        contribuinte=contribuinte,
        cpf_cnpj=cpf_cnpj,
        telefone=telefone,
        endereco=endereco,
        municipio=municipio,
        cep=cep,
        uf=uf,
        numero_documento=numero_doc,
        numero_processo=numero_processo,
        numero_parcela=numero_parcela,
        codigo_receita=codigo_receita,
        tipo_dare=tipo_dare,
        sequencial=sequencial,
        mes_ano_referencia=mes_ano_ref,
        complemento=complemento,
        unidade_gestora=unidade_gestora,
        gestao=gestao,
        nome_servidor=nome_servidor,
        cpf_servidor=cpf_servidor,
        restituicao=restituicao,
        valor_restituido=valor_restituido,
        codigo_barras_formatado=codigo_barras_formatado,
        versao_sefin=versao_sefin,
        arquivo_comprovante=caminho_salvo,
        observacao=obs,
    )


def _resultado_erro(parcela: str, vencimento: str, codigo: str, motivo: str) -> ResultadoDare:
    """Resultado de guia não verificada: só a identificação e o motivo, o resto vazio."""
    vazios = {f.name: "" for f in fields(ResultadoDare)}
    vazios.update(parcela=parcela, vencimento=vencimento, codigo=codigo, situacao="erro", observacao=motivo)
    return ResultadoDare(**vazios)


def consultar_guia(
    client: httpx.Client,
    codigo: str,
    parcela: str = "00",
    vencimento: str = "",
    pasta_destino: Path | None = None,
) -> ResultadoDare:
    """Efetua requisição ao endpoint de impressão da SEFIN."""
    params = {
        "numero_guia_cbarras": codigo.strip(),
        "numero_parcela": "00",
    }

    resp = client.get(IMPRIMIR_URL, params=params)
    resp.raise_for_status()

    html = resp.text
    caminho_salvo = ""

    if pasta_destino:
        pasta_destino.mkdir(parents=True, exist_ok=True)
        # O código da guia entra sempre no nome: na consulta individual a parcela
        # é sempre "00", e o nome só pela parcela fazia uma guia sobrescrever a outra.
        sufixo = f"_p{parcela}" if parcela and parcela != "00" else ""
        nome_arquivo = f"comprovante_{codigo.strip()}{sufixo}.html"
        arquivo = pasta_destino / nome_arquivo
        arquivo.write_text(html, encoding="utf-8")
        caminho_salvo = str(arquivo.resolve())

    return extrair_dados_comprovante(
        html=html,
        codigo=codigo,
        parcela=parcela,
        vencimento=vencimento,
        caminho_salvo=caminho_salvo,
    )


def exibir_painel_detalhado(res: ResultadoDare) -> None:
    """Renderiza todas as informações extraídas do comprovante em painel formatado."""
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    t_contrib = Table(title="Contribuinte", box=None, padding=(0, 1))
    t_contrib.add_column("Campo", style="bold cyan")
    t_contrib.add_column("Valor")
    t_contrib.add_row("Nome", res.contribuinte or "-")
    t_contrib.add_row("CPF / CNPJ", res.cpf_cnpj or "-")
    t_contrib.add_row("Endereço", res.endereco or "-")
    t_contrib.add_row("Município / UF", f"{res.municipio} / {res.uf}" if res.municipio else "-")
    t_contrib.add_row("CEP", res.cep or "-")
    if res.telefone:
        t_contrib.add_row("Telefone", res.telefone)

    t_arrec = Table(title="Arrecadação & Autenticação", box=None, padding=(0, 1))
    t_arrec.add_column("Campo", style="bold cyan")
    t_arrec.add_column("Valor")
    t_arrec.add_row("Nº Documento", res.numero_documento or "-")
    t_arrec.add_row("Código Receita", res.codigo_receita or "-")
    t_arrec.add_row("Data Pagamento", f"[green]{res.data_pagamento}[/green]" if res.data_pagamento else "-")
    t_arrec.add_row("Nº Parcela", res.numero_parcela or "-")
    t_arrec.add_row("Tipo de DARE", res.tipo_dare or "-")
    t_arrec.add_row("Processo", res.numero_processo or "-")
    t_arrec.add_row("Restituição", f"{res.restituicao} (R$ {res.valor_restituido})")

    grid.add_row(t_contrib, t_arrec)

    t_valores = Table(title="Detalhamento Financeiro (R$)", expand=True)
    t_valores.add_column("Principal", justify="right")
    t_valores.add_column("Multa", justify="right")
    t_valores.add_column("Juros", justify="right")
    t_valores.add_column("Acréscimos", justify="right")
    t_valores.add_column("VALOR TOTAL", justify="right", style="bold green")
    t_valores.add_row(
        res.valor_principal or "0,00",
        res.valor_multa or "0,00",
        res.valor_juros or "0,00",
        res.outros_acrescimos or "0,00",
        res.valor_total or "0,00",
    )

    p_content = Table.grid(expand=True)
    p_content.add_row(grid)
    p_content.add_row("")
    p_content.add_row(t_valores)
    if res.codigo_barras_formatado:
        p_content.add_row("")
        p_content.add_row(f"[dim]Código de Barras:[/dim] [yellow]{res.codigo_barras_formatado}[/yellow]")
    if res.versao_sefin:
        p_content.add_row(f"[dim]Sistema SEFIN:[/dim] {res.versao_sefin}")

    cor = "green" if res.situacao == "pago" else "yellow"
    titulo = f"COMPROVANTE DE PAGAMENTO DE DARE — [{cor}]{res.situacao.upper()}[/{cor}]"
    console.print(Panel(p_content, title=titulo, border_style=cor))


@app.default
def main(
    codigo: Annotated[
        str | None,
        Parameter(
            name=["CODIGO", "--codigo", "-c"],
            help="Código de barras ou linha digitável da guia (48 dígitos). Aceito como argumento posicional ou flag.",
        ),
    ] = None,
    *,
    arquivo: Annotated[
        Path | None,
        Parameter(
            name=["--arquivo", "-a"],
            help="Arquivo JSON ou CSV contendo lote de guias a consultar.",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        Parameter(
            name=["--output-dir", "-o"],
            help=(
                "Diretório onde salvar os HTML de comprovante (com dados pessoais). "
                "Omitido, nada é gravado. Prefira um caminho fora do controle de "
                "versão, como .cache/comprovantes-dare/."
            ),
        ),
    ] = None,
    csv_out: Annotated[
        Path | None,
        Parameter(
            name=["--csv"],
            help="Caminho do arquivo CSV de saída consolidado com todas as colunas.",
        ),
    ] = None,
    json_out: Annotated[
        Path | None,
        Parameter(
            name=["--json"],
            help="Caminho do arquivo JSON de saída consolidado com todos os campos.",
        ),
    ] = None,
    session: Annotated[
        str | None,
        Parameter(
            name=["--session", "-s"],
            help="Valor do cookie _dare_session (opcional; o endpoint da SEFIN é público).",
        ),
    ] = None,
) -> int:
    """Consulta e extrai todos os dados de comprovantes de pagamento de DARE na SEFIN/RO.

    Exemplos:
        consultar_dare <codigo-de-barras-48-digitos>
        consultar_dare --arquivo guias.json --csv resultado_completo.csv --json resultado.json
    """
    dare_session = session or os.environ.get("SEFIN_DARE_SESSION")

    cookies = {}
    if dare_session:
        if dare_session.startswith("_dare_session="):
            dare_session = dare_session.split("=", 1)[1]
        cookies["_dare_session"] = dare_session

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": f"{BASE_URL}/situacao-dare/consultar",
    }

    guias_a_consultar = []

    if codigo:
        guias_a_consultar.append({"codigo": codigo.strip(), "parcela": "00", "vencimento": ""})

    if arquivo:
        if not arquivo.exists():
            console.print(f"[bold red]Erro:[/bold red] Arquivo não encontrado: {arquivo}")
            return 1

        if arquivo.suffix.lower() == ".json":
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            if isinstance(dados, list):
                guias_a_consultar.extend(dados)
            else:
                console.print("[bold red]Erro:[/bold red] O JSON deve conter uma lista de guias.")
                return 1
        elif arquivo.suffix.lower() == ".csv":
            with arquivo.open(mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    guias_a_consultar.append(row)
        else:
            console.print("[bold red]Erro:[/bold red] Formato não suportado. Use .json ou .csv.")
            return 1

    if not guias_a_consultar:
        console.print("[bold red]Erro:[/bold red] Nenhuma guia informada. Passe CODIGO ou use --arquivo.")
        return 1

    console.print(f"[bold cyan]SEFIN DARE[/bold cyan] — Iniciando consulta de {len(guias_a_consultar)} guia(s)...")

    resultados: list[ResultadoDare] = []

    with httpx.Client(cookies=cookies, headers=headers, timeout=20.0, follow_redirects=True) as client:
        for idx, g in enumerate(guias_a_consultar, 1):
            cod = g.get("codigo", "").strip()
            parc = str(g.get("parcela", "")).strip()
            venc = str(g.get("vencimento", "")).strip()

            if not cod:
                # Linha sem código não some do lote: vira erro, e o lote sai com 1.
                console.print(f"[{idx}/{len(guias_a_consultar)}] [red]Linha sem código de barras.[/red]")
                resultados.append(_resultado_erro(parc, venc, "", "linha sem código de barras"))
                continue

            console.print(f"[{idx}/{len(guias_a_consultar)}] Consultando guia {parc or cod[:10]}...", end=" ")

            try:
                res = consultar_guia(
                    client=client,
                    codigo=cod,
                    parcela=parc,
                    vencimento=venc,
                    pasta_destino=output_dir,
                )
                resultados.append(res)

                if res.situacao == "pago":
                    console.print(
                        f"[green]PAGO[/green] em {res.data_pagamento} (R$ {res.valor_total}) [{res.observacao}]"
                    )
                else:
                    console.print(f"[yellow]{res.situacao.upper()}[/yellow]")
            except Exception as e:
                console.print(f"[red]FALHA:[/red] {e}")
                resultados.append(_resultado_erro(parc, venc, cod, str(e)))

            time.sleep(0.3)

    # Exibição
    console.print("")
    if len(resultados) == 1:
        exibir_painel_detalhado(resultados[0])
    else:
        table = Table(title="Resultado da Conferência de DAREs")
        table.add_column("Parcela", justify="center")
        table.add_column("Vencimento", justify="center")
        table.add_column("Situação", justify="center")
        table.add_column("Data Pagto", justify="center")
        table.add_column("Valor Total (R$)", justify="right")
        table.add_column("Contribuinte")
        table.add_column("Documento", justify="center")
        table.add_column("Receita", justify="center")

        for r in resultados:
            sit_color = "green" if r.situacao == "pago" else "yellow"
            table.add_row(
                r.parcela or "-",
                r.vencimento or "-",
                f"[{sit_color}]{r.situacao}[/{sit_color}]",
                r.data_pagamento or "-",
                r.valor_total or "-",
                r.contribuinte or "-",
                r.numero_documento or "-",
                r.codigo_receita or "-",
            )

        console.print(table)

    # Salva CSV com TODAS as colunas
    if csv_out:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        with csv_out.open("w", encoding="utf-8", newline="") as f:
            if resultados:
                fieldnames = list(asdict(resultados[0]).keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()
                for r in resultados:
                    writer.writerow(asdict(r))
        console.print(f"[green]CSV consolidado com todos os campos salvo em:[/green] {csv_out.resolve()}")

    # Salva JSON com todos os dados
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        dados_json = [asdict(r) for r in resultados]
        json_out.write_text(json.dumps(dados_json, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]JSON estruturado completo salvo em:[/green] {json_out.resolve()}")

    # Lote com qualquer guia não verificada (SEFIN fora do ar, timeout, HTTP de erro) não é
    # conferência concluída: sair com zero diria a quem automatiza que foi.
    erros = sum(r.situacao == "erro" for r in resultados)
    if not resultados or erros:
        console.print(f"[red]{erros or 'Nenhuma'} guia(s) não verificada(s).[/red]")
        return 1
    return 0


if __name__ == "__main__":
    app()
