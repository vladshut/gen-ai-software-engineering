# API Contract: Customer Support System

Base URL: `http://localhost:8000`

## Endpoints

### Tickets CRUD

#### POST /tickets
Create a new support ticket.

**Request Body**:
```json
{
  "customer_id": "CUST-001",
  "customer_email": "john@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot access my account",
  "description": "I've been unable to log in since yesterday. Getting a 403 error.",
  "category": "account_access",
  "priority": "high",
  "tags": ["login", "urgent"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 120",
    "device_type": "desktop"
  },
  "auto_classify": false
}
```
- `category`, `priority`, `tags`, `metadata`, `auto_classify` are optional
- If `auto_classify: true`, classification runs automatically on creation

**Response**: `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "CUST-001",
  "customer_email": "john@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot access my account",
  "description": "I've been unable to log in since yesterday. Getting a 403 error.",
  "category": "account_access",
  "priority": "high",
  "status": "new",
  "created_at": "2026-05-08T10:30:00Z",
  "updated_at": "2026-05-08T10:30:00Z",
  "resolved_at": null,
  "assigned_to": null,
  "tags": ["login", "urgent"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome 120",
    "device_type": "desktop"
  }
}
```

**Errors**: `400` validation error, `422` unprocessable entity

---

#### GET /tickets
List tickets with filtering and pagination.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number (1-indexed) |
| page_size | int | 20 | Items per page (max 100) |
| category | string | — | Filter by category enum |
| priority | string | — | Filter by priority enum |
| status | string | — | Filter by status enum |

**Response**: `200 OK`
```json
{
  "page": 1,
  "page_size": 20,
  "total": 150,
  "items": [ { ... ticket objects ... } ]
}
```

---

#### GET /tickets/{id}
Get a specific ticket by UUID.

**Response**: `200 OK` with ticket object
**Errors**: `404` ticket not found

---

#### PUT /tickets/{id}
Update an existing ticket. Partial updates supported.

**Request Body** (all fields optional):
```json
{
  "status": "in_progress",
  "assigned_to": "agent-smith",
  "category": "technical_issue",
  "priority": "urgent",
  "tags": ["escalated"]
}
```

**Response**: `200 OK` with updated ticket
**Errors**: `400` validation error, `404` not found

---

#### DELETE /tickets/{id}
Delete a ticket.

**Response**: `200 OK`
```json
{ "detail": "Ticket deleted successfully" }
```
**Errors**: `404` not found

---

### Bulk Import

#### POST /tickets/import
Import tickets from a file (CSV, JSON, or XML).

**Request**: `multipart/form-data`
- `file`: The upload file (required)

Format detected from file extension: `.csv`, `.json`, `.xml`

**Response**: `200 OK`
```json
{
  "total": 50,
  "successful": 47,
  "failed": 3,
  "errors": [
    { "row": 5, "error": "Invalid email format", "fields": { "customer_email": "not-an-email" } },
    { "row": 12, "error": "Subject exceeds 200 characters", "fields": { "subject": "..." } },
    { "row": 33, "error": "Missing required field: description", "fields": {} }
  ]
}
```

**Errors**: `400` malformed file (unparseable)

---

### Auto-Classification

#### POST /tickets/{id}/auto-classify
Run auto-classification on an existing ticket.

**Response**: `200 OK`
```json
{
  "category": "account_access",
  "priority": "urgent",
  "confidence": 0.85,
  "reasoning": "Matched keywords in subject and description indicating account access issues with high urgency",
  "keywords_found": ["can't access", "account", "error 403"]
}
```

The ticket's `category` and `priority` fields are updated with the classification results.

**Errors**: `404` ticket not found
