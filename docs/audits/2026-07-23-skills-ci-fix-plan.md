---
okf:
  type: audit
  subtype: fix-plan
  version: "1.0"
  status: draft
  scope: "Plano de correção dos erros de Lint (Ruff) na CI do repositório de Skills"
  authors:
    - claude
  created: 2026-07-23
---

# Plano de Correção — Skills Lint CI 2026-07-23

Com a introdução da verificação do `ruff check .` na CI do repositório `skills`, foram identificados **48 erros de linting** nos scripts em Python do repositório. Este documento detalha os problemas encontrados e o plano para corrigi-los de forma limpa.

---

## 📌 Resumo dos Erros por Categoria

### 1. `I001` — Ordenação/Formatação de Imports
* **Onde:** Vários arquivos (`process_pdf.py`, `convert_pdf.py`, `compress.py`, `axiom_graph.py`, `lean_docgen_md.py`, `juris.py`).
* **Causa:** Imports fora de ordem alfabética ou sem agrupamento correto (padrão vs. terceiros).
* **Solução:** Executar a ordenação automática com `ruff check --select I --fix .`.

### 2. `RUF046` — Cast Desnecessário para Inteiro
* **Onde:** `pdf-compression/scripts/process_pdf.py` (linhas 106 e 107).
* **Problema:** `int(math.ceil(...))` é redundante pois `math.ceil` no Python 3 já retorna um inteiro.
* **Solução:** Mudar para `math.ceil(...)`.

### 3. `BLE001` — Captura Cega de Exceções (`except Exception`)
* **Onde:** `pdf-compression/scripts/process_pdf.py` (linhas 179, 220, 347, 383) e `pdf-to-markdown/scripts/convert_pdf.py` (linhas 153, 168).
* **Problema:** Uso de `except Exception:` silencia erros inesperados sem especificidade.
* **Solução:** Alterar para exceções específicas (ex: `OSError`, `fitz.FileDataError`, `subprocess.CalledProcessError`) ou adicionar logs detalhados antes de lidar com o erro.

### 4. `FURB122` — Escrita de Arquivo Sequencial em Loop (`f.write`)
* **Onde:** `pdf-to-markdown/scripts/convert_pdf.py` (linha 120).
* **Problema:** Uso de `f.write` repetitivo dentro de um loop.
* **Solução:** Substituir por `f.writelines(...)` usando uma expressão geradora.

### 5. `F541` — f-strings sem Placeholders
* **Onde:** `pdf-to-markdown/scripts/convert_pdf.py` (linha 123) e `scripts/lean_docgen_md.py` (linha 108).
* **Problema:** Uso do prefixo `f` em strings literais estáticas.
* **Solução:** Remover o prefixo `f`.

### 6. `PLW1510` — `subprocess.run` sem check explícito
* **Onde:** `pdf-to-markdown/scripts/convert_pdf.py` (linha 141).
* **Problema:** Chamar `subprocess.run` sem definir o comportamento de verificação de erros (`check`).
* **Solução:** Adicionar `check=False` explicitamente ou tratar a exceção adequadamente com `check=True`.

---

## 🛠️ Plano de Ação

1. **Auto-fix (25 erros fáceis):**
   Executar o ruff com auto-correção para resolver automaticamente importações e f-strings vazias:
   ```bash
   uv run --with ruff ruff check --fix .
   ```
2. **Correção manual (23 erros de lógica):**
   * Corrigir os blocos `except Exception` identificando as exceções reais das dependências (`fitz`, `PIL`, `subprocess`).
   * Substituir `int(math.ceil(...))` por `math.ceil(...)`.
   * Corrigir a chamada de `subprocess.run` adicionando `check=False` ou `check=True`.
3. **Validação:**
   Rodar localmente e garantir retorno limpo:
   ```bash
   uv run --with ruff ruff check .
   ```
