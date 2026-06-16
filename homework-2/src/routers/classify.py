from fastapi import APIRouter, HTTPException
from src.models.ticket import ClassificationResult
from src.services.classify_service import auto_classify_ticket

router = APIRouter()

@router.post("/tickets/{ticket_id}/auto-classify", response_model=ClassificationResult)
async def classify_ticket(ticket_id: str):
    """Auto-classify a ticket by analyzing its subject and description."""
    result = await auto_classify_ticket(ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return result
