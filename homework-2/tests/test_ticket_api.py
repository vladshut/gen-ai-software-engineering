import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ticket_valid(client: AsyncClient, sample_ticket_data):
    """POST /tickets with valid data should return 201 with id, status=new, and timestamps."""
    response = await client.post("/tickets", json=sample_ticket_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "new"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_ticket_invalid_email(client: AsyncClient, sample_ticket_data):
    """POST /tickets with invalid email should return 422."""
    payload = {**sample_ticket_data, "customer_email": "not-a-valid-email"}
    response = await client.post("/tickets", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_missing_required(client: AsyncClient):
    """POST /tickets with empty body should return 422."""
    response = await client.post("/tickets", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_ticket_by_id(client: AsyncClient, sample_ticket_data):
    """Create a ticket, then GET /tickets/{id} should return 200 with correct data."""
    create_response = await client.post("/tickets", json=sample_ticket_data)
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    get_response = await client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == ticket_id
    assert data["customer_id"] == sample_ticket_data["customer_id"]
    assert data["customer_email"] == sample_ticket_data["customer_email"]
    assert data["subject"] == sample_ticket_data["subject"]


@pytest.mark.asyncio
async def test_get_ticket_not_found(client: AsyncClient):
    """GET /tickets/nonexistent-uuid should return 404."""
    response = await client.get("/tickets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_tickets(client: AsyncClient, sample_ticket_data):
    """Create 3 tickets, GET /tickets should return 200 with pagination fields."""
    for _ in range(3):
        await client.post("/tickets", json=sample_ticket_data)

    response = await client.get("/tickets")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] >= 3
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_list_tickets_filter_by_status(client: AsyncClient, sample_ticket_data):
    """Create tickets with different statuses; GET /tickets?status=new should filter correctly."""
    # Create a ticket with default status (new)
    create_resp = await client.post("/tickets", json=sample_ticket_data)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    # Update one ticket to in_progress
    await client.put(f"/tickets/{ticket_id}", json={"status": "in_progress"})

    # Create another ticket that stays new
    await client.post("/tickets", json=sample_ticket_data)

    response = await client.get("/tickets?status=new")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for item in data["items"]:
        assert item["status"] == "new"


@pytest.mark.asyncio
async def test_list_tickets_pagination(client: AsyncClient, sample_ticket_data):
    """Create 25 tickets, GET /tickets?page=2&page_size=10 should return the correct page."""
    for _ in range(25):
        await client.post("/tickets", json=sample_ticket_data)

    response = await client.get("/tickets?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert data["total"] >= 25
    assert len(data["items"]) == 10


@pytest.mark.asyncio
async def test_update_ticket(client: AsyncClient, sample_ticket_data):
    """Create a ticket, PUT /tickets/{id} should update status and assigned_to, and change updated_at."""
    create_response = await client.post("/tickets", json=sample_ticket_data)
    assert create_response.status_code == 201
    created = create_response.json()
    ticket_id = created["id"]
    original_updated_at = created["updated_at"]

    update_payload = {"status": "in_progress", "assigned_to": "agent-1"}
    update_response = await client.put(f"/tickets/{ticket_id}", json=update_payload)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "in_progress"
    assert updated["assigned_to"] == "agent-1"
    assert updated["updated_at"] != original_updated_at


@pytest.mark.asyncio
async def test_update_ticket_not_found(client: AsyncClient):
    """PUT /tickets/nonexistent-uuid should return 404."""
    response = await client.put(
        "/tickets/00000000-0000-0000-0000-000000000000",
        json={"status": "in_progress"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_ticket(client: AsyncClient, sample_ticket_data):
    """Create a ticket, DELETE /tickets/{id} should return 200, then GET should return 404."""
    create_response = await client.post("/tickets", json=sample_ticket_data)
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    delete_response = await client.delete(f"/tickets/{ticket_id}")
    assert delete_response.status_code == 200

    get_response = await client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 404
