import pytest
from httpx import AsyncClient


VALID_XML_3_TICKETS = """\
<?xml version="1.0" encoding="UTF-8"?>
<tickets>
  <ticket>
    <customer_id>CUST-001</customer_id>
    <customer_email>alice@example.com</customer_email>
    <customer_name>Alice Smith</customer_name>
    <subject>Login issue</subject>
    <description>I cannot log in to my account since the last update was applied.</description>
  </ticket>
  <ticket>
    <customer_id>CUST-002</customer_id>
    <customer_email>bob@example.com</customer_email>
    <customer_name>Bob Jones</customer_name>
    <subject>Payment failed</subject>
    <description>My payment keeps failing at checkout even with a valid card on file.</description>
  </ticket>
  <ticket>
    <customer_id>CUST-003</customer_id>
    <customer_email>carol@example.com</customer_email>
    <customer_name>Carol White</customer_name>
    <subject>Missing order</subject>
    <description>I placed an order three days ago but it has not shipped yet.</description>
  </ticket>
</tickets>
"""

MISSING_DESCRIPTION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<tickets>
  <ticket>
    <customer_id>CUST-010</customer_id>
    <customer_email>dave@example.com</customer_email>
    <customer_name>Dave Brown</customer_name>
    <subject>No description ticket</subject>
  </ticket>
</tickets>
"""

INVALID_EMAIL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<tickets>
  <ticket>
    <customer_id>CUST-020</customer_id>
    <customer_email>not-a-valid-email</customer_email>
    <customer_name>Eve Davis</customer_name>
    <subject>Bad email ticket</subject>
    <description>This ticket has an invalid customer email address supplied.</description>
  </ticket>
</tickets>
"""

EMPTY_TICKETS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<tickets></tickets>
"""

MALFORMED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<tickets>
  <ticket>
    <customer_id>CUST-099</customer_id>
    <customer_email>frank@example.com</customer_email>
    <subject>Unclosed tag
  </ticket>
"""


def _xml_upload(xml_str: str) -> dict:
    """Build the multipart files dict for a POST /tickets/import request."""
    return {"file": ("test.xml", xml_str.encode("utf-8"), "application/xml")}


@pytest.mark.asyncio
async def test_import_xml_valid(client: AsyncClient):
    """Upload valid XML with 3 tickets — expect 200, successful=3, failed=0."""
    response = await client.post(
        "/tickets/import",
        files=_xml_upload(VALID_XML_3_TICKETS),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["successful"] == 3
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_xml_missing_elements(client: AsyncClient):
    """Upload XML where a ticket is missing the required description element.

    The record should be counted as failed; the response must still be 200
    (partial-success semantics) with at least one failure reported.
    """
    response = await client.post(
        "/tickets/import",
        files=_xml_upload(MISSING_DESCRIPTION_XML),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["failed"] >= 1


@pytest.mark.asyncio
async def test_import_xml_invalid_values(client: AsyncClient):
    """Upload XML where a ticket has an invalid email.

    The record should be reported as failed; the overall response is still 200.
    """
    response = await client.post(
        "/tickets/import",
        files=_xml_upload(INVALID_EMAIL_XML),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["failed"] >= 1


@pytest.mark.asyncio
async def test_import_xml_empty(client: AsyncClient):
    """Upload XML with an empty <tickets> element — expect 200, total=0, successful=0, failed=0."""
    response = await client.post(
        "/tickets/import",
        files=_xml_upload(EMPTY_TICKETS_XML),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["successful"] == 0
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_import_xml_malformed(client: AsyncClient):
    """Upload broken XML with unclosed tags — expect 400 Bad Request."""
    response = await client.post(
        "/tickets/import",
        files=_xml_upload(MALFORMED_XML),
    )
    assert response.status_code == 400
