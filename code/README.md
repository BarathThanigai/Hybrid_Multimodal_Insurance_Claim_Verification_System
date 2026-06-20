# Multi-Modal Evidence Review

Production-style Python pipeline for the HackerRank Orchestrate June 2026
challenge. It extracts multilingual claims, validates every referenced local
image, applies evidence rules and user-history risk context, and writes the exact
required `output.csv` schema.

## Architecture

1. `claim_extractor.py` extracts claimed parts and issues from English, Hindi,
   Hinglish, and Spanish conversations.
2. `image_analyzer.py` opens and technically checks each image, then emits the
   shared observation schema through a pluggable backend. Deterministic rules are
   the default; Hugging Face, Ollama, and OpenAI remain optional.
3. `evidence_validator.py` applies `evidence_requirements.csv`.
4. `risk_assessor.py` combines image-quality/authenticity flags with history flags.
   History never overrides visual evidence.
5. `decision_engine.py` deterministically returns supported, contradicted, or not
   enough information.
6. `main.py` validates and writes the exact output schema.

The rules backend validates image usability but derives semantic fields from the
claim. Model backends can provide independent visual perception. Text inside an
image is treated as untrusted content by model backends.

## Setup

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r code\requirements.txt
```

Unix/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r code/requirements.txt
```

No model download or paid API key is required for the default rules setup.

## Recommended rules backend

`VISION_BACKEND=rules` is the default and recommended mode for CPU-only systems
with limited RAM. It opens every referenced image, validates dimensions, measures
blur and low light, and maps multilingual claim extraction into `ImageObservation`.
It still applies `evidence_requirements.csv`, `user_history.csv`, risk assessment,
and the unchanged decision engine.

Its tradeoff is explicit: rules cannot independently verify semantic damage in
pixels. They provide fast, deterministic, reproducible orchestration rather than
model-grade visual understanding.

PowerShell:

```powershell
$env:VISION_BACKEND="rules"
python code\main.py --refresh-cache
```

Unix/macOS:

```bash
export VISION_BACKEND=rules
python code/main.py --refresh-cache
```

## Optional Hugging Face backend

The local model is `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`. This is the
canonical checkpoint to which the requested `SmolVLM2-500M-Instruct` name
redirects. It handles still images, runs on CPU, and is the recommended option
for an 8 GB RAM laptop without an NVIDIA GPU. The model is downloaded from
Hugging Face on first use and then reused from the local cache.

PowerShell:

```powershell
$env:VISION_BACKEND="huggingface"
$env:HF_MODEL="HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
$env:HF_DEVICE="cpu"
$env:HF_CPU_THREADS="4"
python code\main.py
```

Unix/macOS:

```bash
export VISION_BACKEND=huggingface
export HF_MODEL=HuggingFaceTB/SmolVLM2-500M-Video-Instruct
export HF_DEVICE=cpu
export HF_CPU_THREADS=4
python code/main.py
```

The first run needs internet access only to download model files. To download
without processing the full dataset, run:

```powershell
python -c "from transformers import AutoProcessor, AutoModelForImageTextToText; m='HuggingFaceTB/SmolVLM2-500M-Video-Instruct'; AutoProcessor.from_pretrained(m); AutoModelForImageTextToText.from_pretrained(m)"
```

After that succeeds, force offline-only loading so the final run never accesses
the network:

```powershell
$env:HF_LOCAL_FILES_ONLY="true"
python code\main.py --refresh-cache
```

If the 500M model is not accurate enough and the laptop can tolerate higher RAM
use and latency, switch to the 2.2B fallback without changing code:

```powershell
$env:HF_MODEL="HuggingFaceTB/SmolVLM2-2.2B-Instruct"
```

The 500M model is deliberately the lightweight option: the 2.2B variant may approach or
exceed comfortable memory limits on an 8 GB system during generation. Lower
`MAX_IMAGE_SIDE` (for example to `768`) or `HF_MAX_NEW_TOKENS` if memory or
latency is still tight. Environment variables can also be placed in a local
`code/.env` file; copy `code/.env.example` as a starting point.

## Generate predictions

```bash
python code/main.py
```

This reads `dataset/claims.csv` and writes `output.csv` plus
`output.telemetry.json`.

Useful options:

```bash
python code/main.py --input dataset/claims.csv --output output.csv
python code/main.py --model HuggingFaceTB/SmolVLM2-500M-Video-Instruct --refresh-cache --verbose
```

Responses are cached under `code/.cache/`. The cache key includes image bytes,
the extracted claim, backend, model, and prompt version. Switching backends
automatically ignores incompatible cache entries, so Hugging Face output can
never be reused by the rules backend.

## Evaluate

```bash
python code/evaluation/main.py
```

This generates:

- `code/evaluation/sample_predictions.csv`
- `code/evaluation/metrics.json`
- `code/evaluation/evaluation_report.md`

Expected labels are loaded only after predictions have been generated.

## Failure behavior

- Missing or corrupt images yield a conservative review result.
- Model loading and inference failures are isolated to the affected image.
- If no image can be analyzed, status is `not_enough_information` with
  `manual_review_required`.
- Every output row is enum- and schema-validated.
- One failed claim does not terminate the batch.

## Configuration

See `.env.example`. Defaults are centralized in `config.py`. The default rules
backend has no model, network, or API cost.

Common settings:

```text
VISION_BACKEND=rules
```

Optional Hugging Face backend:

```text
VISION_BACKEND=huggingface
HF_MODEL=HuggingFaceTB/SmolVLM2-500M-Video-Instruct
HF_DEVICE=cpu
HF_CPU_THREADS=4
HF_LOCAL_FILES_ONLY=false
```

Optional Ollama backend:

```text
VISION_BACKEND=ollama
OLLAMA_MODEL=qwen2.5vl:7b
OLLAMA_URL=http://localhost:11434
```

Optional OpenAI backend:

```bash
pip install openai
export VISION_BACKEND=openai
export OPENAI_API_KEY=...
export OPENAI_VISION_MODEL=gpt-5.5
```

All four backends use the same command after configuration:

```bash
python code/main.py --refresh-cache
python code/evaluation/main.py --refresh-cache
```
