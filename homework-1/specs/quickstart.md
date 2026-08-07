# Quickstart: Banking Transactions API

## Prerequisites

- Node.js 18+ installed
- npm (comes with Node.js)

## Setup

```bash
cd homework-1
npm install
```

## Run

```bash
npm start
```

Server starts at `http://localhost:3000`.

## Test

```bash
npm test
```

## Quick Smoke Test

```bash
# Create a transaction
curl -X POST http://localhost:3000/transactions \
  -H "Content-Type: application/json" \
  -d '{"fromAccount":"ACC-12345","toAccount":"ACC-67890","amount":100.50,"currency":"USD","type":"transfer"}'

# List all transactions
curl http://localhost:3000/transactions

# Get account balance
curl http://localhost:3000/accounts/ACC-12345/balance
```
