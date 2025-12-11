# 🔍 Feature Area: Billing System

## Summary

The billing system implements a credit-based wallet for users with Stripe integration for purchases and per-action/per-minute deductions for chat messages and research pipeline runs. Credits are stored in PostgreSQL, updated atomically via transactions, and streamed to frontend via SSE. Research runs bill continuously per minute via a monitor background thread.

## Code Paths Found

| File                                                                              | Lines            | Purpose                                                                                                                                                                                              | Action    |
| --------------------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `server/app/services/billing_service.py`                                          | 21-194           | Orchestrates wallet queries, Stripe checkout sessions, webhook fulfillment                                                                                                                           | reference |
| `server/app/services/database/billing.py`                                         | 16-297           | Database operations for wallets, transactions, Stripe sessions                                                                                                                                       | reference |
| `server/app/services/stripe_client.py`                                            | 10-40            | Thin wrapper around Stripe SDK for price retrieval and checkout session creation                                                                                                                     | reference |
| `server/app/api/billing.py`                                                       | 29-179           | API endpoints: `/billing/wallet`, `/billing/packs`, `/billing/checkout-session`, `/billing/wallet/stream`, `/billing/stripe-webhook`                                                                 | reference |
| `server/app/models/billing.py`                                                    | 8-44             | Pydantic schemas for API requests/responses                                                                                                                                                          | reference |
| `server/app/services/billing_guard.py`                                            | 12-76            | Enforces minimum credit checks and charges credits atomically                                                                                                                                        | reference |
| `server/app/api/chat_stream.py`                                                   | 82-111           | Enforces `MIN_USER_CREDITS_FOR_CONVERSATION`, charges `CHAT_MESSAGE_CREDIT_COST` per message                                                                                                         | modify    |
| `server/app/api/conversations.py`                                                 | 887-902, 934-944 | Charges credits for conversation imports and manual idea seeds                                                                                                                                       | modify    |
| `server/app/api/research_pipeline_runs.py`                                        | 423-428, 149-150 | Enforces `MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE` on launch, initializes `last_billed_at`                                                                                                            | modify    |
| `server/app/services/research_pipeline/monitor.py`                                | 238-299          | Bills running research runs per minute at rate `RESEARCH_RUN_CREDITS_PER_MINUTE`, updates `last_billed_at`                                                                                           | reference |
| `server/database_migrations/versions/0016_billing_tables.py`                      | 23-168           | Creates `billing_user_wallets`, `billing_credit_transactions`, `billing_stripe_checkout_sessions` tables                                                                                             | reference |
| `server/database_migrations/versions/0017_add_last_billed_at_to_research_runs.py` | 16-24            | Adds `last_billed_at` timestamp column to `research_pipeline_runs`                                                                                                                                   | reference |
| `server/app/config.py`                                                            | 84-106           | Config: `MIN_USER_CREDITS_FOR_CONVERSATION` (1), `MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE` (30), `CHAT_MESSAGE_CREDIT_COST` (1), `RESEARCH_RUN_CREDITS_PER_MINUTE` (1), `STRIPE_PRICE_TO_CREDITS` map | reference |
| `frontend/src/features/billing/api.ts`                                            | 1-51             | Frontend API client: `fetchWallet`, `fetchCreditPacks`, `createCheckoutSession`                                                                                                                      | reference |
| `frontend/src/app/(dashboard)/billing/page.tsx`                                   | 25-175           | Billing page UI: wallet balance, credit packs, transactions table                                                                                                                                    | reference |
| `frontend/src/shared/hooks/useWalletBalance.ts`                                   | 15-111           | React hook: fetches wallet balance, connects to SSE stream `/billing/wallet/stream`, updates query cache on balance changes                                                                          | reference |

**Action legend**: `modify` (files that charge/enforce credits), `reference` (infrastructure/read-only)

## Key Patterns

### Database Schema (0016_billing_tables.py:23-144)

- **`billing_user_wallets`**: `user_id` (PK, FK to users), `balance` (int, default 0), `updated_at`
- **`billing_credit_transactions`**: `id`, `user_id`, `amount` (int, negative for debits), `transaction_type` (purchase/debit/refund/adjustment), `status` (pending/completed/refunded/failed), `description`, `metadata` (JSONB), `stripe_session_id`, timestamps
- **`billing_stripe_checkout_sessions`**: `id`, `user_id`, `stripe_session_id` (unique), `price_id`, `status` (created/completed/expired/failed), `credits`, `amount_cents`, `currency`, `metadata` (JSONB), timestamps

### Credit Purchase Flow

1. User requests `/billing/packs` → returns Stripe price IDs mapped to credit amounts from `STRIPE_PRICE_TO_CREDITS` env var (config.py:102-104)
2. User POSTs to `/billing/checkout-session` with `price_id` → creates Stripe checkout session, persists record in `billing_stripe_checkout_sessions` (billing_service.py:85-143)
3. User completes payment → Stripe sends webhook to `/billing/stripe-webhook` (billing.py:148-178)
4. Webhook handler verifies signature, calls `handle_webhook` → on `checkout.session.completed`, updates session status and calls `_complete_checkout_session` (billing_service.py:148-193)
5. Fulfillment: creates `billing_credit_transactions` record with positive amount, atomically updates wallet balance (database/billing.py:114-185)

### Credit Enforcement & Charging

- **Enforcement**: `enforce_minimum_credits(user_id, required, action)` → raises HTTP 402 if `balance < required` (billing_guard.py:12-35)
- **Charging**: `charge_user_credits(user_id, cost, action, description, metadata)` → checks balance, raises HTTP 402 if insufficient, creates debit transaction with negative amount, atomically updates wallet (billing_guard.py:38-76)
- **Atomic update**: `add_completed_transaction` uses INSERT + UPDATE in single transaction (database/billing.py:124-185)

### Per-Action Billing

- **Chat messages**: enforce `MIN_USER_CREDITS_FOR_CONVERSATION` (1), charge `CHAT_MESSAGE_CREDIT_COST` (1) per message (chat_stream.py:82-111)
- **Conversation imports**: enforce min + charge `CHAT_MESSAGE_CREDIT_COST` (conversations.py:887-902, 934-944)
- **Research pipeline runs**: enforce `MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE` (30) on launch (research_pipeline_runs.py:423-428)

### Per-Minute Billing (Research Runs)

- Background monitor thread polls active runs every N seconds (monitor.py:57-64)
- For each running run: calculate elapsed minutes since `last_billed_at`, bill at rate `RESEARCH_RUN_CREDITS_PER_MINUTE` (default 1 credit/min) (monitor.py:238-299)
- If insufficient credits, fail run with status "failed" and reason "insufficient_credits" (monitor.py:256-263)
- On success: create debit transaction, insert `billing_debit` event, update `last_billed_at` timestamp (monitor.py:276-298)

### Real-Time Balance Updates (SSE)

- Frontend hook `useWalletBalance` connects to `/billing/wallet/stream` (useWalletBalance.ts:34-94)
- Backend emits SSE events on balance changes: `{"type":"credits","data":{"balance":N}}` (billing.py:106-145)
- Frontend updates React Query cache on credit events, triggering UI refresh (useWalletBalance.ts:64-75)

### Initial Wallet Creation

- Wallets created on user signup via `ensure_user_wallet(user_id, is_ae_user)` (database/billing.py:52-64)
- AE employees get 10,000 credits, regular users get 10 credits (database/billing.py:54)
- Migration 0016 backfills wallets for existing users with balance 0 (0016_billing_tables.py:147-153)

## Integration Points

### Backend

- **BillingService** → StripeClient (billing_service.py:28-31)
- **BillingService** → DatabaseManager (billing_service.py:25)
- **BillingGuard** (enforce/charge) → DatabaseManager.get_user_wallet_balance, add_completed_transaction (billing_guard.py:22-75)
- **Chat API** → BillingGuard.enforce_minimum_credits, charge_user_credits (chat_stream.py:82-111)
- **Conversations API** → BillingGuard (conversations.py:887-902, 934-944)
- **Research Pipeline API** → BillingGuard.enforce_minimum_credits (research_pipeline_runs.py:423-428)
- **ResearchPipelineMonitor** → DatabaseManager.add_completed_transaction, insert_research_pipeline_run_event (monitor.py:276-298)
- **Stripe Webhook** → BillingService.handle_webhook (billing.py:148-178)

### Frontend

- **BillingPage** → fetchWallet, fetchCreditPacks, createCheckoutSession (billing/page.tsx:26-69)
- **useWalletBalance** → apiStream(/billing/wallet/stream), React Query cache updates (useWalletBalance.ts:44-75)
- **Header/UserProfileDropdown** → likely uses useWalletBalance hook to display balance

### Database

- **billing_user_wallets.user_id** → users.id (FK, CASCADE)
- **billing_credit_transactions.user_id** → users.id (FK, CASCADE)
- **billing_stripe_checkout_sessions.user_id** → users.id (FK, CASCADE)
- **research_pipeline_runs.last_billed_at** → used by monitor for per-minute billing (0017_add_last_billed_at_to_research_runs.py:16-24)

## Constraints Discovered

### Configuration (server/app/config.py:84-106)

- `MIN_USER_CREDITS_FOR_CONVERSATION`: 1 (default)
- `MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE`: 30 (default)
- `CHAT_MESSAGE_CREDIT_COST`: 1 (default)
- `RESEARCH_RUN_CREDITS_PER_MINUTE`: 1 (default)
- `STRIPE_PRICE_TO_CREDITS`: JSON map from env var (e.g., `{"price_1ABC":100,"price_2DEF":1000}`)

### Business Rules

- All credit amounts are integers (no fractional credits)
- Positive amounts = credits added, negative = credits deducted
- Stripe checkout sessions are idempotent: if status already "completed", skip fulfillment (billing_service.py:167-169)
- Research runs fail immediately if user lacks credits to bill next minute (monitor.py:256-263)
- Atomic wallet updates prevent race conditions (database/billing.py:164-184)

### Security

- Stripe webhook signature verification required (billing.py:167, billing_service.py:148)
- All billing endpoints require authentication via `get_current_user` (billing.py:46, 69, 91)
- Credit checks happen before operations to prevent over-spending

### Performance

- Transaction listing limited to 100 per request (billing.py:41-42)
- SSE heartbeat every 30s to detect disconnects (billing.py:132-134)
- Wallet balance polled every 5s in SSE stream (billing.py:136)
- Indexes on `billing_credit_transactions`: `(user_id, created_at)`, partial index on pending status (0016_billing_tables.py:89-99)
