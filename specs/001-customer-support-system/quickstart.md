# Quickstart: Customer Support System

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
cd homework-2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing)
pip install -r requirements-dev.txt
```

## Run the Server

```bash
cd homework-2
uvicorn src.main:app --reload --port 8000
```

Server starts at `http://localhost:8000`
API docs at `http://localhost:8000/docs` (Swagger UI)

## Quick Test

```bash
# Create a ticket
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-001",
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "subject": "Cannot login",
    "description": "Getting error 403 when trying to access my account"
  }'

# List tickets
curl http://localhost:8000/tickets

# Auto-classify a ticket (replace {id} with actual UUID)
curl -X POST http://localhost:8000/tickets/{id}/auto-classify

# Import from CSV
curl -X POST http://localhost:8000/tickets/import \
  -F "file=@tests/fixtures/sample_tickets.csv"
```

## Run Tests

```bash
cd homework-2

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_ticket_api.py -v
```
