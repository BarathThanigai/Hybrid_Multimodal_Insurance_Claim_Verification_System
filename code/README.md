# Multi-Modal Evidence Review

Production-style Python pipeline for the HackerRank Orchestrate June 2026
challenge. It extracts multilingual claims, independently analyzes every local
image with a vision model, applies evidence rules and user-history risk context,
and writes the exact required `output.csv` schema.

## Architecture

1. `claim_extractor.py` extracts claimed parts and issues from English, Hindi,
   Hinglish, and Spanish conversations.
2. `image_analyzer.py` sends each image independently to the OpenAI Responses API
   and requires structured visual observations.
3. `evidence_validator.py` applies `evidence_requirements.csv`.
4. `risk_assessor.py` combines image-quality/authenticity flags with history flags.
   History never overrides visual evidence.
5. `decision_engine.py` deterministically returns supported, contradicted, or not
   enough information.
6. `main.py` validates and writes the exact output schema.

Images are primary evidence. Text inside an image is treated as untrusted content.

## Setup

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r code\requirements.txt
$env:OPENAI_API_KEY="your-key"
```

Unix/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r code/requirements.txt
export OPENAI_API_KEY="your-key"
```

All secrets come from environment variables. Never commit `.env` files.

## Generate predictions

```bash
python code/main.py
```

This reads `dataset/claims.csv` and writes `output.csv` plus
`output.telemetry.json`.

Useful options:

```bash
python code/main.py --input dataset/claims.csv --output output.csv
python code/main.py --model gpt-5.5 --refresh-cache --verbose
```

Responses are cached under `code/.cache/`. The cache key includes image bytes,
the extracted claim, model, and prompt version.

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
- API failures are retried and isolated to the affected image.
- If no image can be analyzed, status is `not_enough_information` with
  `manual_review_required`.
- Every output row is enum- and schema-validated.
- One failed claim does not terminate the batch.

## Configuration

See `.env.example`. Defaults are centralized in `config.py`. Cost figures are
estimates using configurable assumptions.
