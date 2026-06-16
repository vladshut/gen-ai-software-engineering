import pytest
from pydantic import ValidationError

from src.models.ticket import TicketCreate, TicketMetadata
from src.models.enums import Category, Source, DeviceType

VALID_TICKET_DATA = {
    "customer_id": "CUST-001",
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "subject": "Test Subject",
    "description": "This is a test description that is long enough",
}


def test_valid_ticket_create():
    ticket = TicketCreate(**VALID_TICKET_DATA)
    assert ticket.customer_id == "CUST-001"
    assert ticket.customer_email == "test@example.com"
    assert ticket.customer_name == "Test User"
    assert ticket.subject == "Test Subject"
    assert ticket.description == "This is a test description that is long enough"


def test_invalid_email_format():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "customer_email": "not-an-email"})


def test_subject_too_long():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "subject": "a" * 201})


def test_subject_empty():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "subject": ""})


def test_description_too_short():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "description": "short"})


def test_description_too_long():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "description": "a" * 2001})


def test_invalid_category_enum():
    with pytest.raises(ValidationError):
        TicketCreate(**{**VALID_TICKET_DATA, "category": "invalid_category"})


def test_valid_tags_array():
    ticket = TicketCreate(**{**VALID_TICKET_DATA, "tags": ["tag1", "tag2"]})
    assert ticket.tags == ["tag1", "tag2"]


def test_valid_metadata():
    metadata = {"source": "web_form", "browser": "Chrome", "device_type": "desktop"}
    ticket = TicketCreate(**{**VALID_TICKET_DATA, "metadata": metadata})
    assert ticket.metadata is not None
    assert ticket.metadata.source == Source.web_form
    assert ticket.metadata.browser == "Chrome"
    assert ticket.metadata.device_type == DeviceType.desktop
