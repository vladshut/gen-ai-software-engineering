# Data Model: Banking Transactions API

**Date**: 2026-04-26 | **Source**: [spec.md](spec.md)

## Entities

### Transaction

The core entity representing a money movement between accounts.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | string | Auto-generated UUID v4, unique | Primary identifier |
| fromAccount | string | ACC-XXXXX format (5 alphanumeric), optional for deposits | Sender account |
| toAccount | string | ACC-XXXXX format (5 alphanumeric), optional for withdrawals | Receiver account |
| amount | number | Positive, max 2 decimal places | Transaction amount |
| currency | string | ISO 4217 code from allowlist | USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY |
| type | string | Enum: deposit, withdrawal, transfer | Transaction category |
| timestamp | string | ISO 8601 datetime, auto-generated | Creation time |
| status | string | Enum: pending, completed, failed. Defaults to "completed" | Transaction state |

### Account (Implicit)

Accounts are not stored explicitly. They are identified by their account number (ACC-XXXXX) and their properties (balance, summary) are derived from transactions.

**Balance calculation** (per-currency, standard banking semantics):
- **Deposit**: `toAccount.balance += amount`
- **Withdrawal**: `fromAccount.balance -= amount`
- **Transfer**: `fromAccount.balance -= amount` AND `toAccount.balance += amount`

## Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| amount | Must be a positive number | "Amount must be a positive number" |
| amount | Max 2 decimal places | "Amount must have at most 2 decimal places" |
| fromAccount | Must match `/^ACC-[A-Za-z0-9]{5}$/` | "Account number must follow ACC-XXXXX format" |
| toAccount | Must match `/^ACC-[A-Za-z0-9]{5}$/` | "Account number must follow ACC-XXXXX format" |
| currency | Must be in allowlist | "Invalid currency code" |
| type | Must be deposit, withdrawal, or transfer | "Type must be deposit, withdrawal, or transfer" |
| fromAccount | Required for withdrawal and transfer | "fromAccount is required for this transaction type" |
| toAccount | Required for deposit and transfer | "toAccount is required for this transaction type" |

## Relationships

```
Transaction *──── fromAccount (ACC-XXXXX)
Transaction *──── toAccount (ACC-XXXXX)

Account (implicit) ────* Transaction (derived via fromAccount or toAccount match)
```

- An Account's existence is inferred from transactions referencing its ID
- Balance and summary are computed on-the-fly from the transaction store
- No lifecycle or state transitions for accounts — they exist as long as transactions reference them
