# API Contracts: Banking Transactions API

**Date**: 2026-04-26 | **Base URL**: `http://localhost:3000`

## POST /transactions

Create a new transaction.

**Request Body**:
```json
{
  "fromAccount": "ACC-12345",
  "toAccount": "ACC-67890",
  "amount": 100.50,
  "currency": "USD",
  "type": "transfer"
}
```

**Success Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "fromAccount": "ACC-12345",
  "toAccount": "ACC-67890",
  "amount": 100.50,
  "currency": "USD",
  "type": "transfer",
  "timestamp": "2026-04-26T10:30:00.000Z",
  "status": "completed"
}
```

**Validation Error Response** (400 Bad Request):
```json
{
  "error": "Validation failed",
  "details": [
    { "field": "amount", "message": "Amount must be a positive number" },
    { "field": "currency", "message": "Invalid currency code" }
  ]
}
```

## GET /transactions

List all transactions. Supports filtering via query parameters.

**Query Parameters** (all optional, combinable):
| Parameter | Type | Description |
|-----------|------|-------------|
| accountId | string | Filter by account (matches fromAccount or toAccount) |
| type | string | Filter by transaction type (deposit, withdrawal, transfer) |
| from | string | Filter start date (ISO 8601, inclusive) |
| to | string | Filter end date (ISO 8601, inclusive) |

**Success Response** (200 OK):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "fromAccount": "ACC-12345",
    "toAccount": "ACC-67890",
    "amount": 100.50,
    "currency": "USD",
    "type": "transfer",
    "timestamp": "2026-04-26T10:30:00.000Z",
    "status": "completed"
  }
]
```

## GET /transactions/:id

Get a specific transaction by ID.

**Success Response** (200 OK): Single transaction object (same shape as above)

**Not Found Response** (404):
```json
{
  "error": "Transaction not found"
}
```

## GET /transactions/export?format=csv

Export all transactions as CSV.

**Success Response** (200 OK):
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="transactions.csv"`

```csv
id,fromAccount,toAccount,amount,currency,type,timestamp,status
550e8400-e29b-41d4-a716-446655440000,ACC-12345,ACC-67890,100.50,USD,transfer,2026-04-26T10:30:00.000Z,completed
```

## GET /accounts/:accountId/balance

Get account balance calculated from all completed transactions.

**Success Response** (200 OK):
```json
{
  "accountId": "ACC-12345",
  "balances": {
    "USD": 300.00,
    "EUR": 150.00
  }
}
```

## GET /accounts/:accountId/summary

Get account activity summary.

**Success Response** (200 OK):
```json
{
  "accountId": "ACC-12345",
  "totalDeposits": 1000.00,
  "totalWithdrawals": 300.00,
  "transactionCount": 5,
  "mostRecentTransaction": "2026-04-26T10:30:00.000Z"
}
```
