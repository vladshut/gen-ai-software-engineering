# Implementation Plan: Banking Transactions API

**Branch**: `homework-1-submission` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `homework-1/spec.md`

## Summary

Build a REST API for banking transactions using Node.js and Express with in-memory storage. The API supports transaction CRUD operations, field-level validation (amount, account format, currency), transaction filtering by account/type/date, account balance calculation with standard banking semantics, account summary aggregation, and CSV export. All 19 functional requirements from spec are covered.

## Technical Context

**Language/Version**: Node.js 18+ (LTS)
**Primary Dependencies**: Express.js (HTTP framework), uuid (ID generation)
**Storage**: In-memory (JavaScript Map/Array — no database)
**Testing**: Jest + supertest (HTTP endpoint testing)
**Target Platform**: Local development server (macOS/Linux)
**Project Type**: web-service (REST API)
**Performance Goals**: Sub-second response for all endpoints (homework scope)
**Constraints**: In-memory only, single instance, no auth, port 3000
**Scale/Scope**: Single developer homework project, ~10 source files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is a blank template with no project-specific rules defined. No gates to evaluate. ✅ Passed.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────┐
│                   Express App                     │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────┐│
│  │   Routes     │  │  Validators  │  │  Utils   ││
│  │             │  │              │  │          ││
│  │ transactions│  │ transaction  │  │ helpers  ││
│  │ accounts    │  │ Validator    │  │ csv      ││
│  └──────┬──────┘  └──────┬───────┘  └────┬─────┘│
│         │                │               │       │
│  ┌──────▼──────────────────────────────────────┐ │
│  │              In-Memory Store                 │ │
│  │   transactions: Map<id, Transaction>         │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Request Flow

1. Client sends HTTP request → Express router matches endpoint
2. Route handler invokes validator (for POST) → returns 400 if invalid
3. Route handler interacts with in-memory store
4. Response formatted and returned with appropriate status code

## Project Structure

### Documentation (this feature)

```text
homework-1/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 API contracts
│   └── api.md           # REST endpoint contracts
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 task list (created by /speckit-tasks)
```

### Source Code (repository root)

```text
homework-1/
├── package.json
├── .gitignore
├── README.md
├── HOWTORUN.md
├── src/
│   ├── index.js              # Express app setup + server start
│   ├── routes/
│   │   ├── transactions.js   # Transaction CRUD + filter + export routes
│   │   └── accounts.js       # Balance + summary routes
│   ├── models/
│   │   └── store.js          # In-memory transaction store
│   ├── validators/
│   │   └── transactionValidator.js  # All validation logic
│   └── utils/
│       └── helpers.js        # CSV generation, currency codes, shared utilities
├── tests/
│   ├── transactions.test.js  # Transaction endpoint tests
│   ├── accounts.test.js      # Balance + summary endpoint tests
│   ├── validation.test.js    # Validation logic tests
│   └── export.test.js        # CSV export tests
├── demo/
│   ├── run.sh               # Start script
│   ├── sample-requests.http  # Sample API calls
│   └── sample-data.json     # Sample transaction data
└── docs/
    └── screenshots/         # AI tool interaction screenshots
```

**Structure Decision**: Single project layout with Express conventions — routes, models, validators, and utils directories. Tests in a parallel `tests/` directory. Demo and docs directories as required by homework deliverables.

## Tech Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Express.js | Most widely used Node.js framework, minimal boilerplate, perfect for REST APIs |
| ID Generation | uuid v4 | Standard unique ID generation, no collision risk |
| Testing | Jest + supertest | Jest is the Node.js testing standard; supertest enables HTTP-level endpoint testing |
| Validation | Custom (no library) | Homework scope — simple validation rules don't warrant a library like Joi |
| CSV Generation | Custom | Simple string concatenation sufficient for flat transaction data |

## Complexity Tracking

No constitution violations to justify. Project is straightforward — single Express app with in-memory storage.
