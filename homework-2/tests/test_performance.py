import time
import asyncio
import io
import csv
import pytest


@pytest.mark.asyncio
async def test_crud_latency(client, sample_ticket_data):
    """Benchmark individual CRUD operations: create, get, update, delete.

    Each operation is timed independently and must complete in under 1 second.
    This verifies that basic database interactions maintain acceptable latency.
    """
    # Create
    start = time.perf_counter()
    response = await client.post("/tickets", json=sample_ticket_data)
    elapsed = time.perf_counter() - start
    assert response.status_code == 201, f"Create failed: {response.status_code}"
    assert elapsed < 1.0, f"Create took {elapsed:.3f}s (limit: 1.0s)"

    ticket_id = response.json()["id"]

    # Get
    start = time.perf_counter()
    response = await client.get(f"/tickets/{ticket_id}")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200, f"Get failed: {response.status_code}"
    assert elapsed < 1.0, f"Get took {elapsed:.3f}s (limit: 1.0s)"

    # Update
    update_payload = {"subject": "Updated subject for performance test"}
    start = time.perf_counter()
    response = await client.put(f"/tickets/{ticket_id}", json=update_payload)
    elapsed = time.perf_counter() - start
    assert response.status_code == 200, f"Update failed: {response.status_code}"
    assert elapsed < 1.0, f"Update took {elapsed:.3f}s (limit: 1.0s)"

    # Delete
    start = time.perf_counter()
    response = await client.delete(f"/tickets/{ticket_id}")
    elapsed = time.perf_counter() - start
    assert response.status_code in (200, 204), f"Delete failed: {response.status_code}"
    assert elapsed < 1.0, f"Delete took {elapsed:.3f}s (limit: 1.0s)"


@pytest.mark.asyncio
async def test_bulk_import_performance(client):
    """Benchmark bulk CSV import of 50 tickets via POST /tickets/import.

    Generates a valid 50-row CSV in memory and uploads it. The entire import
    pipeline (parse, validate, insert) must complete in under 5 seconds.
    """
    # Build a 50-row CSV in memory
    output = io.StringIO()
    fieldnames = [
        "customer_id",
        "customer_email",
        "customer_name",
        "subject",
        "description",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for i in range(1, 51):
        writer.writerow(
            {
                "customer_id": f"CUST-{i:03d}",
                "customer_email": f"user{i}@example.com",
                "customer_name": f"User {i}",
                "subject": f"Bulk import test ticket {i}",
                "description": f"Performance test description for ticket {i}. "
                "Verifying bulk import handles 50 rows efficiently.",
            }
        )

    csv_bytes = output.getvalue().encode("utf-8")
    files = {"file": ("tickets.csv", io.BytesIO(csv_bytes), "text/csv")}

    start = time.perf_counter()
    response = await client.post("/tickets/import", files=files)
    elapsed = time.perf_counter() - start

    assert response.status_code in (200, 201), (
        f"Bulk import failed with status {response.status_code}: {response.text}"
    )
    assert elapsed < 5.0, f"Bulk import of 50 tickets took {elapsed:.3f}s (limit: 5.0s)"


@pytest.mark.asyncio
async def test_classification_performance(client, sample_ticket_data):
    """Benchmark auto-classification of a single ticket.

    Creates a ticket then triggers the auto-classify endpoint. The classification
    call must complete in under 1 second, ensuring the ML/rule-based classifier
    does not introduce unacceptable latency.
    """
    # Create a ticket to classify
    create_response = await client.post("/tickets", json=sample_ticket_data)
    assert create_response.status_code == 201, (
        f"Setup failed: could not create ticket ({create_response.status_code})"
    )
    ticket_id = create_response.json()["id"]

    # Benchmark classification
    start = time.perf_counter()
    response = await client.post(f"/tickets/{ticket_id}/auto-classify")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, (
        f"Classification failed with status {response.status_code}: {response.text}"
    )
    assert elapsed < 1.0, f"Classification took {elapsed:.3f}s (limit: 1.0s)"


@pytest.mark.asyncio
async def test_concurrent_requests(client, sample_ticket_data):
    """Benchmark 20 simultaneous GET /tickets requests using asyncio.gather.

    All requests are fired concurrently to simulate burst traffic. Every request
    must return HTTP 200 and the total wall-clock time for all 20 must be under
    5 seconds.
    """
    # Seed at least one ticket so the list endpoint has data
    create_response = await client.post("/tickets", json=sample_ticket_data)
    assert create_response.status_code == 201, "Setup: could not create seed ticket"

    async def get_tickets():
        return await client.get("/tickets")

    start = time.perf_counter()
    responses = await asyncio.gather(*[get_tickets() for _ in range(20)])
    elapsed = time.perf_counter() - start

    for idx, resp in enumerate(responses):
        assert resp.status_code == 200, (
            f"Request {idx} returned unexpected status {resp.status_code}"
        )

    assert elapsed < 5.0, (
        f"20 concurrent GET /tickets requests took {elapsed:.3f}s (limit: 5.0s)"
    )


@pytest.mark.asyncio
async def test_pagination_performance(client, sample_ticket_data):
    """Benchmark paginated retrieval after inserting 50 tickets.

    Populates the database with 50 tickets, then requests page 3 with a page
    size of 10. The paginated query must complete in under 1 second and must
    return exactly 10 results on the correct page.
    """
    # Insert 50 tickets
    for i in range(50):
        payload = dict(sample_ticket_data)
        payload["customer_id"] = f"PERF-{i:03d}"
        payload["customer_email"] = f"perf{i}@example.com"
        payload["subject"] = f"Pagination performance ticket {i}"
        create_resp = await client.post("/tickets", json=payload)
        assert create_resp.status_code == 201, (
            f"Setup: failed to create ticket {i} ({create_resp.status_code})"
        )

    # Benchmark page 3 retrieval
    start = time.perf_counter()
    response = await client.get("/tickets", params={"page": 3, "page_size": 10})
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, (
        f"Pagination request failed with status {response.status_code}: {response.text}"
    )
    assert elapsed < 1.0, f"Paginated GET took {elapsed:.3f}s (limit: 1.0s)"

    body = response.json()
    # Support both {"items": [...]} and a plain list response shape
    items = body.get("items", body) if isinstance(body, dict) else body
    assert len(items) == 10, (
        f"Expected 10 items on page 3 (page_size=10), got {len(items)}"
    )
