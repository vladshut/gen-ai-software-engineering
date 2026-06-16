import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.models.enums import Category, Priority, Status
from src.models.ticket import (
    PaginatedResponse,
    TicketCreate,
    TicketMetadata,
    TicketResponse,
    TicketUpdate,
)
from src.services import ticket_service
from src.services.classify_service import classify_ticket

router = APIRouter()


def _to_response(ticket_dict: dict) -> TicketResponse:
    """Convert a flat DB dict to a TicketResponse, rebuilding nested metadata."""
    source = ticket_dict.get("source")
    browser = ticket_dict.get("browser")
    device_type = ticket_dict.get("device_type")
    metadata = TicketMetadata(source=source, browser=browser, device_type=device_type)

    tags = ticket_dict.get("tags", [])
    if isinstance(tags, str):
        tags = json.loads(tags)

    return TicketResponse(
        id=ticket_dict["id"],
        customer_id=ticket_dict["customer_id"],
        customer_email=ticket_dict["customer_email"],
        customer_name=ticket_dict["customer_name"],
        subject=ticket_dict["subject"],
        description=ticket_dict["description"],
        category=ticket_dict.get("category"),
        priority=ticket_dict["priority"],
        status=ticket_dict["status"],
        created_at=ticket_dict["created_at"],
        updated_at=ticket_dict["updated_at"],
        resolved_at=ticket_dict.get("resolved_at"),
        assigned_to=ticket_dict.get("assigned_to"),
        tags=tags,
        metadata=metadata,
    )


@router.post("/tickets", status_code=201, response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate) -> TicketResponse:
    result = await ticket_service.create_ticket(ticket)
    if ticket.auto_classify:
        classification = classify_ticket(result["subject"], result["description"])
        # Update the ticket with classification results
        from src.db import repository
        await repository.update_ticket(result["id"], {
            "category": classification.category.value,
            "priority": classification.priority.value,
        })
        result["category"] = classification.category.value
        result["priority"] = classification.priority.value
    return _to_response(result)


@router.get("/tickets", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Optional[Category] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    status: Optional[Status] = Query(default=None),
) -> PaginatedResponse[TicketResponse]:
    items, total = await ticket_service.list_tickets(
        page=page,
        page_size=page_size,
        category=category.value if category else None,
        priority=priority.value if priority else None,
        status=status.value if status else None,
    )
    return PaginatedResponse[TicketResponse](
        page=page,
        page_size=page_size,
        total=total,
        items=[_to_response(t) for t in items],
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str) -> TicketResponse:
    result = await ticket_service.get_ticket(ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _to_response(result)


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, update: TicketUpdate) -> TicketResponse:
    result = await ticket_service.update_ticket(ticket_id, update)
    if result is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _to_response(result)


@router.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str) -> dict:
    deleted = await ticket_service.delete_ticket(ticket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"detail": "Ticket deleted successfully"}
