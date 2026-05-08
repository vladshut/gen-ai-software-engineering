import json
import uuid
from datetime import datetime, timezone

from src.db import repository
from src.models.ticket import TicketCreate, TicketUpdate


async def create_ticket(ticket: TicketCreate) -> dict:
    """Create a new ticket with generated ID, timestamps, and status."""
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    ticket_data = ticket.model_dump(exclude={"metadata", "auto_classify"})

    ticket_data["id"] = ticket_id
    ticket_data["created_at"] = now
    ticket_data["updated_at"] = now
    ticket_data["status"] = "new"

    # Convert enum values to strings for storage
    if ticket_data.get("category") is not None:
        ticket_data["category"] = ticket_data["category"].value if hasattr(ticket_data["category"], "value") else ticket_data["category"]
    if ticket_data.get("priority") is not None:
        ticket_data["priority"] = ticket_data["priority"].value if hasattr(ticket_data["priority"], "value") else ticket_data["priority"]

    # Flatten metadata fields into top-level fields
    if ticket.metadata is not None:
        ticket_data["source"] = ticket.metadata.source.value if ticket.metadata.source else "api"
        ticket_data["browser"] = ticket.metadata.browser
        ticket_data["device_type"] = ticket.metadata.device_type.value if ticket.metadata.device_type else None
    else:
        ticket_data["source"] = "api"
        ticket_data["browser"] = None
        ticket_data["device_type"] = None

    # Convert tags list to JSON string for storage
    ticket_data["tags"] = json.dumps(ticket_data.get("tags", []))

    return await repository.create_ticket(ticket_data)


async def get_ticket(ticket_id: str) -> dict | None:
    """Retrieve a single ticket by ID, returning None if not found."""
    return await repository.get_ticket_by_id(ticket_id)


async def list_tickets(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> tuple[list[dict], int]:
    """Return a paginated list of tickets with optional filters."""
    page_size = min(page_size, 100)

    items, total = await repository.get_all_tickets(
        page=page,
        page_size=page_size,
        category=category,
        priority=priority,
        status=status,
    )
    return items, total


async def update_ticket(ticket_id: str, update: TicketUpdate) -> dict | None:
    """Update an existing ticket's fields, returning None if not found."""
    update_data = update.model_dump(exclude_none=True)

    # Flatten metadata fields if provided
    if "metadata" in update_data:
        metadata = update_data.pop("metadata")
        if "source" in metadata:
            update_data["source"] = metadata["source"]
        if "browser" in metadata:
            update_data["browser"] = metadata["browser"]
        if "device_type" in metadata:
            update_data["device_type"] = metadata["device_type"]

    # Convert tags list to JSON string for storage
    if "tags" in update_data:
        update_data["tags"] = json.dumps(update_data["tags"])

    return await repository.update_ticket(ticket_id, update_data)


async def delete_ticket(ticket_id: str) -> bool:
    """Delete a ticket by ID, returning True if deleted."""
    return await repository.delete_ticket(ticket_id)
