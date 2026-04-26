# 🏦 Banking Transactions API

> **Student Name**: Vladyslav Shut
> **Date Submitted**: 2026-04-26
> **AI Tools Used**: Claude Code (Claude Opus 4.6)

---

## 📋 Project Overview

A REST API for banking transactions built with Node.js and Express. Supports creating transactions, checking account balances, filtering transaction history, account summaries, and CSV export — all with in-memory storage.

## Features Implemented

| Task | Feature | Status |
|------|---------|--------|
| Task 1 | Core API (CRUD endpoints) | Done |
| Task 2 | Transaction Validation (amount, account, currency, type) | Done |
| Task 3 | Transaction History & Filtering (accountId, type, date range) | Done |
| Task 4A | Transaction Summary Endpoint | Done |
| Task 4C | Transaction CSV Export | Done |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /transactions | Create a new transaction |
| GET | /transactions | List all transactions (with filters) |
| GET | /transactions/:id | Get a specific transaction |
| GET | /transactions/export?format=csv | Export transactions as CSV |
| GET | /accounts/:accountId/balance | Get account balance (per-currency) |
| GET | /accounts/:accountId/summary | Get account activity summary |

## Architecture Decisions

- **Express.js** for HTTP routing — lightweight, widely used
- **In-memory array storage** — simple, no database dependency
- **Custom validation** — 4 rules don't justify a library like Joi
- **uuid v4** for transaction IDs — standard unique ID generation
- **Jest + supertest** for testing — HTTP-level endpoint tests

## Tech Stack

- Node.js 18+
- Express.js 4.x
- Jest 29.x + supertest 6.x
- uuid 9.x

## Project Structure

```
homework-1/
├── src/
│   ├── index.js                    # Express app setup
│   ├── routes/
│   │   ├── transactions.js         # Transaction CRUD, filter, export
│   │   └── accounts.js             # Balance, summary
│   ├── models/
│   │   └── store.js                # In-memory storage
│   ├── validators/
│   │   └── transactionValidator.js # Validation logic
│   └── utils/
│       └── helpers.js              # UUID, CSV, utilities
├── tests/                          # Jest test suites
├── demo/                           # Run script, sample requests
└── docs/screenshots/               # AI interaction screenshots
```

See [HOWTORUN.md](HOWTORUN.md) for setup and usage instructions.
