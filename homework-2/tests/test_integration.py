import asyncio
import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ticket_lifecycle(client: AsyncClient, sample_ticket_data):
    """End-to-end status transitions: new → in_progress → resolved → closed."""
    # Create ticket
    create_resp = await client.post("/tickets", json=sample_ticket_data)
    assert create_resp.status_code == 201
    created = create_resp.json()
    ticket_id = created["id"]
    assert created["status"] == "new"
    assert created["resolved_at"] is None

    # Transition to in_progress
    update_resp = await client.put(f"/tickets/{ticket_id}", json={"status": "in_progress"})
    assert update_resp.status_code == 200
    in_progress = update_resp.json()
    assert in_progress["status"] == "in_progress"
    assert in_progress["resolved_at"] is None

    # Transition to resolved — resolved_at must be set
    update_resp = await client.put(f"/tickets/{ticket_id}", json={"status": "resolved"})
    assert update_resp.status_code == 200
    resolved = update_resp.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None, "resolved_at must be set when ticket is resolved"

    # Transition to closed
    update_resp = await client.put(f"/tickets/{ticket_id}", json={"status": "closed"})
    assert update_resp.status_code == 200
    closed = update_resp.json()
    assert closed["status"] == "closed"
    # resolved_at should remain set after closing
    assert closed["resolved_at"] is not None

    # Verify final state via GET
    get_resp = await client.get(f"/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    final = get_resp.json()
    assert final["status"] == "closed"
    assert final["resolved_at"] is not None


@pytest.mark.asyncio
async def test_bulk_import_then_classify(client: AsyncClient):
    """Import a 3-row CSV then auto-classify each ticket; assert sensible categories."""
    csv_content = (
        "customer_id,customer_email,customer_name,subject,description,priority\n"
        'CUST-I01,alice@example.com,Alice Smith,Cannot login,I cannot log in to my account at all. '
        "Getting a 403 error every time I try to access my dashboard.,high\n"
        'CUST-I02,bob@example.com,Bob Jones,Billing refund needed,I was charged twice this month '
        "and need a refund for the duplicate billing charge on my account.,high\n"
        'CUST-I03,carol@example.com,Carol White,Suggest dark mode,It would be great if you could '
        "add a dark mode option to reduce eye strain when using the app at night.,low\n"
    )

    file_bytes = csv_content.encode("utf-8")
    import_resp = await client.post(
        "/tickets/import",
        files={"file": ("tickets.csv", io.BytesIO(file_bytes), "text/csv")},
    )
    assert import_resp.status_code == 200
    summary = import_resp.json()
    assert summary["successful"] == 3, f"Expected 3 imported, got: {summary}"

    # Retrieve imported tickets
    list_resp = await client.get("/tickets?page_size=100")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    imported_ids = [t["id"] for t in items]
    assert len(imported_ids) == 3

    # Auto-classify each ticket
    classifications = {}
    for ticket_id in imported_ids:
        classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
        assert classify_resp.status_code == 200
        result = classify_resp.json()
        assert "category" in result
        assert "confidence" in result
        classifications[ticket_id] = result["category"]

    # Map subjects to IDs via the listing so we can assert per-ticket category
    ticket_map = {t["id"]: t for t in items}
    categories_by_subject = {}
    for t_id, t_data in ticket_map.items():
        category = classifications[t_id]
        categories_by_subject[t_data["subject"].lower()] = category

    category_values = list(classifications.values())
    assert "account_access" in category_values, (
        f"Expected account_access classification for login issue, got: {category_values}"
    )
    assert "billing_question" in category_values, (
        f"Expected billing_question classification for billing refund, got: {category_values}"
    )
    assert "feature_request" in category_values, (
        f"Expected feature_request classification for dark mode suggestion, got: {category_values}"
    )


@pytest.mark.asyncio
async def test_concurrent_ticket_creation(client: AsyncClient, sample_ticket_data):
    """Create 25 tickets simultaneously; assert all succeed with unique IDs."""
    tasks = [
        client.post("/tickets", json={**sample_ticket_data, "customer_id": f"CUST-{i:03d}"})
        for i in range(25)
    ]
    responses = await asyncio.gather(*tasks)

    # All requests must return 201
    for i, resp in enumerate(responses):
        assert resp.status_code == 201, (
            f"Request {i} returned {resp.status_code}: {resp.text}"
        )

    # All IDs must be unique
    ids = [resp.json()["id"] for resp in responses]
    assert len(ids) == len(set(ids)), "Duplicate ticket IDs detected in concurrent creation"

    # Total count via GET must reflect all 25 tickets
    list_resp = await client.get("/tickets?page_size=100")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 25, f"Expected total=25, got {list_data['total']}"


@pytest.mark.asyncio
async def test_combined_filtering(client: AsyncClient, sample_ticket_data):
    """Create tickets with varied category/priority; filter by category+priority."""
    tickets_to_create = [
        {"category": "billing_question", "priority": "high",   "customer_id": "CUST-F01"},
        {"category": "billing_question", "priority": "low",    "customer_id": "CUST-F02"},
        {"category": "account_access",   "priority": "high",   "customer_id": "CUST-F03"},
        {"category": "billing_question", "priority": "high",   "customer_id": "CUST-F04"},
        {"category": "feature_request",  "priority": "medium", "customer_id": "CUST-F05"},
    ]

    created_ids = []
    for overrides in tickets_to_create:
        resp = await client.post("/tickets", json={**sample_ticket_data, **overrides})
        assert resp.status_code == 201
        created_ids.append(resp.json()["id"])

    # Filter by both category=billing_question AND priority=high
    filter_resp = await client.get("/tickets?category=billing_question&priority=high&page_size=100")
    assert filter_resp.status_code == 200
    data = filter_resp.json()

    # Only billing_question + high tickets should appear (2 out of 5)
    assert data["total"] == 2, (
        f"Expected 2 matching tickets, got {data['total']}: {data['items']}"
    )
    for item in data["items"]:
        assert item["category"] == "billing_question", (
            f"Unexpected category: {item['category']}"
        )
        assert item["priority"] == "high", (
            f"Unexpected priority: {item['priority']}"
        )


@pytest.mark.asyncio
async def test_import_classify_filter_e2e(client: AsyncClient):
    """Full pipeline: import CSV → auto-classify all → filter by classified category."""
    csv_content = (
        "customer_id,customer_email,customer_name,subject,description,priority\n"
        'CUST-E01,user1@example.com,User One,Login not working,I am completely unable to log in '
        "to my account. The password reset option is not working either and I am locked out.,high\n"
        'CUST-E02,user2@example.com,User Two,Please add dark theme,It would be very helpful to have '
        "a dark theme option for the application interface to reduce eye strain during long sessions.,low\n"
        'CUST-E03,user3@example.com,User Three,Refund for wrong charge,I was charged an incorrect '
        "amount on my last invoice and I need a full refund for the billing error made.,medium\n"
        'CUST-E04,user4@example.com,User Four,App keeps crashing,The application crashes every '
        "time I try to open the settings page. This has been happening since the last update.,high\n"
    )

    # Step 1: Import
    file_bytes = csv_content.encode("utf-8")
    import_resp = await client.post(
        "/tickets/import",
        files={"file": ("e2e_tickets.csv", io.BytesIO(file_bytes), "text/csv")},
    )
    assert import_resp.status_code == 200
    summary = import_resp.json()
    assert summary["successful"] == 4, f"Import failed: {summary}"

    # Step 2: Get all imported tickets
    list_resp = await client.get("/tickets?page_size=100")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 4

    # Step 3: Auto-classify all tickets
    for ticket in items:
        classify_resp = await client.post(f"/tickets/{ticket['id']}/auto-classify")
        assert classify_resp.status_code == 200

    # Step 4: Retrieve updated tickets and check categories were applied
    list_after_resp = await client.get("/tickets?page_size=100")
    assert list_after_resp.status_code == 200
    classified_items = list_after_resp.json()["items"]
    categories_assigned = [t["category"] for t in classified_items if t["category"] is not None]
    assert len(categories_assigned) == 4, (
        f"Expected all 4 tickets to have a category after classification, got: {categories_assigned}"
    )

    # Step 5: Filter by a category that should contain at least one ticket
    # account_access for the login ticket
    filter_resp = await client.get("/tickets?category=account_access&page_size=100")
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()
    assert filtered["total"] >= 1, (
        "Expected at least one account_access ticket after classifying login issue"
    )
    for item in filtered["items"]:
        assert item["category"] == "account_access", (
            f"Filter returned wrong category: {item['category']}"
        )

    # Step 6: Filter by feature_request — should contain dark theme ticket
    filter_resp2 = await client.get("/tickets?category=feature_request&page_size=100")
    assert filter_resp2.status_code == 200
    filtered2 = filter_resp2.json()
    assert filtered2["total"] >= 1, (
        "Expected at least one feature_request ticket after classifying dark theme request"
    )
    for item in filtered2["items"]:
        assert item["category"] == "feature_request", (
            f"Filter returned wrong category: {item['category']}"
        )
