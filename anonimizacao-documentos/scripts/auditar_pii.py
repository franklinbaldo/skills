#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "litellm",
#     "cyclopts>=3.0",
# ]
# ///
"""Optional external LLM audit for already-anonymized Markdown files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import cyclopts
from cyclopts import Parameter

STRICT_HUNTER_PROMPT = """Você audita resíduos de PII em documentos anonimizados.
Procure nomes e iniciais de pessoas, identificadores, contatos, endereços, datas
pessoais, saúde e segredos. Não trate órgãos, municípios ou marcadores no
formato _TIPO_N_ como PII por si sós. Retorne somente JSON no formato
{"achados": [{"trecho": "...", "tipo": "...", "motivo": "..."}]}.
Se não encontrar candidatos, retorne {"achados": []}. Não declare conformidade."""

FORENSIC_LGPD_PROMPT = """Você revisa risco de reidentificação em documentos
anonimizados. Procure combinações de atributos, metadados, rodapés, URLs e
inconsistências de marcadores que possam identificar uma pessoa. Retorne somente
JSON no formato {"achados": [{"trecho": "...", "tipo": "...", "motivo": "..."}]}.
Se não encontrar candidatos, retorne {"achados": []}. Não declare risco zero."""


class ExternalAuditError(RuntimeError):
    """Raised when external audit inputs or outputs are unsafe."""


def call_auditor(text: str, prompt: str, model: str) -> list[dict[str, Any]]:
    """Call one external auditor and validate its JSON envelope."""
    try:
        from litellm import completion
    except ImportError as error:
        raise ExternalAuditError(
            "Install litellm before running the optional external audit."
        ) from error

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content
    if not content:
        raise ExternalAuditError("The external auditor returned empty content.")
    payload = json.loads(content)
    findings = payload.get("achados")
    if not isinstance(findings, list):
        raise ExternalAuditError("The external auditor returned an invalid schema.")
    return [finding for finding in findings if isinstance(finding, dict)]


def input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.anon.md"))
    raise FileNotFoundError(path)


app = cyclopts.App(name="auditar-pii", help=__doc__)


@app.default
def main(
    *,
    input_path: Annotated[Path, Parameter(name=["--input"])],
    output: Path,
    model: str = "gemini/gemini-2.5-flash",
    allow_external_transfer: bool = False,
) -> int:
    """Send anonymized text to two optional external LLM auditors.

    Parameters
    ----------
    input_path
        A *.anon.md file or a directory containing them.
    output
        JSON report path.
    model
        litellm model identifier.
    allow_external_transfer
        Confirm authorization to send document text to the model provider.
    """
    if not allow_external_transfer:
        raise ExternalAuditError(
            "External transfer not authorized; pass --allow-external-transfer only "
            "after confirming the document may be sent to the provider."
        )

    files = input_files(input_path)
    if not files:
        raise ExternalAuditError("No *.anon.md files found.")

    report: dict[str, Any] = {
        "model": model,
        "warning": "LLM findings are candidates, not proof of anonymization.",
        "documents": [],
    }
    for path in files:
        text = path.read_text(encoding="utf-8")
        findings: list[dict[str, Any]] = []
        for role, prompt in (
            ("strict_hunter", STRICT_HUNTER_PROMPT),
            ("forensic_lgpd", FORENSIC_LGPD_PROMPT),
        ):
            for finding in call_auditor(text, prompt, model):
                findings.append({"auditor": role, **finding})
        report["documents"].append(
            {
                "path": str(path),
                "finding_count": len(findings),
                "findings": findings,
            }
        )
        print(f"{path}: {len(findings)} candidate finding(s)")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Sensitive audit report: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(app())
    except (
        ExternalAuditError,
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
