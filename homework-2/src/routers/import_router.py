from fastapi import APIRouter, UploadFile, File, HTTPException
from src.models.ticket import ImportSummary
from src.services import import_service

router = APIRouter()

@router.post("/tickets/import", response_model=ImportSummary)
async def import_tickets(file: UploadFile = File(...)):
    """Bulk import tickets from CSV, JSON, or XML file."""
    content = await file.read()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        summary = await import_service.import_from_file(content, file.filename)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
