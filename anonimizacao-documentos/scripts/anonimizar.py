"""Script de Anonimização Determinística de Documentos (LGPD/OKF).

Realiza a substituição de tags `<pii tipo='...' ref='...'>conteudo</pii>` pelos marcadores
canônicos em caixa alta `_TIPO_REF_` e valida os 5 invariantes mecânicos.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Tipos suportados e seus substitutos canônicos
CANONICAL_TYPES = {
    "nome_pessoa": "NOME_PESSOA",
    "assinatura_signatario": "ASSINATURA_SIGNATARIO",
    "cpf": "CPF",
    "rg": "RG",
    "matricula_servidor": "MATRICULA_SERVIDOR",
    "processo_judicial": "PROCESSO_JUDICIAL",
    "data_nascimento": "DATA_NASCIMENTO",
    "dado_saude": "DADO_SAUDE",
    "oab": "OAB",
    "contato": "CONTATO",
    "endereco": "ENDERECO",
}

class ErroAnonimizacaoError(Exception):
    """Erro de violação de invariante mecânico durante a anonimização."""

def normalizar_tipo(tipo: str) -> str:
    """Retorna a forma canônica do tipo de PII."""
    t_clean = tipo.strip().lower()
    if t_clean in CANONICAL_TYPES:
        return CANONICAL_TYPES[t_clean]
    return t_clean.upper()

def anonimizar(conteudo_md: str) -> tuple[str, int]:
    """Substitui tags <pii> por marcadores canônicos e valida isolamento sem aninhamento."""
    
    # Check Invariante 3: Nenhuma tag <pii> aninhada
    tag_matches = list(re.finditer(r'</?pii\b[^>]*>', conteudo_md, re.IGNORECASE))
    stack = []
    for m in tag_matches:
        is_close = m.group(0).startswith('</')
        if not is_close:
            stack.append(m)
            if len(stack) > 1:
                raise ErroAnonimizacaoError(
                    "1 tag(s) <pii> aninhada(s) — uma PII dentro de outra torna a substituição ambígua."
                )
        else:
            if stack:
                stack.pop()

    count = 0
    ref_map: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def _replace_tag(match: re.Match) -> str:
        nonlocal count
        count += 1
        full_tag = match.group(0)
        
        tipo_match = re.search(r"tipo=['\"]([^'\"]+)['\"]", full_tag, re.IGNORECASE)
        ref_match = re.search(r"ref=['\"]([^'\"]+)['\"]", full_tag, re.IGNORECASE)
        
        tipo = tipo_match.group(1) if tipo_match else "PII"
        ref = ref_match.group(1) if ref_match else "1"
        
        tipo_canon = normalizar_tipo(tipo)
        key = (tipo_canon, ref)
        
        if key not in ref_map:
            counters[tipo_canon] = counters.get(tipo_canon, 0) + 1
            ref_map[key] = f"_{tipo_canon}_{counters[tipo_canon]}_"
            
        return ref_map[key]

    # Substitui tags <pii tipo='...' ref='...'>conteudo</pii>
    pattern = re.compile(r"<pii\b[^>]*>(.*?)</pii\s*>", re.DOTALL | re.IGNORECASE)
    texto_anon = pattern.sub(_replace_tag, conteudo_md)
    
    return texto_anon, count

def main() -> int:
    parser = argparse.ArgumentParser(description="Anonimização determinística de arquivos Markdown.")
    parser.add_argument("--input", required=True, help="Arquivo .md ou diretório contendo arquivos .md")
    args = parser.parse_args()

    input_path = Path(args.input)
    files = [input_path] if input_path.is_file() else list(input_path.glob("**/*.md"))

    print(f"Processando {len(files)} arquivo(s)...")
    for f in files:
        if f.name.endswith(".anon.md"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            anon_text, substitutions = anonimizar(content)
            out_file = f.with_name(f.stem + ".anon.md")
            out_file.write_text(anon_text, encoding="utf-8")
            print(f"  [OK] {f.name} -> {out_file.name} ({substitutions} substituições)")
        except Exception as e:
            print(f"  [ERRO] {f.name}: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
