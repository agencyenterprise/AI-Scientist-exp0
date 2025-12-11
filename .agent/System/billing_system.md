# Billing System Documentation

This document explains the credit-based billing system for AE-Scientist, including how credits are consumed, purchased via Stripe, and how to manually add credits for local testing.

## Related Documentation

- [Server Architecture](server_architecture.md) - Database schema and API routes
- [Database Migrations SOP](../SOP/server_database_migrations.md) - How to add new billing tables

---

## Overview

AE-Scientist uses a credit-based billing system where:
- Users have a **wallet** with a credit balance
- **Research pipeline runs** consume credits at a configurable rate (default: 1 credit/minute)
- Credits are purchased via **Stripe Checkout**
- All transactions are recorded for auditing

---

## Database Schema

Three tables in PostgreSQL (created in migration `0016_billing_tables.py`):

### `billing_user_wallets`
| Column | Type | Description |
|--------|------|-------------|
| `user_id` | INT (PK) | Foreign key to users table |
| `balance` | INT | Current credit balance (default: 0) |
| `updated_at` | TIMESTAMP | Last update timestamp |

### `billing_credit_transactions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT (PK) | Auto-increment ID |
| `user_id` | INT | Foreign key to users table |
| `amount` | INT | Credits (+positive for adds, -negative for debits) |
| `transaction_type` | TEXT | `purchase`, `debit`, `refund`, `adjustment` |
| `status` | TEXT | `pending`, `completed`, `refunded`, `failed` |
| `description` | TEXT | Optional description |
| `metadata` | JSONB | Additional data (run_id, price_id, etc.) |
| `stripe_session_id` | TEXT | Links to Stripe checkout session |
| `created_at`, `updated_at` | TIMESTAMP | Timestamps |

### `billing_stripe_checkout_sessions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT (PK) | Auto-increment ID |
| `user_id` | INT | Foreign key to users table |
| `stripe_session_id` | TEXT | Stripe's session ID (unique) |
| `price_id` | TEXT | Stripe price ID |
| `status` | TEXT | `created`, `completed`, `expired`, `failed` |
| `credits` | INT | Number of credits being purchased |
| `amount_cents` | INT | Price in cents |
| `currency` | TEXT | Default 'usd' |
| `metadata` | JSONB | Additional data |

---

## How Credits Flow

### Initial User Signup
- **AE employees** (email ends with `@ae.studio` or `@agencyenterprise.com`): Start with **1000 credits**
- **Regular users**: Start with **0 credits**
- Code: `server/app/services/database/users.py:58-67`

### Credit Consumption

1. **Before starting conversation import/ideation**:
   - Checks `MIN_USER_CREDITS_FOR_CONVERSATION` (default: 0)
   - File: `server/app/api/conversations.py:887, 923`

2. **Before starting research pipeline**:
   - Checks `MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE` (default: 0)
   - File: `server/app/api/research_pipeline_runs.py:409`

3. **During research pipeline execution**:
   - Billed at `RESEARCH_RUN_CREDITS_PER_MINUTE` (default: 1 credit/min)
   - Billing happens every minute while the run is active
   - If credits run out mid-run, the run fails with "insufficient_credits"
   - File: `server/app/services/research_pipeline/monitor.py:238-295`

### Credit Addition (Stripe Purchase)
1. User visits `/billing` page
2. Frontend calls `POST /billing/checkout-session` with `price_id`
3. Backend creates Stripe Checkout session
4. User completes payment on Stripe
5. Stripe sends `checkout.session.completed` webhook
6. Backend processes webhook at `POST /billing/stripe-webhook`
7. Credits added atomically to wallet + transaction recorded

---

## Configuration Settings

Set these environment variables in your `.env` file:

```bash
# Minimum credits required (default: 0 = no minimum)
MIN_USER_CREDITS_FOR_CONVERSATION=0
MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE=0

# Credits consumed per minute during research runs (default: 1)
RESEARCH_RUN_CREDITS_PER_MINUTE=1

# Stripe configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CHECKOUT_SUCCESS_URL=http://localhost:3000/billing?success=1

# Map Stripe price IDs to credit amounts
STRIPE_PRICE_TO_CREDITS={"price_xxx": 100, "price_yyy": 500}
```

File: `server/app/config.py:85-105`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/billing/wallet` | GET | Get balance + transaction history (paginated) |
| `/billing/packs` | GET | List available credit packs |
| `/billing/checkout-session` | POST | Create Stripe checkout session |
| `/billing/stripe-webhook` | POST | Webhook for Stripe events |

File: `server/app/api/billing.py`

---

## Manually Adding Credits for Local Testing

There are several ways to add credits for local development/testing:

### Method 1: Direct SQL (Quickest)

Connect to your local PostgreSQL database and run:

```sql
-- First, find your user_id
SELECT id, email FROM users WHERE email = 'your-email@example.com';

-- Add 1000 credits (adjust amount as needed)
-- This inserts a transaction record AND updates the wallet atomically
WITH inserted_txn AS (
    INSERT INTO billing_credit_transactions (
        user_id,
        amount,
        transaction_type,
        status,
        description,
        metadata
    )
    VALUES (
        1,  -- Replace with your user_id
        1000,  -- Number of credits to add
        'adjustment',
        'completed',
        'Manual credits for local testing',
        '{"reason": "local_testing"}'::jsonb
    )
    RETURNING user_id, amount
)
INSERT INTO billing_user_wallets (user_id, balance)
VALUES ((SELECT user_id FROM inserted_txn), (SELECT amount FROM inserted_txn))
ON CONFLICT (user_id)
DO UPDATE SET
    balance = billing_user_wallets.balance + (SELECT amount FROM inserted_txn),
    updated_at = NOW();

-- Verify the balance
SELECT * FROM billing_user_wallets WHERE user_id = 1;
```

### Method 2: Python Script (Using Database Helper)

Create a script or run in Python shell:

```python
from server.app.services.database import Database

db = Database()

# Add 1000 credits to user_id=1
db.add_completed_transaction(
    user_id=1,  # Your user ID
    amount=1000,  # Credits to add
    transaction_type="adjustment",
    description="Manual credits for local testing",
    metadata={"reason": "local_testing"}
)

# Verify
wallet = db.get_user_wallet(user_id=1)
print(f"Current balance: {wallet.balance}")
```

### Method 3: Sign Up as AE Employee

If you sign up with an email ending in `@ae.studio` or `@agencyenterprise.com`, you automatically get **1000 credits** on account creation.

### Method 4: Disable Credit Requirements

For development, you can set minimum requirements to 0:

```bash
# In your .env file
MIN_USER_CREDITS_FOR_CONVERSATION=0
MIN_USER_CREDITS_FOR_RESEARCH_PIPELINE=0
RESEARCH_RUN_CREDITS_PER_MINUTE=0  # Set to 0 to disable billing during runs
```

**Note**: Setting `RESEARCH_RUN_CREDITS_PER_MINUTE=0` effectively makes research runs free.

---

## Key Code Files

| File | Purpose |
|------|---------|
| `server/app/services/database/billing.py` | Database helpers (wallets, transactions) |
| `server/app/services/billing_service.py` | Business logic for Stripe integration |
| `server/app/services/billing_guard.py` | Credit enforcement (HTTP 402 responses) |
| `server/app/api/billing.py` | API endpoints |
| `server/app/services/research_pipeline/monitor.py` | Per-minute billing during runs |
| `server/database_migrations/versions/0016_billing_tables.py` | DB migration |
| `frontend/src/features/billing/api.ts` | Frontend API client |
| `frontend/src/app/(dashboard)/billing/page.tsx` | Billing UI page |

---

## Transaction Types

| Type | Amount | Description |
|------|--------|-------------|
| `purchase` | Positive | Credits bought via Stripe |
| `debit` | Negative | Credits consumed by research runs |
| `refund` | Positive | Manual refunds |
| `adjustment` | Any | Admin/manual adjustments |

---

## Troubleshooting

### "Insufficient credits" error
- Check wallet balance: `SELECT balance FROM billing_user_wallets WHERE user_id = ?`
- Add credits using methods above
- Or set `MIN_USER_CREDITS_FOR_*=0` in `.env`

### Credits not appearing after Stripe purchase
- Check webhook received: Look at server logs for `/billing/stripe-webhook`
- Verify `STRIPE_WEBHOOK_SECRET` is correct
- Check `billing_stripe_checkout_sessions` table status

### Research run failing due to credits
- The monitor checks credits every minute
- If balance < rate per minute, run fails
- Set `RESEARCH_RUN_CREDITS_PER_MINUTE=0` for development