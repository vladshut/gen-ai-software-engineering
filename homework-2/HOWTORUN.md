# How to Run: Customer Support System

## Prerequisites

- Python 3.11 or higher (`python3 --version`)

## 1. Setup

```bash
cd homework-2

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 2. Start the Server

```bash
uvicorn src.main:app --reload --port 8000
```

The API will be available at:
- http://localhost:8000 — health check
- http://localhost:8000/docs — Swagger UI (interactive API docs)

## 3. Test the API

### Create a ticket

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-001",
    "customer_email": "john@example.com",
    "customer_name": "John Doe",
    "subject": "Cannot access my account",
    "description": "Getting error 403 when trying to access my dashboard since yesterday"
  }'
```

### List tickets

```bash
curl http://localhost:8000/tickets
```

### Import from CSV

```bash
curl -X POST http://localhost:8000/tickets/import \
  -F "file=@tests/fixtures/sample_tickets.csv"
```

### Auto-classify a ticket

```bash
# Replace <ticket-id> with an actual UUID from create/list response
curl -X POST http://localhost:8000/tickets/<ticket-id>/auto-classify
```

## 4. Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=term --cov-report=html

# Open coverage report
open htmlcov/index.html
```

Expected result: **56 tests passed, 88.49% coverage**

## 5. Cleanup

```bash
deactivate           # Exit virtual environment
rm -f test_tickets.db  # Remove test database
rm -f tickets.db       # Remove dev database
```
