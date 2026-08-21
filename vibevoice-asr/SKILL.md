---
name: vibevoice-asr
description: Transcreve áudio com VibeVoice ASR pelo Google Colab CLI, escolhendo entre o BitNet econômico em CPU e o modelo completo VibeVoice-ASR-HF em GPU de alta memória. Use para converter o upload temporariamente em MP3, fornecer hotwords, executar transcrição estruturada com falantes e timestamps, comparar qualidade e custo, recuperar artefatos e encerrar ou reutilizar a sessão.
compatibility: >-
  Requires network access, Python/uv and an authenticated Google Colab CLI on
  Linux/macOS or WSL. BitNet runs remotely on CPU; the full 7B model requires a
  high-memory CUDA GPU such as A100/H100. Audio is transferred to Google Colab.
---

# VibeVoice ASR no Colab CLI

Escolha conscientemente entre dois caminhos oficiais:

- **BitNet**: `microsoft/VibeVoice-ASR-BitNet` com `VibeASR.cpp`, 1,58 GB,
  inferência CPU e menor custo;
- **full**: `microsoft/VibeVoice-ASR-HF` com Transformers, modelo completo 7B,
  maior qualidade e necessidade de GPU de alta memória.

Não trate `ASR-HF`, vLLM ou outra interface como modelo automaticamente mais
preciso: o ganho de qualidade vem do checkpoint completo 7B. vLLM muda sobretudo
o throughput. O projeto BitNet publica apenas o par GGUF VAE `I8_S` + LM `I2_S`
com embeddings `Q6_K`; não inventar uma gradação oficial Q4/Q5/Q8 inexistente.

## Escolher o modelo

| Situação                                            | Escolha                             |
| --------------------------------------------------- | ----------------------------------- |
| triagem, lotes, baixo custo, ausência de GPU        | `--model bitnet`                    |
| áudio jurídico crítico, sotaques ou máxima precisão | `--model full` em A100/H100         |
| disponibilidade mais importante que garantir o 7B   | `--model full --fallback-bitnet`    |
| a execução deve falhar se não obtiver o 7B          | `--model full --no-fallback-bitnet` |

No benchmark comparativo publicado pelo projeto BitNet, o WER em português foi
22,41 no VibeVoice-ASR-7B e 24,87 no BitNet. O repositório principal publica
outras medições sob configuração diferente; registrar sempre checkpoint,
runtime, dtype e corpus ao comparar resultados.

## Uso rápido

BitNet em sessão CPU, padrão:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.wav ./resultado/transcricao
```

Modelo completo em A100:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.wav ./resultado/transcricao-full \
  --model full --gpu A100 \
  --context "IPERON, Sisprev, Procuradoria-Geral do Estado"
```

Fallback explícito para BitNet quando a GPU não for alocada, o modelo não couber
inteiramente na GPU ou o job completo falhar:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.wav ./resultado/transcricao \
  --model full --gpu A100 --fallback-bitnet
```

O fallback nunca deve ser escondido. O wrapper imprime `Requested model`,
`Effective model` e `Fallback reason`; os mesmos campos ficam no metadata.
Sem `--fallback-bitnet`, `--model full` falha em vez de entregar silenciosamente
uma transcrição BitNet.

## MP3 para transporte

Por padrão, entradas que não sejam MP3 são convertidas **localmente** para MP3
mono, 24 kHz e 128 kbps antes do upload. O original não é alterado. No Colab, o
arquivo recebido é normalizado para WAV PCM mono de 24 kHz, formato comum aos
dois runtimes.

A conversão para MP3 reduz tráfego; não melhora reconhecimento. Se o áudio já
for AAC/OGG, estiver muito ruidoso, contiver fala sobreposta ou exigir máxima
fidelidade, evitar nova compressão lossy:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.m4a ./resultado/transcricao \
  --upload-format original
```

`--mp3-bitrate 96k` serve para fala limpa e upload menor. Manter 128k como
padrão; 192k raramente traz ganho de ASR que justifique o tráfego.

## Como cada caminho roda

### BitNet

O wrapper cria sessão CPU e executa `scripts/colab_job_bitnet.py`, que:

1. converte o áudio remoto para WAV mono de 24 kHz;
2. compila uma revisão fixada do `microsoft/VibeASR.cpp`;
3. baixa apenas os dois GGUF oficiais;
4. executa `asr_infer` em CPU, com decodificação gulosa;
5. registra CPU, threads, revisão, duração e métricas.

O runtime oficial define `n_gpu_layers = 0`. Não pedir T4, L4 ou A100 para este
caminho: isso consome quota sem acelerar a inferência BitNet.

### Modelo completo

O wrapper solicita a GPU indicada, A100 por padrão, e executa
`scripts/colab_job_full.py`, que:

1. confirma que CUDA está visível antes de baixar o modelo;
2. converte o áudio para WAV mono de 24 kHz;
3. instala uma revisão fixada do Transformers com suporte nativo a VibeVoice;
4. carrega `microsoft/VibeVoice-ASR-HF` com BF16 em GPUs Ampere ou posteriores,
   ou FP16 em GPUs mais antigas;
5. recusa offload parcial para CPU/disco, pois isso pode transformar o job em
   uma execução imprevisivelmente lenta;
6. usa `apply_transcription_request`, contexto opcional e geração determinística;
7. salva transcrição, segmentos estruturados no metadata, GPU, dtype e pico de
   memória.

O modelo aceita áudio longo e o projeto anuncia até 60 minutos em uma passagem,
mas isso não garante que qualquer duração caiba em qualquer GPU. A memória cresce
com o áudio. Preferir A100/H100; em GPU menor, reduzir
`--acoustic-chunk-size` para múltiplo de 3200 ou dividir o arquivo com pequena
sobreposição.

Exemplo reduzindo o chunk acústico de 1.440.000 para 64.000 amostras:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.wav ./resultado/transcricao \
  --model full --gpu A100 --acoustic-chunk-size 64000
```

Isso reduz memória do tokenizer, mas não garante que o modelo completo caiba na
VRAM disponível.

## Hotwords e contexto

Use `--context` para nomes, órgãos, siglas e vocabulário que realmente possam
aparecer no áudio:

```bash
--context "IPERON, Sisprev, TJRO, Porto Velho, Procuradoria-Geral do Estado"
```

Não introduzir fatos, versões ou conclusões que não estejam na gravação. O texto
de contexto é redigido dos comandos e não é repetido no metadata; permanece
necessário considerar que ele é enviado ao runtime remoto junto com o job.

## Sessões e lotes

Preservar a sessão evita recompilar ou baixar modelos em cada arquivo:

```bash
bash <skill-dir>/scripts/run_colab.sh audio-1.mp3 ./saida/audio-1 \
  --model full --session vibeasr-lote --keep

bash <skill-dir>/scripts/run_colab.sh audio-2.mp3 ./saida/audio-2 \
  --model full --session vibeasr-lote --reuse --keep

uvx --from google-colab-cli colab stop -s vibeasr-lote
```

Uma sessão reutilizada mantém o acelerador originalmente alocado. Se uma sessão
CPU for reutilizada com `--model full`, o job falha rapidamente ou usa o fallback
somente quando `--fallback-bitnet` tiver sido passado.

Não usar `--keep` por padrão. Sessões preservadas consomem quota e continuam
sujeitas a expiração.

## Opções

- `--model bitnet|full`: escolhe checkpoint e runtime;
- `--gpu A100|H100|L4|T4`: acelerador pedido para `full`; disponibilidade depende
  do plano, quota e capacidade atual;
- `--fallback-bitnet`: autoriza downgrade explícito após falha de GPU ou full;
- `--threads N`: controla threads do BitNet;
- `--max-tokens N`: limita a saída dos dois runtimes;
- `--acoustic-chunk-size N`: controla o chunk do tokenizer do full e deve ser
  múltiplo de 3200;
- `--context TEXTO`: fornece hotwords/contexto;
- `--upload-format mp3|original`: escolhe staging comprimido ou fonte intacta;
- `--mp3-bitrate TAXA`: controla o MP3 temporário;
- `--session`, `--reuse`, `--keep`: controlam o ciclo da sessão.

## Artefatos

- `<prefixo>.txt`: transcrição sem rótulos técnicos;
- `<prefixo>.metadata.json`: modelo solicitado/efetivo, fallback, revisão,
  hardware, duração e configuração; no full, inclui segmentos estruturados;
- `<prefixo>.stderr.log`: build/inferência e métricas; no full, inclui a saída
  bruta do modelo para auditoria.

## Plataforma e segurança

O Colab CLI oficial suporta Linux e macOS. No Windows, usar WSL. Sem WSL ou
permissão administrativa, seguir [`free-gpu`](../free-gpu/SKILL.md) e
[`litebox`](../litebox/SKILL.md), ou escolher outro ambiente Linux.

- confirmar que a gravação pode ser transferida à infraestrutura do Google;
- não enviar material sigiloso ou dados pessoais sem base e autorização;
- preservar o original e remover o MP3 temporário no cleanup local;
- revisar nomes, números, termos jurídicos, timestamps e falantes contra o áudio;
- não confundir fallback bem-sucedido com validação do modelo completo;
- informar honestamente quando a verificação foi apenas sintática ou simulada.

Referências oficiais:

- <https://huggingface.co/microsoft/VibeVoice-ASR-BitNet>
- <https://huggingface.co/microsoft/VibeVoice-ASR>
- <https://huggingface.co/microsoft/VibeVoice-ASR-HF>
- <https://huggingface.co/docs/transformers/model_doc/vibevoice_asr>
- <https://github.com/microsoft/VibeASR.cpp>
- <https://github.com/microsoft/VibeVoice>
- <https://github.com/googlecolab/google-colab-cli>

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
