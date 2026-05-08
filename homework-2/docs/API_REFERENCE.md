# API Reference

Customer Support System — v1.0.0

Base URL: `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`
OpenAPI schema: `http://localhost:8000/openapi.json`

---

## Table of Contents

1. [Endpoints](#endpoints)
   - [POST /tickets](#post-tickets)
   - [GET /tickets](#get-tickets)
   - [GET /tickets/{id}](#get-ticketsid)
   - [PUT /tickets/{id}](#put-ticketsid)
   - [DELETE /tickets/{id}](#delete-ticketsid)
   - [POST /tickets/import](#post-ticketsimport)
   - [POST /tickets/{id}/auto-classify](#post-ticketsidauto-classify)
2. [Data Models](#data-models)
3. [Enum Values](#enum-values)
4. [Error Response Format](#error-response-format)

---

## Endpoints

### POST /tickets

Create a new support ticket. Optionally triggers automatic AI classification on creation.

**Request Body** (JSON, `Content-Type: application/json`)

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `customer_id` | string | Yes | min length 1 | Unique identifier for the customer |
| `customer_email` | string (email) | Yes | valid email | Customer email address |
| `customer_name` | string | Yes | min length 1 | Customer display name |
| `subject` | string | Yes | 1–200 characters | Short summary of the issue |
| `description` | string | Yes | 10–2000 characters | Full description of the issue |
| `category` | string (enum) | No | see [Category](#category) | Ticket category |
| `priority` | string (enum) | No | default `medium` | Ticket priority |
| `tags` | array of strings | No | default `[]` | Arbitrary labels |
| `metadata` | object | No | see [TicketMetadata](#ticketmetadata) | Channel and device context |
| `auto_classify` | boolean | No | default `false` | Run AI classification on creation |

**Full request body example**

```json
{
  "customer_id": "cust-001",
  "customer_email": "alice@example.com",
  "customer_name": "Alice Smith",
  "subject": "Cannot log in to my account",
  "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
  "category": "account_access",
  "priority": "high",
  "tags": ["login", "password-reset"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 124",
    "device_type": "desktop"
  },
  "auto_classify": false
}
```

**cURL example**

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "customer_email": "alice@example.com",
    "customer_name": "Alice Smith",
    "subject": "Cannot log in to my account",
    "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
    "category": "account_access",
    "priority": "high",
    "tags": ["login", "password-reset"],
    "metadata": {
      "source": "web_form",
      "browser": "Chrome 124",
      "device_type": "desktop"
    },
    "auto_classify": false
  }'
```

**Success response — 201 Created**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "customer_id": "cust-001",
  "customer_email": "alice@example.com",
  "customer_name": "Alice Smith",
  "subject": "Cannot log in to my account",
  "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
  "category": "account_access",
  "priority": "high",
  "status": "new",
  "created_at": "2026-05-08T10:00:00.000Z",
  "updated_at": "2026-05-08T10:00:00.000Z",
  "resolved_at": null,
  "assigned_to": null,
  "tags": ["login", "password-reset"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 124",
    "device_type": "desktop"
  }
}
```

**Error response — 422 Unprocessable Entity** (validation failure)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "customer_email"],
      "msg": "Field required",
      "input": {
        "customer_id": "cust-001",
        "customer_name": "Alice Smith",
        "subject": "Cannot log in",
        "description": "I cannot log in to my account at all."
      },
      "url": "https://errors.pydantic.dev/2.x/v/missing"
    }
  ]
}
```

---

### GET /tickets

List tickets with optional filtering and pagination.

**Query Parameters**

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `page` | integer | `1` | min 1 | Page number (1-based) |
| `page_size` | integer | `20` | 1–100 | Number of items per page |
| `category` | string (enum) | — | see [Category](#category) | Filter by category |
| `priority` | string (enum) | — | see [Priority](#priority) | Filter by priority |
| `status` | string (enum) | — | see [Status](#status) | Filter by status |

**cURL example**

```bash
curl "http://localhost:8000/tickets?page=2&page_size=5&status=new&priority=high"
```

**Success response — 200 OK**

```json
{
  "page": 2,
  "page_size": 5,
  "total": 42,
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "customer_id": "cust-001",
      "customer_email": "alice@example.com",
      "customer_name": "Alice Smith",
      "subject": "Cannot log in to my account",
      "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
      "category": "account_access",
      "priority": "high",
      "status": "new",
      "created_at": "2026-05-08T10:00:00.000Z",
      "updated_at": "2026-05-08T10:00:00.000Z",
      "resolved_at": null,
      "assigned_to": null,
      "tags": ["login", "password-reset"],
      "metadata": {
        "source": "web_form",
        "browser": "Chrome 124",
        "device_type": "desktop"
      }
    }
  ]
}
```

**Error response — 422 Unprocessable Entity** (invalid query parameter value)

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["query", "status"],
      "msg": "Input should be 'new', 'in_progress', 'waiting_customer', 'resolved' or 'closed'",
      "input": "unknown_status",
      "url": "https://errors.pydantic.dev/2.x/v/enum"
    }
  ]
}
```

---

### GET /tickets/{id}

Retrieve a single ticket by its UUID.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | string (UUID) | Ticket identifier |

**cURL example**

```bash
curl http://localhost:8000/tickets/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Success response — 200 OK**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "customer_id": "cust-001",
  "customer_email": "alice@example.com",
  "customer_name": "Alice Smith",
  "subject": "Cannot log in to my account",
  "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
  "category": "account_access",
  "priority": "high",
  "status": "in_progress",
  "created_at": "2026-05-08T10:00:00.000Z",
  "updated_at": "2026-05-08T11:30:00.000Z",
  "resolved_at": null,
  "assigned_to": "agent-007",
  "tags": ["login", "password-reset"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 124",
    "device_type": "desktop"
  }
}
```

**Error response — 404 Not Found**

```json
{
  "detail": "Ticket not found"
}
```

---

### PUT /tickets/{id}

Update an existing ticket. All fields are optional — only supplied fields are changed.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | string (UUID) | Ticket identifier |

**Request Body** (JSON, `Content-Type: application/json`)

| Field | Type | Constraints | Description |
|---|---|---|---|
| `customer_id` | string | optional | Updated customer ID |
| `customer_email` | string (email) | optional | Updated email address |
| `customer_name` | string | optional | Updated customer name |
| `subject` | string | optional, max 200 chars | Updated subject |
| `description` | string | optional, 10–2000 chars | Updated description |
| `category` | string (enum) | optional | Updated category |
| `priority` | string (enum) | optional | Updated priority |
| `status` | string (enum) | optional | Updated status |
| `assigned_to` | string | optional | Agent or team assignment |
| `tags` | array of strings | optional | Replaces existing tags |
| `metadata` | object | optional | Updated channel/device context |

**Partial update request example**

```json
{
  "status": "in_progress",
  "assigned_to": "agent-007",
  "priority": "urgent"
}
```

**cURL example**

```bash
curl -X PUT http://localhost:8000/tickets/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "assigned_to": "agent-007",
    "priority": "urgent"
  }'
```

**Success response — 200 OK**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "customer_id": "cust-001",
  "customer_email": "alice@example.com",
  "customer_name": "Alice Smith",
  "subject": "Cannot log in to my account",
  "description": "I have been trying to log in for the past two hours but keep getting an invalid credentials error even though I just reset my password.",
  "category": "account_access",
  "priority": "urgent",
  "status": "in_progress",
  "created_at": "2026-05-08T10:00:00.000Z",
  "updated_at": "2026-05-08T11:45:00.000Z",
  "resolved_at": null,
  "assigned_to": "agent-007",
  "tags": ["login", "password-reset"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 124",
    "device_type": "desktop"
  }
}
```

**Error response — 404 Not Found**

```json
{
  "detail": "Ticket not found"
}
```

---

### DELETE /tickets/{id}

Permanently delete a ticket.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | string (UUID) | Ticket identifier |

**cURL example**

```bash
curl -X DELETE http://localhost:8000/tickets/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Success response — 200 OK**

```json
{
  "detail": "Ticket deleted successfully"
}
```

**Error response — 404 Not Found**

```json
{
  "detail": "Ticket not found"
}
```

---

### POST /tickets/import

Bulk import tickets from a file. Supported formats: **CSV**, **JSON**, **XML**.

The endpoint processes every record in the file independently. Records that fail validation are recorded in `errors`; successfully created records increment `successful`. The overall HTTP response is always `200 OK` — per-row failures do not change the status code.

**Request** (`Content-Type: multipart/form-data`)

| Field | Type | Description |
|---|---|---|
| `file` | file (binary) | CSV, JSON, or XML file containing ticket records |

**CSV format** — one ticket per row, header row required.

Expected columns match `TicketCreate` fields. Metadata sub-fields use the prefix `metadata_` (e.g. `metadata_source`, `metadata_browser`, `metadata_device_type`). The `tags` column accepts either a JSON array string or a comma-separated list.

```
customer_id,customer_email,customer_name,subject,description,category,priority,tags,metadata_source,metadata_browser,metadata_device_type
cust-001,alice@example.com,Alice Smith,Cannot log in,I have been trying to log in for two hours and keep getting errors.,account_access,high,"[""login"",""password-reset""]",web_form,Chrome 124,desktop
cust-002,bob@example.com,Bob Jones,Billing discrepancy,My invoice shows a charge I do not recognize from last month.,billing_question,medium,billing,email,,
```

**JSON format** — top-level array of ticket objects.

```json
[
  {
    "customer_id": "cust-001",
    "customer_email": "alice@example.com",
    "customer_name": "Alice Smith",
    "subject": "Cannot log in to my account",
    "description": "I have been trying to log in for two hours and keep getting an invalid credentials error.",
    "category": "account_access",
    "priority": "high",
    "tags": ["login", "password-reset"],
    "metadata": {
      "source": "web_form",
      "browser": "Chrome 124",
      "device_type": "desktop"
    }
  }
]
```

**XML format** — `<tickets>` root element containing `<ticket>` children. Tags use nested `<tag>` elements; metadata uses nested sub-elements.

```xml
<tickets>
  <ticket>
    <customer_id>cust-001</customer_id>
    <customer_email>alice@example.com</customer_email>
    <customer_name>Alice Smith</customer_name>
    <subject>Cannot log in to my account</subject>
    <description>I have been trying to log in for two hours and keep getting an invalid credentials error.</description>
    <category>account_access</category>
    <priority>high</priority>
    <tags>
      <tag>login</tag>
      <tag>password-reset</tag>
    </tags>
    <metadata>
      <source>web_form</source>
      <browser>Chrome 124</browser>
      <device_type>desktop</device_type>
    </metadata>
  </ticket>
</tickets>
```

**cURL example**

```bash
curl -X POST http://localhost:8000/tickets/import \
  -F "file=@tickets.csv"
```

```bash
curl -X POST http://localhost:8000/tickets/import \
  -F "file=@tickets.json"
```

**Success response — 200 OK**

```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "errors": [
    {
      "row": 3,
      "error": "Value error, description must be at least 10 characters",
      "fields": {}
    },
    {
      "row": 7,
      "error": "Field required",
      "fields": {}
    }
  ]
}
```

An import with zero failures returns:

```json
{
  "total": 10,
  "successful": 10,
  "failed": 0,
  "errors": []
}
```

**Error response — 400 Bad Request** (malformed or unsupported file)

Returned when the file cannot be parsed at all, for example when the content is not valid JSON or the file extension is not recognised.

```json
{
  "detail": "JSON parse error: Expecting value: line 1 column 1 (char 0)"
}
```

```json
{
  "detail": "Unsupported file format"
}
```

---

### POST /tickets/{id}/auto-classify

Run AI classification on an existing ticket. The service analyses the ticket's `subject` and `description` and returns a suggested `category`, `priority`, confidence score, human-readable reasoning, and the keywords that influenced the decision.

> Note: this endpoint does **not** mutate the ticket. Use `PUT /tickets/{id}` to apply the returned classification.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | string (UUID) | Ticket identifier |

**cURL example**

```bash
curl -X POST http://localhost:8000/tickets/3fa85f64-5717-4562-b3fc-2c963f66afa6/auto-classify
```

**Success response — 200 OK**

```json
{
  "category": "account_access",
  "priority": "high",
  "confidence": 0.92,
  "reasoning": "The subject and description both reference login failure and credential errors, which are strong indicators of an account access issue. The urgency expressed by the customer ('two hours', 'keep getting') suggests high priority.",
  "keywords_found": ["log in", "invalid credentials", "password", "reset"]
}
```

**Error response — 404 Not Found**

```json
{
  "detail": "Ticket not found"
}
```

---

## Data Models

### Ticket

The full ticket object returned by all ticket endpoints.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | string (UUID) | No | Unique ticket identifier |
| `customer_id` | string | No | Customer identifier |
| `customer_email` | string | No | Customer email address |
| `customer_name` | string | No | Customer display name |
| `subject` | string | No | Short summary of the issue (max 200 chars) |
| `description` | string | No | Full issue description (10–2000 chars) |
| `category` | string (enum) | Yes | Ticket category; `null` if not yet set |
| `priority` | string (enum) | No | Ticket priority |
| `status` | string (enum) | No | Current ticket status |
| `created_at` | string (ISO 8601) | No | Creation timestamp |
| `updated_at` | string (ISO 8601) | No | Last update timestamp |
| `resolved_at` | string (ISO 8601) | Yes | Resolution timestamp; `null` if unresolved |
| `assigned_to` | string | Yes | Assigned agent or team; `null` if unassigned |
| `tags` | array of strings | No | Arbitrary labels |
| `metadata` | object (TicketMetadata) | No | Channel and device context |

### TicketMetadata

Embedded in every Ticket response.

| Field | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `source` | string (enum) | Yes | `"api"` | Channel through which the ticket was submitted |
| `browser` | string | Yes | `null` | Browser identifier (free-form string) |
| `device_type` | string (enum) | Yes | `null` | Device class |

### ClassificationResult

Returned by `POST /tickets/{id}/auto-classify`.

| Field | Type | Description |
|---|---|---|
| `category` | string (enum) | Suggested category |
| `priority` | string (enum) | Suggested priority |
| `confidence` | float | Confidence score in the range [0, 1] |
| `reasoning` | string | Human-readable explanation of the classification |
| `keywords_found` | array of strings | Keywords from the ticket text that influenced the result |

### ImportSummary

Returned by `POST /tickets/import`.

| Field | Type | Description |
|---|---|---|
| `total` | integer | Total number of records found in the file |
| `successful` | integer | Number of tickets successfully created |
| `failed` | integer | Number of records that could not be created |
| `errors` | array of ImportError | Per-row error details |

### ImportError

Embedded in `ImportSummary.errors`.

| Field | Type | Description |
|---|---|---|
| `row` | integer | 1-based row/record index within the file |
| `error` | string | Error message describing why the row failed |
| `fields` | object (string → string) | Map of field names to per-field error messages (may be empty) |

---

## Enum Values

### Category

| Value | Description |
|---|---|
| `account_access` | Login, password, or account management issues |
| `technical_issue` | General technical problems |
| `billing_question` | Invoice, payment, or subscription queries |
| `feature_request` | Requests for new or changed functionality |
| `bug_report` | Confirmed or suspected software bugs |
| `other` | Issues that do not fit another category |

### Priority

| Value | Description |
|---|---|
| `urgent` | Requires immediate attention |
| `high` | Should be addressed soon |
| `medium` | Normal handling (default) |
| `low` | Can be deferred |

### Status

| Value | Description |
|---|---|
| `new` | Newly created, not yet worked on (default) |
| `in_progress` | Actively being handled |
| `waiting_customer` | Awaiting a response from the customer |
| `resolved` | Issue has been resolved |
| `closed` | Ticket is closed and archived |

### Source

Used in `TicketMetadata.source`.

| Value | Description |
|---|---|
| `web_form` | Submitted via web form |
| `email` | Submitted via email |
| `api` | Submitted via API (default) |
| `chat` | Submitted via live chat |
| `phone` | Submitted via phone call |

### DeviceType

Used in `TicketMetadata.device_type`.

| Value | Description |
|---|---|
| `desktop` | Desktop or laptop computer |
| `mobile` | Mobile phone |
| `tablet` | Tablet device |

---

## Error Response Format

### Validation errors (422)

FastAPI returns a `422 Unprocessable Entity` status with a structured body whenever request data fails Pydantic validation. The `detail` field is an array — there is one entry per failing field.

```json
{
  "detail": [
    {
      "type": "<pydantic error type>",
      "loc": ["<location>", "<field name>"],
      "msg": "<human-readable message>",
      "input": "<value that was supplied>",
      "url": "https://errors.pydantic.dev/2.x/v/<type>"
    }
  ]
}
```

| Field | Description |
|---|---|
| `type` | Machine-readable error code (e.g. `missing`, `string_too_short`, `enum`) |
| `loc` | Array path to the invalid field. First element is `"body"` or `"query"`. |
| `msg` | Human-readable error description |
| `input` | The value that triggered the error |
| `url` | Link to Pydantic documentation for this error type |

### HTTP errors (400, 404)

All other errors return a plain object with a single `detail` string.

```json
{
  "detail": "<error message>"
}
```

Common HTTP error codes:

| Status | Trigger |
|---|---|
| `400 Bad Request` | Malformed or unsupported import file |
| `404 Not Found` | Ticket ID does not exist |
| `422 Unprocessable Entity` | Request body or query parameter validation failure |
