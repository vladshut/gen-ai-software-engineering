# How to Run

## Prerequisites

- Node.js 18 or higher
- npm (comes with Node.js)

## Installation

```bash
cd homework-1
npm install
```

## Start the Server

```bash
npm start
```

The API will be running at `http://localhost:3000`.

## Run Tests

```bash
npm test
```

## Example API Requests

### Create a transaction (transfer)

```bash
curl -X POST http://localhost:3000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "fromAccount": "ACC-12345",
    "toAccount": "ACC-67890",
    "amount": 100.50,
    "currency": "USD",
    "type": "transfer"
  }'
```

### Create a deposit

```bash
curl -X POST http://localhost:3000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "toAccount": "ACC-12345",
    "amount": 500,
    "currency": "USD",
    "type": "deposit"
  }'
```

### List all transactions

```bash
curl http://localhost:3000/transactions
```

### Filter transactions by account

```bash
curl "http://localhost:3000/transactions?accountId=ACC-12345"
```

### Filter by type and date range

```bash
curl "http://localhost:3000/transactions?type=deposit&from=2024-01-01&to=2026-12-31"
```

### Get a specific transaction

```bash
curl http://localhost:3000/transactions/<transaction-id>
```

### Get account balance

```bash
curl http://localhost:3000/accounts/ACC-12345/balance
```

### Get account summary

```bash
curl http://localhost:3000/accounts/ACC-12345/summary
```

### Export transactions as CSV

```bash
curl http://localhost:3000/transactions/export?format=csv
```
