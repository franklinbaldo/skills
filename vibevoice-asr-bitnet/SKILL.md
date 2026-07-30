---
name: vibevoice-asr-bitnet
description: Transcreve áudio com microsoft/VibeVoice-ASR-BitNet usando o runtime oficial VibeASR.cpp em uma sessão Linux remota controlada pelo Google Colab CLI. Use quando for necessário preparar áudio, reduzir o upload com MP3 temporário, compilar o inferidor CPU, baixar os GGUF, recuperar transcrição e métricas e escolher entre o BitNet econômico e variantes VibeVoice de maior qualidade.
---

# VibeVoice ASR BitNet no Colab CLI

Use o runtime oficial `microsoft/VibeASR.cpp`, não uma integração genérica de
chat. O executável `asr_infer` recebe áudio e produz transcrição com segmentos e
falantes quando o modelo os retorna.

Este modelo é otimizado para **CPU**. O runtime oficial fixa a linguagem em CPU
(`n_gpu_layers = 0`), portanto não pedir T4, L4 ou outra GPU para o caminho
BitNet. O Colab serve aqui como Linux remoto reproduzível, com armazenamento e
CPU temporários; alocar GPU não acelera este runtime e pode consumir quota sem
benefício.

## Escolher a variante

Não confundir checkpoint, empacotamento e runtime:

| Opção | Qualidade esperada | Recurso no Colab | Quando usar |
| --- | --- | --- | --- |
| `microsoft/VibeVoice-ASR-BitNet` + `VibeASR.cpp` | Menor que o 7B, mas próxima; o relatório mede aumento de 1–4 pontos absolutos de WER | CPU, cerca de 1,58 GB de modelos | padrão econômico, lotes, máquinas sem GPU e validação rápida |
| `microsoft/VibeVoice-ASR` | melhor qualidade oficial pronta, modelo 7B | GPU de alta memória; preferir A100 e medir por duração | áudio jurídico crítico, sotaques difíceis e máxima precisão antes de ajuste fino |
| `microsoft/VibeVoice-ASR-HF` | a mesma família/pesos do modelo completo em formato Transformers | GPU de alta memória | integração direta com Transformers; não é uma variante mais precisa por si só |
| modelo completo via vLLM | mesma qualidade do modelo completo | GPU, voltado a serviço e concorrência | muitos arquivos ou API persistente; melhora throughput, não WER isolado |
| LoRA do modelo completo | pode superar o modelo geral no domínio treinado | GPU para treino e inferência | corpus jurídico representativo, avaliação separada e manutenção do adaptador |

No benchmark publicado pelo projeto BitNet, o WER em português passa de 22,41
no VibeVoice-ASR-7B para 24,87 no BitNet. Portanto, quando **qualidade prevalece
sobre custo**, o salto relevante é usar o modelo completo 7B, não procurar outro
GGUF oficial dentro do repositório BitNet. Hoje há somente um par oficial pronto
para `VibeASR.cpp`: VAE `I8_S` e LM `I2_S` com embeddings `Q6_K`.

O modelo completo aceita mais de 50 idiomas e áudio longo, mas a memória cresce
com a duração. Não presumir que T4 de 16 GB ou L4 de 24 GB executará qualquer
arquivo em FP16. Preferir A100; em hardware menor, testar trechos curtos e dividir
o áudio com sobreposição. Quantizações comunitárias de 4 bits são experimentais:
não tratá-las como melhoria de qualidade sem benchmark no corpus real.

Para português jurídico, o ganho de menor custo costuma vir antes de trocar o
modelo: fornecer `--context` com nomes, órgãos, siglas e vocabulário que
realmente possam aparecer no áudio. Avaliar sempre contra uma amostra revisada.

Esta skill automatiza atualmente o caminho BitNet oficial. Para o modelo completo,
seguir o runtime oficial `microsoft/VibeVoice` e registrar GPU, dtype, duração,
chunking e revisão do checkpoint; não declarar esse caminho validado por este
wrapper.

## Caminho recomendado

No Linux, macOS ou WSL com o Colab CLI autenticado:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.wav ./resultado/transcricao
```

O wrapper:

1. cria uma sessão Colab CPU;
2. converte localmente a entrada para MP3 mono de 24 kHz e 128 kbps, sem alterar
   o original, para reduzir o upload;
3. envia o MP3 temporário e um JSON de configuração;
4. converte a entrada remota para WAV PCM mono de 24 kHz com FFmpeg;
5. compila uma revisão fixada do `VibeASR.cpp`;
6. baixa apenas os dois GGUF quantizados do modelo;
7. executa `asr_infer` com decodificação gulosa;
8. baixa a transcrição, metadados e log técnico; e
9. encerra a sessão mesmo quando uma etapa falha.

Se a entrada já for MP3, o wrapper a envia sem recomprimir. A conversão para MP3
é uma otimização de transporte, **não** uma melhoria de reconhecimento. Em áudio
crítico, já comprimido em AAC/OGG, muito ruidoso ou com fala sobreposta, evitar
uma nova geração lossy:

```bash
bash <skill-dir>/scripts/run_colab.sh gravacao.m4a ./resultado/transcricao \
  --upload-format original
```

Para reduzir mais o upload, `--mp3-bitrate 96k` é aceitável em fala limpa. Para
preservar melhor ruído, sibilância e vozes sobrepostas, manter 128k ou usar
`--upload-format original`.

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
  --context "IPERON, Sisprev, Procuradoria-Geral do Estado" \
  --mp3-bitrate 128k
```

- `--threads N`: fixa o número de threads; sem a opção, usa a CPU disponível
  com limite conservador de oito threads.
- `--context TEXTO`: envia hotwords ou contexto ao modelo. Não usar o campo para
  introduzir fatos que não estejam no áudio.
- `--upload-format mp3|original`: usa MP3 temporário por padrão ou envia a fonte
  intacta quando evitar recompressão for prioritário.
- `--mp3-bitrate TAXA`: controla o MP3 temporário, por exemplo `96k`, `128k` ou
  `192k`; não se aplica a um arquivo que já seja MP3.
- `--session NOME`: escolhe um nome estável para a sessão.
- `--reuse`: exige que a sessão nomeada já exista e reaproveita build/modelos.
- `--keep`: não encerra a sessão ao final.

## Fluxo manual equivalente

Quando precisar depurar o transporte, executar as mesmas etapas sem o wrapper:

```bash
ffmpeg -i gravacao.wav -vn -ac 1 -ar 24000 \
  -c:a libmp3lame -b:a 128k /tmp/vibevoice-upload.mp3
uvx --from google-colab-cli colab new -s vibeasr
uvx --from google-colab-cli colab upload -s vibeasr \
  /tmp/vibevoice-upload.mp3 /content/vibevoice-input.mp3
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
- Preservar o áudio original. O MP3 é temporário e removido no cleanup local.
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
- <https://huggingface.co/microsoft/VibeVoice-ASR>
- <https://huggingface.co/microsoft/VibeVoice-ASR-HF>
- <https://github.com/microsoft/VibeASR.cpp>
- <https://github.com/microsoft/VibeVoice>
- <https://github.com/googlecolab/google-colab-cli>
