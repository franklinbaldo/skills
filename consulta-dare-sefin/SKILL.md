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

### O Endpoint de Impressão Direta

Ao realizar uma consulta pública com sucesso, o portal gera o comprovante oficial através da rota de impressão:
```http
GET /situacao-dare/imprimir?numero_guia_cbarras=<CODIGO_BARRAS>&numero_parcela=00
Host: dare.sefin.ro.gov.br
```

Quando invocado com um cookie de sessão válido (`_dare_session`), esse endpoint **não exige resolução de captcha** e retorna imediatamente a página HTML do comprovante oficial, contendo:
* **Situação:** Confirmação explícita de "COMPROVANTE DE PAGAMENTO DE DARE" (*pago*);
* **Data do Pagamento:** Data exata da liquidação bancária/Pix (`dd/mm/aaaa`);
* **Valor Total:** Montante arrecadado (valor principal, juros, multa e acréscimos);
* **Dados do Contribuinte:** Nome e CPF/CNPJ;
* **Código da Receita:** Ex.: `7257` (*Ressarcimento ao Erário — IPERON*);
* **Autenticação:** Número do documento emitido pela SEFIN.

---

## 2. Como Obter a Sessão (`_dare_session`)

Para consultas automatizadas diretas (individuais ou em lote sem captcha):

1. Abra qualquer navegador e acerte a URL: `https://dare.sefin.ro.gov.br/situacao-dare`
2. Abra as Ferramentas do Desenvolvedor (**F12** ou Ctrl+Shift+I);
3. Na aba **Rede / Network** (ou em **Application / Armazenamento -> Cookies -> dare.sefin.ro.gov.br**), localize o cookie nomeado `_dare_session`;
4. Copie o valor completo do cookie (string iniciada tipicamente por `eQds...` ou caracteres alfanuméricos com percent-encoding);
5. Utilize-o via parâmetro `--session` ou exporte como variável de ambiente:
   ```powershell
   $env:SEFIN_DARE_SESSION = "<valor_do_cookie>"
   ```

---

## 3. Origem Canônica e Execução Direta via URL

A fonte canônica da skill é:
```text
https://github.com/franklinbaldo/skills/blob/main/consulta-dare-sefin/SKILL.md
```

A URL canônica do script executável é:
```text
https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py
```

**Prefira rodar o script diretamente da sua URL HTTPS no GitHub com `uv run`**. Não é necessário clonar o repositório de skills para utilizá-lo. O script declara suas próprias dependências via PEP 723, de modo que o `uv` cria o ambiente isolado e instala `httpx`, `cyclopts`, `beautifulsoup4` e `rich` automaticamente na primeira execução.

> [!TIP]
> Se esta skill foi lida de um commit específico (ref pinada) em vez da `main`, substitua `main` na URL do script raw pelo mesmo SHA do commit antes de executar, garantindo alinhamento de versão.

---

## 4. Uso do Script

### A. Consulta Direta de Guia Individual (via URL)

```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py \
  --codigo "856600000124046500227247305300138966452150725722" \
  --session "<valor_do_cookie>"
```

### B. Consulta de Lote via JSON (via URL)

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

Execute a conferência em lote salvando o CSV consolidado e os HTMLs:
```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/consulta-dare-sefin/scripts/consultar_dare.py \
  --arquivo guias.json \
  --session "<valor_do_cookie>" \
  --output-dir comprovantes/ \
  --csv resultado_dares.csv
```

### C. Execução Local (quando o repositório estiver clonado)

Caso esteja dentro do repositório de skills ou de um projeto que possua a pasta `.claude/skills/`:
```bash
uv run --script consulta-dare-sefin/scripts/consultar_dare.py --codigo "<codigo>" --session "<cookie>"
```

### D. Consulta de Lote via CSV

Também aceita arquivo `.csv` delimitado por ponto e vírgula contendo no mínimo a coluna `codigo` (e opcionalmente `parcela` e `vencimento`):
```csv
parcela;vencimento;codigo
83;31/10/2024;856600000124046500227247305300138966452150725722
84;29/11/2024;856800000122046500227247334580138967452150725722
```

---

## 4. Estrutura dos Arquivos de Saída

1. **Relatório CSV (`resultado_dares.csv`):**
   * Colunas: `parcela`, `vencimento`, `codigo`, `situacao`, `data_pagamento`, `valor`, `contribuinte`, `cpf_cnpj`, `codigo_receita`, `numero_documento`, `arquivo_comprovante`, `observacao`.
   * Permite integração direta com tabelas de petições jurídicas em Markdown.

2. **Comprovantes Oficiais HTML (`comprovantes/comprovante_*.html`):**
   * Arquivo HTML standalone com layout oficial do Governo de Rondônia / SEFIN.
   * Contém formatação de impressão pronta (`@media print`).
   * Pode ser aberto diretamente no navegador ou convertido em PDF para juntada aos autos do PJe.

---

## 5. Boas Práticas e Regras Processuais

* **Ônus probatório:** O ônus de provar pagamento em execução ou cumprimento de sentença é sempre do executado (art. 373, II, e art. 525 do CPC). A conferência pela Fazenda Pública serve para tutela do erário, evitar excesso de execução e permitir eventual homologação de abatimento de valores incontroversos.
* **Depósitos judiciais não são DAREs:** Se o executado juntar comprovantes com conta judicial vinculada ao TJRO/Caixa Econômica Federal (Operação 040), a conferência deve ser feita nos extratos da conta judicial nos autos do PJe, não no portal da SEFIN. Para esses valores, o pedido processual cabível é de expedição de alvará/transferência eletrônica ao ente público credor.
* **Guia faltante:** Se houver intervalo na numeração das parcelas sem a respectiva guia ou comprovante juntado, registre a parcela como *não comprovada* para fins de liquidação de sentença.
