## 🔍 Feature Area: OpenAPI Schema Generation Missing Environment Variable

## Summary

The `make gen-api-types` command fails because `export_openapi.py` imports `app.main`, which triggers config initialization that requires `JSON_MODEL_PRICE_PER_MILLION_IN_CENTS` environment variable. The local `.env` file is missing this variable, while the CI workflow and `env.example` both include it.

## Code Paths Found

| File                                     | Lines  | Purpose                                                         | Action    |
| ---------------------------------------- | ------ | --------------------------------------------------------------- | --------- |
| `server/export_openapi.py`               | 1-10   | Imports app.main to export OpenAPI schema                       | reference |
| `server/app/main.py`                     | 7      | Imports settings from config (triggers initialization)          | reference |
| `server/app/config.py`                   | 27-76  | LLMPricing class requires non-empty JSON string                 | reference |
| `server/app/config.py`                   | 79-169 | Settings class instantiates LLMPricing at line 161              | reference |
| `server/app/config.py`                   | 161    | Hard-coded initialization: `LLMPricing(os.getenv(..., ""))`     | modify    |
| `server/app/validation.py`               | 5-19   | Validates pricing data matches LLM registry after init          | reference |
| `server/app/services/cost_calculator.py` | 23-28  | Uses LLM_PRICING.get_input_price/get_output_price               | reference |
| `server/.env`                            | 1-99   | Local env file missing JSON_MODEL_PRICE_PER_MILLION_IN_CENTS    | modify    |
| `server/env.example`                     | 84     | Contains proper JSON_MODEL_PRICE_PER_MILLION_IN_CENTS value     | reference |
| `.github/workflows/lint.yml`             | 139    | CI sets JSON_MODEL_PRICE_PER_MILLION_IN_CENTS for gen-api-types | reference |
| `server/Makefile`                        | 29-31  | export-openapi target runs export_openapi.py                    | reference |
| `server/Makefile`                        | 39-41  | gen-api-types depends on export-openapi                         | reference |

**Action legend**: `modify` (needs changes), `reference` (read only)

## Key Patterns

- Environment-based configuration loaded at import time (server/app/config.py:8)
- Settings instantiated as module-level singleton (server/app/config.py:169)
- LLMPricing validation ensures all registry models have pricing (server/app/validation.py:5-14)
- OpenAPI export script imports app to access FastAPI schema
- Make targets chain: gen-api-types → export-openapi → export_openapi.py

## Integration Points

- LLMPricing.**init** at config.py:32-46 parses nested JSON structure
- Settings.LLM_PRICING at config.py:161 instantiates with env var
- validate_configuration() at validation.py:17 called from app.main.py:11
- Cost calculator services access settings.LLM_PRICING methods at cost_calculator.py:24, 27

## Constraints Discovered

- LLMPricing cannot accept empty string (config.py:33-36)
- Pricing data must be valid JSON with nested provider/model structure (config.py:38-46)
- All models in LLM_PROVIDER_REGISTRY must have pricing entries (validation.py:9-14)
- CI workflow requires this env var to generate types during linting (.github/workflows/lint.yml:139)

## Root Cause

The local `server/.env` file does not contain the `JSON_MODEL_PRICE_PER_MILLION_IN_CENTS` variable that was added to `env.example`. When `make gen-api-types` runs, it triggers module-level config initialization which immediately fails.

## Solution Options

### Option A: Add Missing Env Var to Local .env (Recommended)

Copy the JSON_MODEL_PRICE_PER_MILLION_IN_CENTS value from `server/env.example:84` to `server/.env`.

**Pros**:

- Fixes immediate issue
- Aligns local config with CI and example
- No code changes needed

**Cons**:

- Requires manual env file update
- Doesn't prevent future similar issues

### Option B: Make LLMPricing Optional

Modify config.py:161 to conditionally instantiate LLMPricing only when env var is set, default to None.

**Pros**:

- Allows OpenAPI export without pricing config
- More resilient to missing config

**Cons**:

- Requires validation.py changes to skip validation when None
- Runtime errors when cost_calculator tries to use None pricing
- Pricing is critical business logic, shouldn't be optional

## Recommendation

**Option A** - Add the missing environment variable to local `.env`. This is the correct fix because:

1. Pricing is required business logic, not optional
2. CI and env.example already define this as required
3. The local .env simply fell out of sync with env.example
