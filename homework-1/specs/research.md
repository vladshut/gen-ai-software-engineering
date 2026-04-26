# Research: Banking Transactions API

**Date**: 2026-04-26 | **Feature**: Banking Transactions API

## R1: Node.js Framework Selection

**Decision**: Express.js 4.x
**Rationale**: Express is the de facto standard for Node.js REST APIs. Minimal, unopinionated, well-documented. Perfect fit for a homework-scope API with ~6 endpoints.
**Alternatives considered**:
- Fastify: Better performance but more complex setup, overkill for in-memory homework project
- Koa: Smaller ecosystem, async middleware adds complexity without benefit here
- Hono: Newer, less documentation available for students

## R2: Transaction ID Generation

**Decision**: uuid v4 (via `uuid` npm package)
**Rationale**: Universally unique, no collision risk, standard practice for distributed systems. Simple `uuidv4()` call.
**Alternatives considered**:
- Sequential integers: Simple but not realistic for banking; reveals transaction count
- nanoid: Shorter IDs but less standard; uuid is more recognizable

## R3: In-Memory Storage Strategy

**Decision**: JavaScript Array for transactions, accessed by helper functions
**Rationale**: Array provides simple iteration for filtering. For ID lookups, a find() is sufficient at homework scale. No need for Map optimization.
**Alternatives considered**:
- Map<id, Transaction>: Better O(1) lookups but filtering still requires iteration
- SQLite in-memory: Overkill, adds dependency, spec says "no database"

## R4: Validation Approach

**Decision**: Custom validation module with regex and type checks
**Rationale**: Only 4 validation rules (amount, account format, currency, type). A library like Joi or Zod adds dependency overhead for trivial checks.
**Alternatives considered**:
- Joi: Powerful but heavy for 4 rules
- express-validator: Middleware-based, adds abstraction layer not needed
- Zod: TypeScript-first, not ideal for plain JS project

## R5: Testing Strategy

**Decision**: Jest for unit tests, supertest for HTTP integration tests
**Rationale**: Jest is the most popular Node.js test runner with built-in assertions and mocking. Supertest enables testing Express routes without starting a real server.
**Alternatives considered**:
- Mocha + Chai: More setup required, Jest has better DX
- Vitest: Newer, less widespread documentation

## R6: ISO 4217 Currency Validation

**Decision**: Hardcoded allowlist of common currencies (USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY)
**Rationale**: Spec requires "at minimum" these 8 currencies. A full ISO 4217 list (160+ codes) is unnecessary for homework scope and would bloat the codebase.
**Alternatives considered**:
- Full ISO 4217 list: Comprehensive but unnecessary
- npm currency-codes package: Adds dependency for a simple check

## R7: CSV Export Approach

**Decision**: Custom string builder with proper escaping
**Rationale**: Transaction data is flat (no nested objects). Simple join with comma separator, quoting fields that may contain commas. No need for a CSV library.
**Alternatives considered**:
- csv-stringify package: Overkill for flat data
- json2csv: Adds unnecessary dependency
