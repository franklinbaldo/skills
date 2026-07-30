---
name: vibevoice-asr-bitnet
description: Transcreve áudio com microsoft/VibeVoice-ASR-BitNet usando o runtime oficial VibeASR.cpp em uma sessão Linux remota controlada pelo Google Colab CLI. Use quando for necessário enviar áudio, preparar o runtime, compilar o inferidor CPU, baixar os GGUF, recuperar transcrição e métricas e encerrar ou reutilizar a sessão sem abrir um notebook no navegador.
---

# VibeVoice ASR BitNet no Colab CLI

Use o runtime oficial `microsoft/VibeASR.cpp`, não uma integração genérica de
chat. O executável `asr_infer` recebe áudio e produz transcrição com segmentos e
falantes quando o modelo os retorna.

Este modelo é otimizado para **CPU**. O runtime oficial fixa a linguagem em CPU
(`n_gpu_layers = 0`), portanto não pedir T4, L4 ou outra GPU. O Colab serve aqui
como Linux remoto reproduzível, com armazenamento e CPU temporários; alocar GPU
não acelera esse caminho e pode consumir quota sem benefício.

## Caminho recomendado

No Linux, macOS ou WSL com o Colab CLI autenticado:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.mp3 ./resultado/transcricao
```

O wrapper:

1. cria uma sessão Colab CPU;
2. envia somente o áudio e um JSON de configuração;
3. converte a entrada para WAV mono de 24 kHz com FFmpeg;
4. compila uma revisão fixada do `VibeASR.cpp`;
5. baixa apenas os dois GGUF quantizados do modelo;
6. executa `asr_infer` com decodificação gulosa;
7. baixa a transcrição, metadados e log técnico; e
8. encerra a sessão mesmo quando uma etapa falha.

Arquivos locais produzidos:

- `<prefixo>.txt`: transcrição formatada;
- `<prefixo>.metadata.json`: revisão do runtime, CPU, threads, duração e comando;
- `<prefixo>.stderr.log`: progresso e métricas emitidos pelo inferidor.

A primeira execução baixa aproximadamente 1,58 GB de modelos e compila o
runtime. Para vários áudios, preservar e reutilizar a mesma sessão evita repetir
essas etapas:

```bash
bash <skill-dir>/scripts/run_colab.sh audio-1.wav ./saida/audio-1 \
  --session vibeasr-lote --keep

bash <skill-dir>/scripts/run_colab.sh audio-2.wav ./saida/audio-2 \
  --session vibeasr-lote --reuse --keep

uvx --from google-colab-cli colab stop -s vibeasr-lote
```

Não usar `--keep` por padrão. Uma sessão preservada continua sujeita a quota,
expiração e desconexão do Colab.

## Opções úteis

```bash
bash <skill-dir>/scripts/run_colab.sh entrada.m4a ./saida/transcricao \
  --threads 4 \
  --context "IPERON, Sisprev, Procuradoria-Geral do Estado"
```

- `--threads N`: fixa o número de threads; sem a opção, usa a CPU disponível
  com limite conservador de oito threads.
- `--context TEXTO`: envia hotwords ou contexto ao modelo. Não usar o campo para
  introduzir fatos que não estejam no áudio.
- `--session NOME`: escolhe um nome estável para a sessão.
- `--reuse`: exige que a sessão nomeada já exista e reaproveita build/modelos.
- `--keep`: não encerra a sessão ao final.

## Fluxo manual equivalente

Quando precisar depurar o transporte, executar as mesmas etapas sem o wrapper:

```bash
uvx --from google-colab-cli colab new -s vibeasr
uvx --from google-colab-cli colab upload -s vibeasr \
  gravacao.wav /content/vibevoice-input.wav
uvx --from google-colab-cli colab upload -s vibeasr \
  job.json /content/vibevoice-job.json
uvx --from google-colab-cli colab exec -s vibeasr \
  -f <skill-dir>/scripts/colab_job.py
uvx --from google-colab-cli colab download -s vibeasr \
  /content/vibevoice-transcript.txt ./transcricao.txt
uvx --from google-colab-cli colab stop -s vibeasr
```

O `colab exec -f` transmite o script local ao kernel; o áudio continua exigindo
`colab upload`. Preferir o wrapper porque ele mantém o `stop` em uma rotina de
limpeza.

## Plataforma local

O Colab CLI oficial suporta Linux e macOS. No Windows, usar WSL. Sem WSL ou
permissão administrativa, seguir a adaptação descrita em
[`free-gpu`](../free-gpu/SKILL.md) e [`litebox`](../litebox/SKILL.md), ou escolher
outro ambiente Linux. Não mandar o agente insistir na instalação direta do CLI
no Windows.

## Segurança e validação

- Confirmar antes que o áudio pode ser transferido à infraestrutura do Google.
- Não enviar gravação sigilosa, segredo, credencial ou dado pessoal sem base e
  autorização compatíveis com a finalidade.
- O checkpoint é público e não exige `HF_TOKEN`; não criar ou transmitir token
  sem necessidade.
- Preservar o áudio original. O wrapper só lê o arquivo local.
- Revisar nomes próprios, números, termos jurídicos, pontuação e atribuição de
  falantes contra o áudio. ASR não substitui conferência humana.
- Para português, sotaques ou domínio jurídico, registrar que a qualidade pode
  ser inferior aos benchmarks gerais do modelo.
- Se o áudio longo exceder memória ou contexto, dividir em trechos com pequena
  sobreposição e reconciliar as bordas; não truncar silenciosamente.
- Informar honestamente se a validação foi apenas sintática. Ajuda do CLI, build
  local ou dry run não provam quota, alocação ou inferência Colab ao vivo.

Referências oficiais:

- <https://huggingface.co/microsoft/VibeVoice-ASR-BitNet>
- <https://github.com/microsoft/VibeASR.cpp>
- <https://github.com/googlecolab/google-colab-cli>
