import io
import pytest


# ---------------------------------------------------------------------------
# Helper: build a minimal valid CSV as bytes
# ---------------------------------------------------------------------------
HEADERS = "customer_id,customer_email,customer_name,subject,description,category,priority\n"


def _csv_bytes(rows: list[str]) -> bytes:
    return (HEADERS + "\n".join(rows)).encode("utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_csv_valid(client, fixtures_path):
    """Upload a valid CSV with 5 rows; expect 200, successful=5, failed=0."""
    rows = [
        f"CUST-{i:03d},user{i}@example.com,User {i},Subject {i},This is a valid description for ticket {i},billing_question,medium"
        for i in range(1, 6)
    ]
    csv_bytes = _csv_bytes(rows)

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["successful"] == 5
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_csv_missing_required_fields(client, fixtures_path):
    """Row missing customer_email should be reported as a failure with row info."""
    rows = [
        # valid row
        "CUST-001,valid@example.com,Valid User,Subject 1,This is a valid description for testing,billing_question,medium",
        # invalid row: empty customer_email
        "CUST-002,,Missing Email,Subject 2,This is a valid description for testing,billing_question,medium",
    ]
    csv_bytes = _csv_bytes(rows)

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["failed"] == 1

    # The failure record must reference the problematic row (row 2, i.e. index 1)
    failures = data.get("errors") or data.get("failures") or []
    assert len(failures) == 1
    failure = failures[0]
    # Row number should be present (1-based row 2 or 0-based index 1)
    row_ref = failure.get("row") or failure.get("row_number") or failure.get("line")
    assert row_ref is not None


@pytest.mark.asyncio
async def test_import_csv_invalid_email(client, fixtures_path):
    """Row with a malformed email should be reported as a failure."""
    rows = [
        "CUST-001,not-an-email,Bad Email User,Subject 1,Description 1,billing,medium",
    ]
    csv_bytes = _csv_bytes(rows)

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["failed"] == 1
    assert data["successful"] == 0

    failures = data.get("errors") or data.get("failures") or []
    assert len(failures) == 1


@pytest.mark.asyncio
async def test_import_csv_extra_columns(client, fixtures_path):
    """Extra columns not in the ticket model should be ignored; valid rows import."""
    headers_with_extra = (
        "customer_id,customer_email,customer_name,subject,description,"
        "category,priority,extra_field,another_extra\n"
    )
    rows = [
        "CUST-001,user1@example.com,User One,Sub 1,This is a valid description for testing,billing_question,medium,foo,bar",
        "CUST-002,user2@example.com,User Two,Sub 2,This is another valid description for testing,technical_issue,high,baz,qux",
    ]
    csv_bytes = (headers_with_extra + "\n".join(rows)).encode("utf-8")

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["successful"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_csv_empty_file(client, fixtures_path):
    """CSV with only headers and no data rows should return total=0, successful=0, failed=0."""
    csv_bytes = HEADERS.encode("utf-8")

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    total = data.get("total") or (data.get("successful", 0) + data.get("failed", 0))
    assert total == 0
    assert data["successful"] == 0
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_csv_malformed(client, fixtures_path):
    """Completely non-CSV binary content should return 400."""
    garbage = bytes(range(256)) * 4  # arbitrary binary garbage

    response = await client.post(
        "/tickets/import",
        files={"file": ("test.csv", io.BytesIO(garbage), "text/csv")},
    )

    assert response.status_code == 400
