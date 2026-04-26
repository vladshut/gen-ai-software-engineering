# Feature Specification: Banking Transactions API

**Feature Branch**: `homework-1-submission`
**Created**: 2026-04-26
**Status**: Draft
**Input**: User description: "Build a Simple Banking Transactions REST API with CRUD operations, validation, filtering, and additional features"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Retrieve Transactions (Priority: P1)

A user sends money between bank accounts by creating a transaction. They can then view all transactions or look up a specific one by ID. This is the core operation the entire API revolves around.

**Why this priority**: Without transaction creation and retrieval, no other feature has meaning. This is the foundational capability.

**Independent Test**: Can be fully tested by sending POST requests to create transactions and GET requests to retrieve them. Delivers immediate value as the primary banking operation.

**Acceptance Scenarios**:

1. **Given** no transactions exist, **When** a user creates a transfer of 100.50 USD from ACC-12345 to ACC-67890, **Then** the system returns a 201 status with the transaction including an auto-generated ID, ISO 8601 timestamp, and "completed" status.
2. **Given** a transaction with ID "txn-001" exists, **When** a user requests that transaction by ID, **Then** the system returns a 200 status with the full transaction details.
3. **Given** multiple transactions exist, **When** a user requests all transactions, **Then** the system returns a 200 status with a list of all transactions.
4. **Given** no transaction with ID "txn-999" exists, **When** a user requests that ID, **Then** the system returns a 404 status with an appropriate error message.

---

### User Story 2 - Validate Transaction Data (Priority: P1)

A user submitting a transaction receives clear, field-level error messages when the data is invalid. This prevents bad data from entering the system and provides a good developer experience.

**Why this priority**: Equal to P1 because invalid data must never be accepted — validation is inseparable from transaction creation.

**Independent Test**: Can be tested by submitting transactions with various invalid fields and verifying each returns the correct validation error with field-level detail.

**Acceptance Scenarios**:

1. **Given** a transaction with amount -50, **When** submitted, **Then** the system returns a 400 status with error details indicating "Amount must be a positive number."
2. **Given** a transaction with amount 100.999 (3 decimal places), **When** submitted, **Then** the system returns a 400 with error details indicating "Amount must have at most 2 decimal places."
3. **Given** a transaction with fromAccount "INVALID", **When** submitted, **Then** the system returns a 400 with error details indicating account must follow ACC-XXXXX format.
4. **Given** a transaction with currency "XYZ" (not ISO 4217), **When** submitted, **Then** the system returns a 400 with error details indicating invalid currency code.
5. **Given** a transaction with multiple invalid fields, **When** submitted, **Then** the system returns all validation errors at once (not just the first one).

---

### User Story 3 - Check Account Balance (Priority: P2)

A user checks their account balance by querying the account balance endpoint. The balance is calculated from all completed transactions involving that account.

**Why this priority**: Balance is a derived view of transactions — important but dependent on transactions existing first.

**Independent Test**: Can be tested by creating several transactions for an account and verifying the balance endpoint returns the correct calculated balance.

**Acceptance Scenarios**:

1. **Given** ACC-12345 has received 500 USD in deposits and sent 200 USD in transfers, **When** a user requests the balance for ACC-12345, **Then** the system returns a 200 status with balance of 300 USD.
2. **Given** no transactions exist for ACC-99999, **When** a user requests the balance, **Then** the system returns a 200 status with balance of 0.

---

### User Story 4 - Filter Transaction History (Priority: P2)

A user filters their transaction list by account, type, or date range to find specific transactions. Multiple filters can be combined.

**Why this priority**: Filtering enhances usability for accounts with many transactions — important for real-world use but not strictly required for core operations.

**Independent Test**: Can be tested by creating diverse transactions and applying various filter combinations, verifying only matching transactions are returned.

**Acceptance Scenarios**:

1. **Given** transactions exist for multiple accounts, **When** a user filters by `?accountId=ACC-12345`, **Then** only transactions involving ACC-12345 (as sender or receiver) are returned.
2. **Given** transactions of types deposit, withdrawal, and transfer exist, **When** a user filters by `?type=transfer`, **Then** only transfer transactions are returned.
3. **Given** transactions span January through March, **When** a user filters by `?from=2024-01-01&to=2024-01-31`, **Then** only January transactions are returned.
4. **Given** various transactions exist, **When** a user combines filters `?accountId=ACC-12345&type=deposit`, **Then** only deposits involving ACC-12345 are returned.

---

### User Story 5 - View Account Summary (Priority: P3)

A user views a summary of their account activity including total deposits, total withdrawals, number of transactions, and most recent transaction date.

**Why this priority**: This is an additional/optional feature that provides analytical value on top of the core functionality.

**Independent Test**: Can be tested by creating a mix of transactions for an account and verifying the summary endpoint returns correct aggregated values.

**Acceptance Scenarios**:

1. **Given** ACC-12345 has 3 deposits totaling 1000 USD and 2 withdrawals totaling 300 USD, **When** a user requests the account summary, **Then** the system returns total deposits (1000), total withdrawals (300), transaction count (5), and most recent transaction date.
2. **Given** no transactions exist for ACC-99999, **When** a user requests the summary, **Then** the system returns zeroes for all totals and null for most recent date.

---

### User Story 6 - Export Transactions as CSV (Priority: P3)

A user exports their transaction data in CSV format for use in spreadsheets or external reporting tools.

**Why this priority**: Export is a convenience feature that adds value but is not essential for core operations.

**Independent Test**: Can be tested by creating transactions and requesting CSV export, verifying the response is valid CSV with correct headers and data.

**Acceptance Scenarios**:

1. **Given** multiple transactions exist, **When** a user requests `GET /transactions/export?format=csv`, **Then** the system returns a CSV file with headers (id, fromAccount, toAccount, amount, currency, type, timestamp, status) and one row per transaction.
2. **Given** no transactions exist, **When** a user requests CSV export, **Then** the system returns a CSV file with only the header row.

---

### Edge Cases

- What happens when a deposit has only a `toAccount` and no `fromAccount`? (Deposits should require only toAccount; fromAccount is optional)
- What happens when a withdrawal has only a `fromAccount` and no `toAccount`? (Withdrawals should require only fromAccount; toAccount is optional)
- What happens when amount is exactly 0? (Should be rejected — amounts must be positive)
- What happens when date range filters have `from` after `to`? (Should return empty results or a 400 error)
- What happens when filter parameters have invalid values (e.g., `?type=invalid`)? (Should return 400 with descriptive error)
- How does balance calculation handle different currencies? (Balance is calculated per-currency — each currency tracked separately)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to create transactions via POST /transactions with fields: fromAccount, toAccount, amount, currency, and type
- **FR-002**: System MUST auto-generate a unique ID and ISO 8601 timestamp for each transaction, defaulting status to "completed"
- **FR-003**: System MUST return all transactions via GET /transactions
- **FR-004**: System MUST return a specific transaction by ID via GET /transactions/:id, returning 404 if not found
- **FR-005**: System MUST calculate and return account balance via GET /accounts/:accountId/balance using standard banking semantics: deposits add to toAccount balance, withdrawals subtract from fromAccount balance, transfers subtract from fromAccount and add to toAccount. Balance is tracked per-currency.
- **FR-006**: System MUST validate that transaction amounts are positive numbers with at most 2 decimal places
- **FR-007**: System MUST validate that account numbers follow the format ACC-XXXXX where X is alphanumeric (letters and digits)
- **FR-008**: System MUST validate currency codes against ISO 4217 standard (accepting at minimum: USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY)
- **FR-009**: System MUST validate that transaction type is one of: deposit, withdrawal, or transfer
- **FR-010**: System MUST return field-level validation errors with a structured error response containing field name and error message for each invalid field
- **FR-011**: System MUST support filtering transactions by accountId (matching either fromAccount or toAccount)
- **FR-012**: System MUST support filtering transactions by type
- **FR-013**: System MUST support filtering transactions by date range using `from` and `to` query parameters with ISO 8601 date format
- **FR-014**: System MUST support combining multiple filter parameters simultaneously
- **FR-015**: System MUST provide an account summary endpoint (GET /accounts/:accountId/summary) returning total deposits, total withdrawals, transaction count, and most recent transaction date
- **FR-016**: System MUST provide a CSV export endpoint (GET /transactions/export?format=csv) returning transaction data in CSV format
- **FR-017**: For deposit transactions, fromAccount is optional; for withdrawal transactions, toAccount is optional; for transfer transactions, both are required
- **FR-018**: System MUST use in-memory storage (no database required)
- **FR-019**: System MUST return appropriate HTTP status codes: 200 for success, 201 for creation, 400 for validation errors, 404 for not found

### Key Entities

- **Transaction**: The core entity representing a money movement. Attributes: id (auto-generated string), fromAccount (string, ACC-XXXXX format), toAccount (string, ACC-XXXXX format), amount (positive number, max 2 decimals), currency (ISO 4217 string), type (deposit|withdrawal|transfer), timestamp (ISO 8601 datetime), status (pending|completed|failed)
- **Account**: An implicit entity identified by its account number (ACC-XXXXX format). Has no explicit storage — its balance and summary are derived from transactions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a valid transaction and receive confirmation in under 1 second
- **SC-002**: Users can retrieve any transaction by ID with a single request
- **SC-003**: 100% of invalid transaction submissions are rejected with clear, actionable error messages identifying every invalid field
- **SC-004**: Users can filter transactions by any combination of account, type, and date range and receive only matching results
- **SC-005**: Account balance accurately reflects the sum of all completed transactions for that account
- **SC-006**: Account summary correctly aggregates deposits, withdrawals, and transaction counts
- **SC-007**: CSV export produces valid, parseable CSV containing all transaction records
- **SC-008**: All API endpoints return appropriate HTTP status codes as specified

## Clarifications

### Session 2026-04-26

- Q: Should transactions default to "pending" or "completed" status? (FR-002 contradicted Assumptions) → A: Default to "completed" — no async processing pipeline needed for homework scope.
- Q: How do different transaction types affect account balance? → A: Standard banking semantics — deposits add to toAccount, withdrawals subtract from fromAccount, transfers do both.

## Assumptions

- Users interact with the API via HTTP clients (curl, Postman, or similar) — no UI is required
- The API runs on a single server instance; horizontal scaling is out of scope
- All transactions are immediately set to "completed" status for balance calculation purposes (no async processing pipeline)
- Currency conversion is out of scope — balances are tracked per-currency
- Authentication and authorization are out of scope for this version
- The API server runs on port 3000 by default
- Data is ephemeral — restarting the server clears all transactions (in-memory storage)
- The ACC-XXXXX format means "ACC-" followed by exactly 5 alphanumeric characters (letters A-Z, a-z and digits 0-9)
