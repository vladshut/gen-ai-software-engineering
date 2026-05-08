import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_classify_account_access(client: AsyncClient, sample_ticket_data):
    """Auto-classify a ticket describing an account access problem."""
    payload = {
        **sample_ticket_data,
        "description": "I can't access my account, password reset not working",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "account_access"


@pytest.mark.asyncio
async def test_classify_billing(client: AsyncClient, sample_ticket_data):
    """Auto-classify a ticket describing a billing / refund request."""
    payload = {
        **sample_ticket_data,
        "description": "I need a refund for my last invoice payment",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "billing_question"


@pytest.mark.asyncio
async def test_classify_technical_issue(client: AsyncClient, sample_ticket_data):
    """Auto-classify a ticket describing an application crash / export error."""
    payload = {
        **sample_ticket_data,
        "description": "The application crashes with an error when I try to export",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "technical_issue"


@pytest.mark.asyncio
async def test_classify_feature_request(client: AsyncClient, sample_ticket_data):
    """Auto-classify a ticket that suggests a new feature (dark mode)."""
    payload = {
        **sample_ticket_data,
        "description": "I would like to suggest adding dark mode to the dashboard",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "feature_request"


@pytest.mark.asyncio
async def test_classify_bug_report(client: AsyncClient, sample_ticket_data):
    """Auto-classify a ticket that reports a reproducible defect."""
    payload = {
        **sample_ticket_data,
        "description": "Found a defect in the login page, here are steps to reproduce the issue",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "bug_report"


@pytest.mark.asyncio
async def test_classify_priority_urgent(client: AsyncClient, sample_ticket_data):
    """Auto-classify a critical production-down / security-breach ticket as urgent."""
    payload = {
        **sample_ticket_data,
        "description": "CRITICAL: production is down and we can't access the system, security breach",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["priority"] == "urgent"


@pytest.mark.asyncio
async def test_classify_vague_text(client: AsyncClient, sample_ticket_data):
    """Vague ticket description should be classified as 'other' with medium priority and low confidence."""
    payload = {
        **sample_ticket_data,
        "description": "Need help with something please",
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert data["category"] == "other"
    assert data["priority"] == "medium"
    assert data["confidence"] < 0.5


@pytest.mark.asyncio
async def test_classify_confidence_range(client: AsyncClient, sample_ticket_data):
    """Confidence score returned by auto-classify must be between 0 and 1 (inclusive)."""
    create_resp = await client.post("/tickets", json=sample_ticket_data)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200
    data = classify_resp.json()
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_classify_auto_on_creation(client: AsyncClient, sample_ticket_data):
    """Creating a ticket with auto_classify=True should return a response with category already set."""
    payload = {
        **sample_ticket_data,
        "description": "I need a refund for my last invoice payment",
        "auto_classify": True,
    }
    create_resp = await client.post("/tickets", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data.get("category") is not None


@pytest.mark.asyncio
async def test_classify_manual_override(client: AsyncClient, sample_ticket_data):
    """After auto-classify, a manual PUT to change category should persist."""
    create_resp = await client.post("/tickets", json=sample_ticket_data)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    classify_resp = await client.post(f"/tickets/{ticket_id}/auto-classify")
    assert classify_resp.status_code == 200

    update_resp = await client.put(
        f"/tickets/{ticket_id}",
        json={"category": "other"},
    )
    assert update_resp.status_code == 200

    get_resp = await client.get(f"/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["category"] == "other"
