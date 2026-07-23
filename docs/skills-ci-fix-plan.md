# Plano de Correção do CI/Lint do Repositório de Skills

Este documento apresenta o diagnóstico e o plano de ação para corrigir as falhas de CI (especialmente linting do Ruff) no repositório `skills`.

## Diagnóstico
Atualmente, a execução do linter `ruff check .` detecta **48 erros** em arquivos Python do repositório, organizados principalmente nos seguintes scripts:
1. `pdf-compression/scripts/process_pdf.py` (importações desordenadas, conversão desnecessária de `int`, capturas genéricas `Exception`)
2. `pdf-to-markdown/scripts/convert_pdf.py` (importações desordenadas, `f-strings` sem placeholders, `subprocess.run` sem check explícito, loops com `.write`)
3. `scripts/axiom_graph.py` (importações desordenadas)
4. `scripts/lean_docgen_md.py` (importações desordenadas, `f-strings` sem placeholders)

## Plano de Ação

1. **Correção automática do Ruff**:
   Executar `ruff check . --fix` e `ruff format .` usando `uv` sem carregar o projeto pai:
   ```bash
   uv run --no-project --with ruff ruff check . --fix
   uv run --no-project --with ruff ruff format .
   ```

2. **Correções manuais remanescentes**:
   Tratar manualmente os avisos do tipo `BLE001` (blind except blocks) e `PLW1510` (subprocess run checks) que não são corrigidos automaticamente pelo linter.

3. **Validação**:
   Garantir localmente que `ruff check .` e `ruff format --check .` retornem sucesso (zero saídas de erro).
