# /// script
# requires-python = ">=3.11"
# dependencies = ["pikepdf[pdfa]>=10.17"]
# ///
"""PDF/A promotion with `pikepdf.pdfa`, without Ghostscript.

`pikepdf.pdfa.prepare` repairs structure and metadata in memory (output
intent, XMP identification, annotation flags, interpolation, JavaScript)
and never touches page content; the file is then written with
`resolve_save_kwargs` and checked again by `validate_written`.

`prepare` writes `xmp:CreateDate`/`xmp:ModifyDate` only from the Info
dictionary. Google Docs exports have no /CreationDate, and the PDPJ portal
refuses a PDF without `xmp:createdate`, so missing dates are filled first.

`validate_written` sorts findings into `violation` and `unsupported`. Only
the `pikepdf:schema-*` unsupported findings (dictionary keys its schemas do
not list, e.g. /Type in /MarkInfo, /SE in an outline item; all three in a
Google Docs export) are harmless enough to accept. Any other unsupported
finding is an ISO 19005 rule pikepdf could not decide (a non-embedded font
is reported this way) or an internal error, and blocks acceptance like a
violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pikepdf
import pikepdf.pdfa

SUPPORTED_PARTS = (1, 2, 3)
#: Unsupported findings that only mean "key not in pikepdf's schema".
SCHEMA_ONLY_PREFIX = "pikepdf:schema-"


@dataclass(frozen=True)
class PikepdfResult:
    """What the pikepdf promotion did and what `validate_written` found."""

    violations: tuple[str, ...]
    #: Unsupported findings that pikepdf could not decide; they block like violations.
    undecided: tuple[str, ...]
    #: Schema-only unsupported findings, reported as "não verificados pelo pikepdf".
    unchecked: tuple[str, ...]
    changes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def blocking(self) -> tuple[str, ...]:
        """Findings that keep the output from being accepted."""
        return self.violations + self.undecided


def pdf_date(when: datetime) -> str:
    """Format a datetime as a PDF date; a naive value is taken as local time."""
    if when.tzinfo is None:
        when = when.astimezone()
    base = when.strftime("D:%Y%m%d%H%M%S")
    offset = when.utcoffset()
    if not offset:
        return f"{base}Z"
    minutes = int(offset.total_seconds()) // 60
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"{base}{sign}{hours:02d}'{rest:02d}'"


def _has(pdf: pikepdf.Pdf, key: str) -> bool:
    info = pdf.trailer.get("/Info")
    return isinstance(info, pikepdf.Dictionary) and bool(str(info.get(key, "")).strip())


def fill_missing_dates(pdf: pikepdf.Pdf, when: datetime | None = None) -> list[str]:
    """Set /CreationDate (and /ModDate) when absent, so the XMP gets xmp:CreateDate."""
    filled = []
    stamp = pdf_date(when or datetime.now().astimezone())
    for key in ("/CreationDate", "/ModDate"):
        if not _has(pdf, key):
            pdf.docinfo[key] = pikepdf.String(stamp)
            filled.append(key[1:])
    if not filled:
        return []
    return [f"Set missing {' and '.join(filled)} to {stamp} (PDPJ requires xmp:CreateDate)"]


def convert_pikepdf(
    input_path: Path,
    output_path: Path,
    *,
    part: int,
    creation_date: datetime | None = None,
) -> PikepdfResult:
    """Promote `input_path` to PDF/A-<part>b at `output_path` and validate the written file."""
    if part not in SUPPORTED_PARTS:
        raise ValueError(f"Unsupported PDF/A part: {part}")
    flavour = f"{part}b"
    save_kwargs = pikepdf.pdfa.resolve_save_kwargs(flavour)
    with pikepdf.open(input_path) as pdf:
        changes = fill_missing_dates(pdf, creation_date)
        prepared = pikepdf.pdfa.prepare(pdf, flavour)
        changes.extend(prepared.describe())
        pdf.save(output_path, **save_kwargs)
    report = pikepdf.pdfa.validate_written(output_path, flavour, save_kwargs)
    unsupported = list(report.unsupported)
    return PikepdfResult(
        violations=tuple(str(finding) for finding in report.violations),
        undecided=tuple(str(f) for f in unsupported if not f.rule.startswith(SCHEMA_ONLY_PREFIX)),
        unchecked=tuple(str(f) for f in unsupported if f.rule.startswith(SCHEMA_ONLY_PREFIX)),
        changes=tuple(changes),
    )
