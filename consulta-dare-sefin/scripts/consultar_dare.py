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
extraindo a situação, data de pagamento, valor arrecadado, autenticação e
salvando os comprovantes oficiais. O endpoint é público e dispensa autenticação.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

import httpx
from bs4 import BeautifulSoup
from cyclopts import App, Parameter
from rich.console import Console
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
    parcela: str
    vencimento: str
    codigo: str
    situacao: str
    data_pagamento: str
    valor: str
    contribuinte: str
    cpf_cnpj: str
    codigo_receita: str
    numero_documento: str
    arquivo_comprovante: str
    observacao: str


def extrair_dados_comprovante(
    html: str,
    codigo: str,
    parcela: str = "",
    vencimento: str = "",
    caminho_salvo: str = "",
) -> ResultadoDare:
    """Extrai campos estruturados do HTML do comprovante da SEFIN."""
    soup = BeautifulSoup(html, "html.parser")

    data_pagamento = ""
    valor_total = ""
    contribuinte = ""
    cpf_cnpj = ""
    codigo_receita = ""
    numero_doc = ""
    situacao = "nao_encontrado"
    obs = ""

    # Verifica se há título de comprovante
    titulo = soup.find(class_=re.compile(r"legacy-title", re.I))
    texto_geral = soup.get_text()

    if titulo or "COMPROVANTE DE PAGAMENTO DE DARE" in texto_geral:
        situacao = "pago"

    # Busca em legacy-arrec-row ou divs de chave-valor
    for row in soup.find_all(class_=re.compile(r"legacy-arrec-row|legacy-item", re.I)):
        txt = row.get_text(separator=" ", strip=True)
        if "Data Pagamento:" in txt:
            span = row.find("span")
            if span:
                data_pagamento = span.get_text(strip=True)
        if "Cod. Receita:" in txt or "Código da Receita:" in txt:
            span = row.find("span")
            if span:
                codigo_receita = span.get_text(strip=True)
        if "Nº do Documento:" in txt:
            span = row.find("span")
            if span:
                numero_doc = span.get_text(strip=True)
        if "Nome / Contribuinte:" in txt:
            contribuinte = txt.replace("Nome / Contribuinte:", "").strip()
        if "Inscricao Estadual / CPF / CNPJ:" in txt:
            cpf_cnpj = txt.replace("Inscricao Estadual / CPF / CNPJ:", "").strip()

    # Busca valor total na tabela financeira
    val_total_el = soup.find(string=re.compile(r"Valor Total", re.I))
    if val_total_el:
        parent_td = val_total_el.find_parent("td")
        if parent_td:
            span_val = parent_td.find("span")
            if span_val:
                valor_total = span_val.get_text(strip=True)

    # Fallbacks por regex caso a estrutura varie
    if not data_pagamento:
        m = re.search(r"Data Pagamento:</b>\s*<span>([^<]+)</span>", html, re.I)
        if m:
            data_pagamento = m.group(1).strip()
            situacao = "pago"

    if not valor_total:
        m = re.search(r"Valor Total</b>\s*<span[^>]*>\s*([^<]+)</span>", html, re.I)
        if m:
            valor_total = m.group(1).strip()

    if not numero_doc:
        m = re.search(r"Nº do Documento:</b>\s*<span>([^<]+)</span>", html, re.I)
        if m:
            numero_doc = m.group(1).strip()

    if not contribuinte:
        m = re.search(r"Nome\s*/\s*Contribuinte:</b>\s*([^<]+)</div>", html, re.I)
        if m:
            contribuinte = m.group(1).strip()

    if situacao == "pago" and not obs:
        obs = f"Doc: {numero_doc}" if numero_doc else "Quitado"

    return ResultadoDare(
        parcela=parcela,
        vencimento=vencimento,
        codigo=codigo,
        situacao=situacao,
        data_pagamento=data_pagamento,
        valor=valor_total,
        contribuinte=contribuinte,
        cpf_cnpj=cpf_cnpj,
        codigo_receita=codigo_receita,
        numero_documento=numero_doc,
        arquivo_comprovante=caminho_salvo,
        observacao=obs,
    )


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
        nome_arquivo = f"comprovante_{parcela if parcela else codigo[:12]}.html"
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
        Path,
        Parameter(
            name=["--output-dir", "-o"],
            help="Diretório onde salvar os arquivos HTML de comprovante.",
        ),
    ] = Path("comprovantes_dares"),
    csv_out: Annotated[
        Path | None,
        Parameter(
            name=["--csv"],
            help="Caminho do arquivo CSV de saída consolidado.",
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
    """Consulta comprovantes de pagamento de DARE na SEFIN/RO.

    Exemplos:
        consultar_dare 856600000124046500227247305300138966452150725722
        consultar_dare --codigo 856600000124...
        consultar_dare --arquivo guias.json --csv resultado.csv
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
                    console.print(f"[green]PAGO[/green] em {res.data_pagamento} (R$ {res.valor}) [{res.observacao}]")
                else:
                    console.print(f"[yellow]{res.situacao.upper()}[/yellow]")
            except Exception as e:
                console.print(f"[red]FALHA:[/red] {e}")
                resultados.append(
                    ResultadoDare(
                        parcela=parc,
                        vencimento=venc,
                        codigo=cod,
                        situacao="erro",
                        data_pagamento="",
                        valor="",
                        contribuinte="",
                        cpf_cnpj="",
                        codigo_receita="",
                        numero_documento="",
                        arquivo_comprovante="",
                        observacao=str(e),
                    )
                )

            time.sleep(0.3)

    # Exibe tabela resumo
    table = Table(title="Resultado da Conferência de DAREs")
    table.add_column("Parcela", justify="center")
    table.add_column("Vencimento", justify="center")
    table.add_column("Situação", justify="center")
    table.add_column("Data Pagto", justify="center")
    table.add_column("Valor (R$)", justify="right")
    table.add_column("Documento", justify="center")
    table.add_column("Observação")

    for r in resultados:
        sit_color = "green" if r.situacao == "pago" else "yellow"
        table.add_row(
            r.parcela or "-",
            r.vencimento or "-",
            f"[{sit_color}]{r.situacao}[/{sit_color}]",
            r.data_pagamento or "-",
            r.valor or "-",
            r.numero_documento or "-",
            r.observacao or "-",
        )

    console.print("")
    console.print(table)

    # Salva CSV se solicitado
    if csv_out:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        with csv_out.open("w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "parcela",
                "vencimento",
                "codigo",
                "situacao",
                "data_pagamento",
                "valor",
                "contribuinte",
                "cpf_cnpj",
                "codigo_receita",
                "numero_documento",
                "arquivo_comprovante",
                "observacao",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            for r in resultados:
                writer.writerow(asdict(r))
        console.print(f"[green]CSV consolidado salvo com sucesso em:[/green] {csv_out.resolve()}")

    return 0


if __name__ == "__main__":
    app()
