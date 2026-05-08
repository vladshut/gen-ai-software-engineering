import json

import pytest
from httpx import AsyncClient


VALID_TICKETS = [
    {
        "customer_id": "CUST-001",
        "customer_email": "alice@example.com",
        "customer_name": "Alice Smith",
        "subject": "Login issue",
        "description": "I cannot log into my account since yesterday morning.",
    },
    {
        "customer_id": "CUST-002",
        "customer_email": "bob@example.com",
        "customer_name": "Bob Jones",
        "subject": "Billing question",
        "description": "I was charged twice for my subscription last month.",
    },
    {
        "customer_id": "CUST-003",
        "customer_email": "carol@example.com",
        "customer_name": "Carol White",
        "subject": "Feature request",
        "description": "Please add dark mode support to the mobile application.",
    },
]


@pytest.mark.asyncio
async def test_import_json_valid(client: AsyncClient):
    """Upload a valid JSON array of 3 tickets; expect 200, successful=3, failed=0."""
    json_bytes = json.dumps(VALID_TICKETS).encode()
    response = await client.post(
        "/tickets/import",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["successful"] == 3
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_json_invalid_fields(client: AsyncClient):
    """Upload a JSON array where one ticket has an invalid email; expect that record to fail."""
    tickets = [
        {
            "customer_id": "CUST-010",
            "customer_email": "not-a-valid-email",
            "customer_name": "Invalid User",
            "subject": "Bad email ticket",
            "description": "This ticket has an invalid email address field.",
        }
    ]
    json_bytes = json.dumps(tickets).encode()
    response = await client.post(
        "/tickets/import",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    data = response.json()
    assert data["failed"] >= 1
    assert len(data["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_json_empty_array(client: AsyncClient):
    """Upload an empty JSON array; expect 200 with total=0, successful=0, failed=0."""
    json_bytes = json.dumps([]).encode()
    response = await client.post(
        "/tickets/import",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["successful"] == 0
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_json_malformed(client: AsyncClient):
    """Upload a file with invalid JSON syntax; expect 400."""
    malformed_bytes = b'[{"customer_id": "CUST-999", "customer_email": "x@x.com"'  # missing closing bracket
    response = await client.post(
        "/tickets/import",
        files={"file": ("test.json", malformed_bytes, "application/json")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_json_nested_objects(client: AsyncClient):
    """Upload tickets that include nested metadata objects; expect them to import successfully with metadata preserved."""
    tickets_with_metadata = [
        {
            "customer_id": "CUST-101",
            "customer_email": "dave@example.com",
            "customer_name": "Dave Brown",
            "subject": "App crash on startup",
            "description": "The application crashes immediately when I try to open it on Windows.",
            "metadata": {
                "source": "web_form",
                "browser": "Firefox 121",
                "device_type": "desktop",
            },
        },
        {
            "customer_id": "CUST-102",
            "customer_email": "eve@example.com",
            "customer_name": "Eve Green",
            "subject": "Slow performance noticed",
            "description": "Pages are loading very slowly compared to last week on my device.",
            "metadata": {
                "source": "chat",
                "browser": None,
                "device_type": "mobile",
            },
        },
    ]
    json_bytes = json.dumps(tickets_with_metadata).encode()
    response = await client.post(
        "/tickets/import",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["successful"] == 2
    assert data["failed"] == 0
