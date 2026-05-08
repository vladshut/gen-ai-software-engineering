# Data Model: Intelligent Customer Support System

## Entities

### Ticket

The core entity representing a customer support request.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | Primary key, auto-generated | uuid4 |
| customer_id | string | Required, non-empty | Caller-provided identifier |
| customer_email | string | Required, valid email format | RFC 5322 validation |
| customer_name | string | Required, non-empty | |
| subject | string | Required, 1-200 chars | |
| description | string | Required, 10-2000 chars | |
| category | enum | One of: account_access, technical_issue, billing_question, feature_request, bug_report, other | Default: null (unclassified) |
| priority | enum | One of: urgent, high, medium, low | Default: medium |
| status | enum | One of: new, in_progress, waiting_customer, resolved, closed | Default: new |
| created_at | datetime | Auto-set on creation, immutable | ISO 8601 UTC |
| updated_at | datetime | Auto-set on creation and update | ISO 8601 UTC |
| resolved_at | datetime | Nullable, set when status → resolved | ISO 8601 UTC |
| assigned_to | string | Nullable | Agent name/ID |
| tags | array[string] | Default: empty array | JSON-serialized in SQLite |
| metadata | object | Optional | Contains source, browser, device_type |

### Metadata (embedded in Ticket)

| Field | Type | Constraints |
|-------|------|-------------|
| source | enum | One of: web_form, email, api, chat, phone. Default: api |
| browser | string | Optional |
| device_type | enum | One of: desktop, mobile, tablet. Optional |

### ClassificationResult (returned by auto-classify, not persisted separately)

| Field | Type | Notes |
|-------|------|-------|
| category | enum | Assigned category |
| priority | enum | Assigned priority |
| confidence | float | 0.0 - 1.0 |
| reasoning | string | Human-readable explanation |
| keywords_found | array[string] | Matched keywords from input |

### ImportSummary (returned by bulk import, not persisted)

| Field | Type | Notes |
|-------|------|-------|
| total | integer | Total records in file |
| successful | integer | Successfully imported count |
| failed | integer | Failed record count |
| errors | array[ImportError] | Per-failure details |

### ImportError (embedded in ImportSummary)

| Field | Type | Notes |
|-------|------|-------|
| row | integer | Row/record number (1-indexed) |
| error | string | Human-readable error message |
| fields | object | Optional: which fields failed validation |

## State Transitions

```
Ticket Status Flow:

  new → in_progress → waiting_customer → in_progress (loop)
                    → resolved → closed
  new → resolved (direct resolution)
  new → closed (direct close)
  Any status → Any status (no strict enforcement, manual override allowed)
```

Note: Status transitions are not strictly enforced — agents can set any valid status. This simplifies the implementation for an educational project.

## Relationships

- A Ticket contains embedded Metadata (1:1, stored as JSON columns)
- ClassificationResult is computed on-demand, not stored as a separate entity (results update the Ticket's category/priority fields)
- ImportSummary is ephemeral (returned in response only)

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'new',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    assigned_to TEXT,
    tags TEXT DEFAULT '[]',
    source TEXT DEFAULT 'api',
    browser TEXT,
    device_type TEXT
);
```

Tags stored as JSON string, metadata fields (source, browser, device_type) stored as flat columns for simplicity.
