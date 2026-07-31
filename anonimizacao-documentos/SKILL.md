---
name: anonimizacao-documentos
description: Anonimiza textos e documentos Markdown jurídicos ou administrativos para publicação, revisão ou formação de corpus. Use para detectar PII com OpenAI Privacy Filter localmente ou em GPU do Google Colab, revisar marcações semânticas, substituir dados por marcadores canônicos e auditar resíduos segundo a política LGPD do projeto.
---

# Anonimização de documentos

Trate este fluxo como redução de risco, não como garantia automática de
anonimização ou conformidade. Preserve o original, mantenha revisão humana e
registre as limitações da detecção.

## Escolher o fluxo

- Usar `scripts/anonimizar_opf.py` para detectar PII em texto ainda não
  marcado com `openai/privacy-filter`.
- Usar `scripts/anonimizar.py` quando o texto já contém tags `pii` revisadas e
  só falta gerar marcadores determinísticos.
- Usar GPU local ou Colab para o modelo. Não iniciar OPF neste laptop sem GPU.
  O modo CPU existe apenas como override explícito para diagnóstico e pode ser
  impraticavelmente lento.
- Para documentos jurídicos, governamentais, médicos ou de RH, revisar
  manualmente tanto falsos negativos quanto remoções excessivas.

O modelo padrão reconhece apenas oito classes: número de conta, endereço,
e-mail, pessoa, telefone, URL, data privada e segredo. Ele é principalmente
treinado em inglês. O script complementa o modelo com padrões mecânicos para
CPF e número CNJ, mas RG, matrícula, OAB, saúde e outras categorias brasileiras
continuam exigindo revisão ou ajuste específico.

## Fluxo recomendado

1. Extrair o documento para Markdown ou texto sem sobrescrever o original.
2. Rodar a detecção assistida em uma GPU. Sem GPU local, usar diretamente o
   wrapper Colab da seção seguinte. Em uma máquina com NVIDIA configurada:

   ```bash
   uv run --no-project \
     --with "opf @ git+https://github.com/openai/privacy-filter.git@f7f00ca7fb869683eb732c010299d901457f19c3" \
     python <skill-dir>/scripts/anonimizar_opf.py \
     --input documento.md --device cuda
   ```

3. Inspecionar `documento.tagged.md`. Corrigir spans, categorias e referências
   antes de liberar a versão anonimizada.
4. Gerar novamente a versão determinística após qualquer correção:

   ```bash
   uv run --no-project python <skill-dir>/scripts/anonimizar.py \
     --input documento.tagged.md
   ```

5. Revisar `documento.anon.md` contra o original. Procurar especialmente
   nomes parciais, iniciais, rodapés, URLs, metadados, RG, matrícula, OAB,
   diagnósticos e combinações que permitam reidentificação.

Os relatórios `.opf-report.json` contêm somente contagens, configuração e
avisos; não persistir os spans originais com PII.

## Google Colab CLI com GPU

Executar a partir do WSL onde `colab` está autenticado:

```bash
bash <skill-dir>/scripts/run_colab_opf.sh documento.md ./documento
```

Este é o caminho padrão quando a máquina local não tem GPU. O wrapper cria uma
sessão T4, instala o pacote oficial com `uv`, envia um único
arquivo, baixa os resultados e encerra a VM. A entrada é enviada para a
infraestrutura do Google; obter autorização antes de usar o Colab com material
sigiloso ou restrito.

O `google-colab-cli` 0.6.0 instalado diretamente no Windows é sabidamente
incompatível porque importa os módulos Unix `termios` e `tty`. Não mandar o
agente repetir esse caminho. Sem WSL, consultar
[`free-gpu`](../free-gpu/SKILL.md): usar Kaggle nativo ou adaptar o cliente
Linux do Colab pela aula [`litebox`](../litebox/SKILL.md).

O wrapper PowerShell abaixo usa deliberadamente um shim limitado a comandos
não interativos; ele não é uma instalação Windows nativa:

```powershell
powershell -ExecutionPolicy Bypass -File `
  <skill-dir>\scripts\run_colab_opf.ps1 `
  -InputPath documento.md -OutputPrefix .\documento
```

Usar esse wrapper somente quando o fluxo escolher explicitamente o shim. Para
uma adaptação geral do cliente Linux, seguir a
[receita Colab do LiteBox](../litebox/references/task-recipes.md).

O checkpoint é público e não requer token. Se `HF_TOKEN` estiver salvo nos
Colab Secrets, o script tenta lê-lo com `google.colab.userdata` sem imprimir ou
persistir o valor. Não colocar tokens em argumentos, notebooks, scripts ou no
Google Drive.

Para reutilizar o checkpoint entre sessões, montar o Drive de forma explícita:

```bash
COLAB_DRIVE_CACHE=1 \
  bash <skill-dir>/scripts/run_colab_opf.sh documento.md ./documento
```

Isso usa a autenticação OAuth do Drive, não um segredo contendo credenciais do
Drive. O primeiro uso ainda baixa o modelo e grava uma cópia em
`MyDrive/.cache/openai/privacy-filter`; em sessões posteriores, o script usa
essa cópia. Medir antes de manter essa opção: ler vários gigabytes do Drive
pode não ser mais rápido que baixar o checkpoint.

## Política de substituição

Marcar spans revisados neste formato:

```xml
<pii tipo='nome_pessoa' ref='1'>JOÃO DA SILVA</pii>
<pii tipo='cpf' ref='1'>123.456.789-00</pii>
```

O passe determinístico gera `_NOME_PESSOA_1_`, `_CPF_1_` e equivalentes.
Repetições com o mesmo tipo e `ref` recebem o mesmo marcador. Não aninhar tags.

Remover, conforme a finalidade e base legal:

- nomes e iniciais de pessoas físicas;
- CPF, RG, matrícula, conta e identificadores de partes;
- endereço, telefone, e-mail e URL privada;
- datas pessoais, saúde, segredos e credenciais;
- números CNJ que identifiquem partes ou permitam reidentificação.

Não remover automaticamente municípios, órgãos públicos, processos
administrativos públicos ou precedentes apenas por parecerem identificadores.
A decisão depende da finalidade, do acesso e do risco de combinação.

## Auditoria externa opcional

`scripts/auditar_pii.py` envia o texto a um provedor LLM. Usar somente com
autorização explícita para a transferência a terceiro e nunca tratar a resposta
como prova de ausência de PII. O fluxo local com OPF e revisão humana é o
padrão.

## Validação mínima

- Confirmar que o original permanece intacto.
- Confirmar que não restaram tags abertas, fechadas sem par ou aninhadas.
- Revisar cada span do `.tagged.md` e cada marcador do `.anon.md`.
- Executar busca mecânica por identificadores brasileiros conhecidos.
- Informar modelo, dispositivo, arquivos produzidos e limitações.

Referências oficiais:

- <https://huggingface.co/openai/privacy-filter>
- <https://github.com/openai/privacy-filter>
