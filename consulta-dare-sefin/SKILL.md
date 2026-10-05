---
name: consulta-dare-sefin
description: Consulta a situação e extrai comprovantes de pagamento oficiais de DARE (Documento de Arrecadação de Receitas Estaduais) no portal da Secretaria de Estado de Finanças de Rondônia (SEFIN/RO). Use quando precisar verificar se guias DARE foram pagas, auditar parcelamentos, obter datas e números de autenticação para manifestações e cumprimentos de sentença, ou baixar comprovantes em lote.
compatibility: Requer Python 3.11+ e uv. Opera via script PEP 723 independente com httpx, cyclopts, beautifulsoup4 e rich.
---

# Consulta de DARE — SEFIN/RO

Guia operacional e automação para verificação de quitação e extração de comprovantes oficiais de DARE no portal da Secretaria de Estado de Finanças de Rondônia (`dare.sefin.ro.gov.br`).

## 1. Como Funciona o Portal da SEFIN

O portal da SEFIN disponibiliza a verificação pública de DARE em:
`https://dare.sefin.ro.gov.br/situacao-dare`

### O Endpoint de Impressão Direta (Sem Captcha e Sem Autenticação)

A aplicação do portal da SEFIN expõe a seguinte rota pública de impressão de comprovante:
```http
GET /situacao-dare/imprimir?numero_guia_cbarras=<CODIGO_BARRAS>&numero_parcela=00
Host: dare.sefin.ro.gov.br
```

Esse endpoint é **totalmente público**:
* **Não exige captcha:** Não passa pelo fluxo de desafio com imagem do formulário inicial;
* **Não exige autenticação nem cookies:** Pode ser consumido diretamente via GET puro por qualquer cliente HTTP (`curl`, `httpx`, navegador);
* Retorna imediatamente o documento HTML oficial do comprovante de pagamento contendo:
  * **Situação:** Identificação de "COMPROVANTE DE PAGAMENTO DE DARE" (*pago*);
  * **Data do Pagamento:** Data exata da liquidação bancária/Pix (`dd/mm/aaaa`);
  * **Valor Total:** Montante arrecadado (principal, juros, multa e acréscimos);
  * **Dados do Contribuinte:** Nome e CPF/CNPJ;
  * **Código da Receita:** Ex.: `7257` (*Ressarcimento ao Erário — IPERON*);
  * **Autenticação SEFIN:** Número do documento gerado pelo sistema fazendário.

---

## 2. Origem Canônica e Execução Direta via URL

A fonte canônica da skill é:
```text
https://github.com/franklinbaldo/skills/blob/main/consulta-dare-sefin/SKILL.md
```

A URL canônica do script executável é:
```text
https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py
```

**Prefira rodar o script diretamente da sua URL HTTPS no GitHub com `uv run`**. Não é necessário clonar o repositório de skills nem instalar nada previamente. O script declara suas próprias dependências via PEP 723, de modo que o `uv` cria o ambiente isolado e instala `httpx`, `cyclopts`, `beautifulsoup4` e `rich` automaticamente na primeira execução.

> [!TIP]
> Se esta skill foi lida de um commit específico (ref pinada) em vez da `main`, substitua `main` na URL do script raw pelo mesmo SHA do commit antes de executar, garantindo alinhamento de versão.

---

## 3. Uso do Script

### A. Consulta Direta de Guia Individual (Zero Configuração)

Basta passar o código de barras (48 dígitos) diretamente na URL do GitHub:

```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py \
  --codigo "856600000124046500227247305300138966452150725722"
```

### B. Consulta de Lote via JSON

Prepare um arquivo `guias.json` no formato:
```json
[
  {
    "parcela": "83",
    "vencimento": "31/10/2024",
    "codigo": "856600000124046500227247305300138966452150725722"
  },
  {
    "parcela": "84",
    "vencimento": "29/11/2024",
    "codigo": "856800000122046500227247334580138967452150725722"
  }
]
```

Execute a conferência em lote salvando o CSV consolidado e os comprovantes HTML:
```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py \
  --arquivo guias.json \
  --output-dir comprovantes/ \
  --csv resultado_dares.csv
```

### C. Consulta de Lote via CSV

Também aceita arquivo `.csv` delimitado por ponto e vírgula contendo no mínimo a coluna `codigo` (e opcionalmente `parcela` e `vencimento`):
```csv
parcela;vencimento;codigo
83;31/10/2024;856600000124046500227247305300138966452150725722
84;29/11/2024;856800000122046500227247334580138967452150725722
```

Execute:
```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py \
  --arquivo guias.csv \
  --output-dir comprovantes/ \
  --csv resultado_dares.csv
```

### D. Execução Local (quando o repositório estiver clonado)

Caso esteja dentro do repositório de skills ou de um projeto que possua a pasta `.claude/skills/`:
```bash
uv run --script consulta-dare-sefin/scripts/consultar_dare.py --codigo "<codigo>"
```

---

## 4. Estrutura dos Arquivos de Saída e Dados Extraídos

O script realiza a extração exaustiva de **todos os blocos e campos** da certidão de pagamento da SEFIN:

### Campos Estruturados Extraídos (CSV e JSON)

* **Identificação:** `parcela`, `vencimento`, `codigo`, `situacao` (*pago / nao_encontrado / erro*);
* **Detalhamento Financeiro:** `valor_principal`, `valor_multa`, `valor_juros`, `outros_acrescimos`, `valor_total`, `data_pagamento`;
* **Dados do Contribuinte:** `contribuinte` (nome completo), `cpf_cnpj` (extraído *verbatim* como retornado pela SEFIN, sem mascaramento introduzido pelo script), `endereco`, `municipio`, `cep`, `uf`, `telefone`;
* **Dados da Arrecadação & Autenticação:** `numero_documento` (autenticação oficial SEFIN), `codigo_receita` (ex.: 7257), `numero_parcela`, `numero_processo`, `tipo_dare`, `sequencial`, `mes_ano_referencia`, `complemento`, `unidade_gestora`, `gestao`, `nome_servidor`, `cpf_servidor`, `restituicao`, `valor_restituido`;
* **Metadados de Rastreabilidade:** `codigo_barras_formatado` (linha digitável com espaçamento oficial), `versao_sefin` (versão e build do sistema fazendário), `arquivo_comprovante` (caminho local do HTML), `observacao`.

> [!NOTE]
> **Preservação Fidedigna dos Dados (Sem Mascaramento Próprio):** O script não aplica nenhuma função de mascaramento, truncamento ou ofuscação. Todos os campos (CPF/CNPJ, nome, endereço, valores) são capturados exatamente (*verbatim*) como constam na resposta do servidor da SEFIN/RO. Se a SEFIN exibir caracteres de ocultação (ex.: `***.896.452-**`), isso reflete a política de privacidade pública do próprio portal fazendário na emissão daquela via.

### Formatos de Exportação

1. **Painel Visual no Terminal (Guia Única):**
   Renderiza caixas e tabelas formatadas com `rich` divididas em *Contribuinte*, *Arrecadação & Autenticação* e *Detalhamento Financeiro*.

2. **Relatório Consolidado CSV (`--csv resultado.csv`):**
   Gera planilha delimitada por ponto e vírgula com **todas as 34 colunas** descritas acima.

3. **Objeto JSON Completo (`--json resultado.json`):**
   Gera JSON estruturado completo contendo a lista de todos os registros com tipagem textual estrita.

4. **Comprovantes Oficiais HTML (`comprovantes/comprovante_*.html`):**
   Arquivo HTML standalone com layout oficial do Governo de Rondônia / SEFIN, pronto para impressão ou conversão em PDF.

---

## 5. Boas Práticas e Regras Processuais

* **Ônus probatório:** O ônus de provar pagamento em execução ou cumprimento de sentença é sempre do executado (art. 373, II, e art. 525 do CPC). A conferência pela Fazenda Pública serve para tutela do erário, evitar excesso de execução e permitir eventual homologação de abatimento de valores incontroversos.
* **Depósitos judiciais não são DAREs:** Se o executado juntar comprovantes com conta judicial vinculada ao TJRO/Caixa Econômica Federal (Operação 040), a conferência deve ser feita nos extratos da conta judicial nos autos do PJe, não no portal da SEFIN. Para esses valores, o pedido processual cabível é de expedição de alvará/transferência eletrônica ao ente público credor.
* **Guia faltante:** Se houver intervalo na numeração das parcelas sem a respectiva guia ou comprovante juntado, registre a parcela como *não comprovada* para fins de liquidação de sentença.
