---
name: anonimizacao-documentos
description: |
  Anonimiza documentos jurídicos e administrativos (do SEI, PJe ou relatórios) segundo o padrão OKF/LGPD
  desenvolvido no projeto. Marca PIIs com a tag `<pii tipo='...' ref='...'>` e as substitui deterministicamente por
  marcadores canônicos (`_NOME_PESSOA_1_`, `_CPF_1_`, `_MATRICULA_SERVIDOR_1_`, `_RG_1_`, `_PROCESSO_JUDICIAL_1_`,
  `_DATA_NASCIMENTO_1_`, `_DADO_SAUDE_1_`), validando 5 invariantes mecânicos e rodando auditoria adversarial com LLM.
---

# Anonimização de Documentos Jurídicos e Administrativos (Padrão LGPD/OKF)

Esta skill codifica o fluxo completo de anonimização e auditoria adversarial de documentos jurídicos, informações técnicas e pareceres administrativos (SEI/PJe) desenvolvido e validado em produção.

---

## 🎯 Quando Usar esta Skill

Dispare esta skill sempre que o usuário pedir:
- "Anonimize estes documentos/pareceres"
- "Higienize o processo X para LGPD/dados abertos"
- "Remova PIIs deste arquivo mantendo o contexto jurídico"
- "Prepare o corpus de documentos para publicação sem dados pessoais"
- "Rode o pipeline de anonimização e validação de invariantes"

---

## 📐 Padrão de Anonimização em Duas Etapas (Two-Pass Architecture)

### 1. Etapa de Marcação (Tagging Pass)
Envolve todas as entidades identificáveis no texto com marcadores semânticos `<pii tipo='...' ref='...'>`:

```xml
O requerimento formulado por <pii tipo='nome_pessoa' ref='1'>JOÃO DA SILVA</pii>, 
portador do CPF <pii tipo='cpf' ref='1'>123.456.789-00</pii> e RG <pii tipo='rg' ref='1'>123456 SSP/RO</pii>...
```

**Tipos de PII Suportados:**
- `nome_pessoa`: Requerentes, falecidos, dependentes, menores (incluindo iniciais `T. D. R.`), advogados, procuradores, auditores e signatários.
- `cpf`: CPFs formatados (`123.456.789-00`), parcialmente mascarados pelo SEI (`***.455.532.**`) ou de 11 dígitos em rodapés (`Criado por 03579099256`).
- `rg`: Números de RG com ou sem órgão emissor (`18052197 SSP/SP`, `268877SSP/RO`).
- `matricula_servidor`: Matrículas funcionais completas (`300017166`) ou parcialmente mascaradas pelo SEI (`******249`).
- `processo_judicial`: Números CNJ de processos judiciais (`7005781-78.2017.8.22.0007`).
- `data_nascimento`: Datas de nascimento ou falecimento completas (`nasceu em 18 de maio de 1959`).
- `dado_saude`: Diagnósticos médicos, CIDs e laudos (`CID10: M500`, `Transtorno do disco cervical`).
- `oab`: Número da OAB de advogados (`OAB n. 1046`).
- `contato` / `endereco`: Endereços particulares de rua/bairro e telefones pessoais.

### 2. Etapa de Substituição Determinística (Replacement Pass)
Substitui as tags pelos marcadores canônicos em caixa alta:
- `<pii tipo='nome_pessoa' ref='1'>JOÃO DA SILVA</pii>` $\rightarrow$ `_NOME_PESSOA_1_`
- `<pii tipo='cpf' ref='1'>123.456.789-00</pii>` $\rightarrow$ `_CPF_1_`
- `<pii tipo='processo_judicial' ref='1'>...</pii>` $\rightarrow$ `_PROCESSO_JUDICIAL_1_`

Os arquivos anonimizados são salvos em paralelo com extensão **`.anon.md`**, garantindo a rastreabilidade e a não-destruição do original.

---

## 🏛️ Fronteira LGPD: O que REMOVER vs O que MANTER

### ❌ REMOVER (Dados Pessoais / PII):
- Nomes próprios de pessoas físicas e iniciais.
- CPFs, RGs, Matrículas e Processos Judiciais de partes/interessados.
- Datas exatas de nascimento/óbito de servidores e dependentes.
- Endereços residenciais particulares, telefones e e-mails pessoais.
- Diagnósticos médicos e CIDs específicos.

### 📌 MANTER (Contexto Jurídico de Acesso Aberto):
- **Municípios e Estados**: `Porto Velho`, `Vilhena`, `Cacoal`, `Guarapari/ES` *(Município é dado geográfico de interesse público)*.
- **Órgãos e Secretarias**: `SEDUC`, `SESAU`, `IPERON`, `SEJUS`, `HICD`.
- **Processos Administrativos / SEI**: `0016.004052/2023-81` *(Números NUP de processos públicos)*.
- **Precedentes de Tribunais Superiores**: `REsp 1.767.955/RJ`, `ARE 1.246.685/STF`, `RE 630.501/RS` *(Fundamentação de direito pública)*.

---

## 🛡️ Os 5 Invariantes Mecânicos Obligatórios (`anonimizar.py`)

Todo documento anonimizado **DEVE** satisfazer 100% dos 5 invariantes mecânicos:

1. **Invariante 1 (Extensão Paralela `.anon.md`)**: O arquivo gerado tem extensão `.anon.md` e preserva o original intacto.
2. **Invariante 2 (Estabilidade do Fingerprint P2)**: A canonicalização de campos operacionais históricos (`status_operacional`) é feita antes do hash para não alterar a impressão digital.
3. **Invariante 3 (Isolamento de Tags - Zero Aninhamento)**: Nenhuma tag `<pii>` pode ficar contida dentro de outra tag `<pii>`.
4. **Invariante 4 (Fidelidade do Hash e Frontmatter)**: A estrutura em Markdown, títulos, tabelas e metadados do documento mantêm fidelidade exata.
5. **Invariante 5 (Invariante de Resíduos / Consistência Global)**: Se uma PII é anonimizada em um ponto do documento, ela **NÃO PODE** ser esquecida em outro trecho do mesmo texto (ex.: URLs, tabelas ou notas de rodapé).

---

## 🤖 Auditoria Adversarial com Múltiplos Prompts LLM

Após a anonimização mecânica, o corpus concatenado é submetido a auditoria adversarial contra modelos LLM (Gemini 2.5 Flash / 2.0 Flash) utilizando dois papéis especializados:

1. **Prompt `Strict_Hunter`**: Atua como caçador hiper-rigoroso procurando nomes parciais, iniciais, idades de menores e dados de contato residuais.
2. **Prompt `Forensic_LGPD`**: Atua como perito forense de LGPD buscando vulnerabilidades de reidentificação por combinação de metadados ou vazamentos em rodapés.

---

## 🚀 Como Executar o Pipeline

```bash
# 1. Executar a marcação e substituição determinística dos documentos
uv run python scripts/anonimizar.py --input "caminho/para/pasta_md"

# 2. Validar os 5 invariantes mecânicos
uv run python scripts/process_pii_batch.py

# 3. Executar a auditoria adversarial concatenada via Gemini
uv run --with litellm python scripts/auditar_pii.py
```
