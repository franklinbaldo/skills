# Installation branches

Use an isolated virtual environment locally. Do not install PaddleOCR into a
project environment unless the project already owns that dependency.

## CPU

CPU requires no CUDA and works on Windows and Linux:

```bash
uv venv .venv
uv pip install --python .venv/bin/python \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
  "paddlepaddle==3.3.0"
uv pip install --python .venv/bin/python "paddleocr>=3.7,<4"
```

On Windows, replace `.venv/bin/python` with
`.venv\Scripts\python.exe`.

CPU is a fallback, not the default for batches. It is materially slower than
an NVIDIA GPU; warn the user before processing a long PDF.

## Local NVIDIA GPU

Choose the official PaddlePaddle wheel index matching the environment:

| CUDA | Index                                                    |
| ---- | -------------------------------------------------------- |
| 11.8 | `https://www.paddlepaddle.org.cn/packages/stable/cu118/` |
| 12.6 | `https://www.paddlepaddle.org.cn/packages/stable/cu126/` |
| 12.9 | `https://www.paddlepaddle.org.cn/packages/stable/cu129/` |

Example for CUDA 12.6:

```bash
uv venv .venv
uv pip install --python .venv/bin/python \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  "paddlepaddle-gpu==3.3.0"
uv pip install --python .venv/bin/python "paddleocr>=3.7,<4"
```

Verify before OCR:

```bash
.venv/bin/python -c \
  "import paddle; print(paddle.__version__, paddle.device.is_compiled_with_cuda(), paddle.device.get_device())"
```

If the host CUDA or driver is incompatible, do not keep mutating the local
environment. Use the Colab branch.

## Google Colab CLI

The bundled `setup_colab_gpu.py` installs the CUDA 12.6 wheel with `uv`, which
was validated on a Colab T4. Run it only in the dedicated ephemeral session
created by `run_colab.sh`, then restart the kernel before importing Paddle.

The current official references are:

- <https://www.paddlepaddle.org.cn/documentation/docs/en/install/index_en.html>
- <https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html>

Check them before changing pinned Paddle or CUDA versions.
