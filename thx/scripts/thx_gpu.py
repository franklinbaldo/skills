"""Run THX-02 over a JSONL batch on a free GPU (Colab T4 or Kaggle).

Same contract as `thx.py`: each input line is {"id", "input"}; each output line
is {"id", "answers", "erro"}. The output is resumable: ids already written are
skipped, so a session that dies can be restarted on the same files.

Paths are found by environment, overridable with THX_ENTRADAS, THX_PERGUNTAS
and THX_SAIDA:
- Colab: /content/entradas.jsonl, /content/perguntas.json -> /content/saida.jsonl
- Kaggle: the first entradas.jsonl and perguntas.json under /kaggle/input
  -> /kaggle/working/saida.jsonl

Installs `thx02[local]` when it is missing (Kaggle has no install step).
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def caminhos() -> tuple[Path, Path, Path]:
    kaggle = Path("/kaggle/input")
    if kaggle.exists():
        entradas = next(kaggle.rglob("entradas.jsonl"))
        perguntas = next(kaggle.rglob("perguntas.json"))
        saida = Path("/kaggle/working/saida.jsonl")
    else:
        entradas = Path("/content/entradas.jsonl")
        perguntas = Path("/content/perguntas.json")
        saida = Path("/content/saida.jsonl")
    return (
        Path(os.environ.get("THX_ENTRADAS", entradas)),
        Path(os.environ.get("THX_PERGUNTAS", perguntas)),
        Path(os.environ.get("THX_SAIDA", saida)),
    )


def conferir_gpu() -> None:
    import torch

    if not torch.cuda.is_available():
        sys.exit("sem GPU CUDA: abra a sessão com --gpu T4 ou ligue o acelerador no Kaggle")
    nome = torch.cuda.get_device_name(0)
    capacidade = torch.cuda.get_device_capability(0)
    print(f"GPU: {nome} (sm{capacidade[0]}{capacidade[1]})", flush=True)
    if capacidade < (8, 0):
        print(
            "aviso: sem BF16 nativo; o thx02 carrega em BF16 no CUDA. Calibre contra a API antes do lote.", flush=True
        )


def main() -> None:
    entradas, perguntas, saida = caminhos()
    conferir_gpu()
    if importlib.util.find_spec("thx02") is None:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "thx02[local]"], check=True)
    from thx02 import THX02
    from thx02.protocol import LengthError

    questoes = json.loads(perguntas.read_text())
    feitos = set()
    if saida.exists():
        feitos = {json.loads(linha)["id"] for linha in saida.read_text().splitlines() if linha.strip()}
    itens = [json.loads(linha) for linha in entradas.read_text().splitlines() if linha.strip()]
    pendentes = [item for item in itens if item["id"] not in feitos]
    print(f"{len(pendentes)} pendentes de {len(itens)}", flush=True)

    modelo = THX02.load(os.environ.get("THX_MODELO", "HAL-X-AI/THX-02"), device="cuda")
    inicio = time.time()
    with saida.open("a") as arquivo:
        for n, item in enumerate(pendentes, 1):
            try:
                resposta = modelo.decide(item["input"], questoes, think=False)
                linha = {"id": item["id"], "answers": resposta.get("answers"), "erro": None}
            except LengthError as erro:  # entrada longa demais para o modelo
                linha = {"id": item["id"], "answers": None, "erro": str(erro)[:300]}
            arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
            arquivo.flush()
            if n % 100 == 0:
                print(f"{n}/{len(pendentes)} em {time.time() - inicio:.0f}s", flush=True)
    print(f"fim: {len(pendentes)} em {time.time() - inicio:.0f}s; saída em {saida}", flush=True)


if __name__ == "__main__":
    main()
