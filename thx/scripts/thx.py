# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3"]
# ///
"""Roda perguntas da Gemini Decisions API sobre um JSONL de entradas.

A chave vem de GEMINI_API_KEY e fica só em memória. A saída é retomável:
ids já respondidos são pulados.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import cyclopts

URL = "https://generativelanguage.googleapis.com/v1beta/decisions"
app = cyclopts.App(help="Triagem com a Gemini Decisions API (gemini-decision-1).")


def perguntar(chave: str, entrada: str, perguntas: dict, modelo: str) -> dict:
    corpo = json.dumps({"model": modelo, "input": entrada, "questions": perguntas}).encode()
    pedido = urllib.request.Request(URL, corpo, {"x-goog-api-key": chave, "Content-Type": "application/json"})
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                return json.load(resposta)
        except urllib.error.HTTPError as erro:
            if erro.code == 429:
                time.sleep(30 * (tentativa + 1))
                continue
            return {"erro": erro.code, "corpo": erro.read().decode()[:300]}
        except OSError:
            time.sleep(10)
    return {"erro": "tentativas esgotadas"}


def ja_respondidos(saida: Path) -> set[str]:
    if not saida.exists():
        return set()
    return {json.loads(linha)["id"] for linha in saida.read_text().splitlines() if linha.strip()}


@app.command
def executar(
    entradas: Path,
    perguntas: Path,
    saida: Path,
    *,
    fatias: int = 1,
    modelo: str = "gemini-decision-1",
    pausa: float = 0.3,
) -> None:
    """Responde PERGUNTAS para cada linha {"id", "input"} de ENTRADAS, gravando em SAIDA."""
    chave = os.environ.get("GEMINI_API_KEY", "")
    if not chave:
        raise SystemExit("defina GEMINI_API_KEY (lida de um cofre, nunca colada no chat)")
    questoes = json.loads(perguntas.read_text())
    feitos = ja_respondidos(saida)
    itens = [json.loads(linha) for linha in entradas.read_text().splitlines() if linha.strip()]
    pendentes = [item for item in itens if item["id"] not in feitos]
    trava = threading.Lock()

    def trabalhar(fatia: int) -> None:
        for item in pendentes[fatia::fatias]:
            resposta = perguntar(chave, item["input"], questoes, modelo)
            linha = {
                "id": item["id"],
                "answers": resposta.get("answers"),
                "erro": resposta.get("erro"),
                "tokens": resposta.get("usage", {}).get("total_input_tokens"),
            }
            with trava, saida.open("a") as arquivo:
                arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
            time.sleep(pausa)

    threads = [threading.Thread(target=trabalhar, args=(i,)) for i in range(fatias)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"{len(pendentes)} entradas processadas; saída em {saida}")


if __name__ == "__main__":
    app()
