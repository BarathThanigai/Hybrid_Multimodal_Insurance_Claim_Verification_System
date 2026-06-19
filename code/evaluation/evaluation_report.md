# Evaluation Report

Generated: 2026-06-19T07:53:34.043333+00:00

## Final strategy

Each image is independently analyzed by a vision-capable model using a strict
structured schema. Deterministic Python modules then apply evidence requirements,
history-only risk flags, and final decisions. Images remain the primary source of
truth; user history never changes a visual decision.

> **Environment note:** this measured run had no usable vision API credential.
> Every model call followed the conservative failure path. The metrics below
> therefore validate schema, orchestration, claim extraction, and error handling;
> they are not representative of the configured vision strategy. Re-run with
> `OPENAI_API_KEY` set before submission to obtain meaningful visual metrics.


## Sample metrics

| Field | Exact accuracy |
|---|---:|
| `evidence_standard_met` | 10.0% |
| `risk_flags` | 5.0% |
| `issue_type` | 15.0% |
| `object_part` | 85.0% |
| `claim_status` | 10.0% |
| `supporting_image_ids` | 10.0% |
| `valid_image` | 10.0% |
| `severity` | 10.0% |

Full structured-row accuracy: **0.0%**

Risk flag set F1: **25.5%**

Supporting-image set F1: **10.0%**

### Claim-status accuracy by object

| Object | Accuracy |
|---|---:|
| car | 12.5% |
| laptop | 0.0% |
| package | 16.7% |

## Strategy comparison

1. **Rules-only fallback:** multilingual dictionaries extract claims and technical
   checks detect unreadable images, but rules cannot reliably perceive semantic damage.
2. **Vision observations + deterministic policy (selected):** the model performs
   perception; code controls evidence, risk, decisions, enums, and serialization.

## Operational analysis

- Claims processed: 20
- Images processed: 29
- Approximate model calls: 29
- Cache hits: 0
- Input tokens: 0
- Output tokens: 0
- Approximate cost: **$0.0000**
- Runtime: 1.68 seconds
- Model: `gpt-5.5`

Pricing assumptions are configurable. Images are resized before upload and cached
by bytes, claim, model, and prompt version. SDK retries are bounded; sequential
processing stays conservative for RPM/TPM, while bounded concurrency can be added.

## Failure behavior

Unreadable images and exhausted API retries are isolated. The affected claim is
emitted conservatively as `not_enough_information` with
`manual_review_required`. Every row is schema-validated before writing.
