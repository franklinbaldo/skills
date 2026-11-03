# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlglot>=27,<29"]
# ///
"""Strict SQL to Metabase MBQL 5 compiler: the converter behind `sql_to_mbql.py`.

Pink carries its own copy (`pink.sql_to_mbql`); keep both verified by the
same conformance tests when either evolves."""

from mbql_core.base import ConversionError, TableRef
from mbql_core.converter import Converter, convert_sql
from mbql_core.rewrite import CaseSensitiveEquality
from mbql_core.rewrite_window import UniqueRowPerGroup

__all__ = [
    "CaseSensitiveEquality",
    "ConversionError",
    "Converter",
    "TableRef",
    "UniqueRowPerGroup",
    "convert_sql",
]
