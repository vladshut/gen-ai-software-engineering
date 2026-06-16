from typing import TypeVar, Generic, Optional

from pydantic import BaseModel, EmailStr, Field

from src.models.enums import Category, Priority, Status, Source, DeviceType

T = TypeVar("T")


class TicketMetadata(BaseModel):
    source: Optional[Source] = Source.api
    browser: Optional[str] = None
    device_type: Optional[DeviceType] = None


class TicketCreate(BaseModel):
    customer_id: str = Field(min_length=1)
    customer_email: EmailStr
    customer_name: str = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = Priority.medium
    tags: list[str] = []
    metadata: Optional[TicketMetadata] = None
    auto_classify: bool = False


class TicketUpdate(BaseModel):
    customer_id: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    subject: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assigned_to: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[TicketMetadata] = None


class TicketResponse(BaseModel):
    id: str
    customer_id: str
    customer_email: str
    customer_name: str
    subject: str
    description: str
    category: Optional[Category]
    priority: Priority
    status: Status
    created_at: str
    updated_at: str
    resolved_at: Optional[str]
    assigned_to: Optional[str]
    tags: list[str]
    metadata: TicketMetadata


class PaginatedResponse(BaseModel, Generic[T]):
    page: int
    page_size: int
    total: int
    items: list[T]


class ClassificationResult(BaseModel):
    category: Category
    priority: Priority
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    keywords_found: list[str]


class ImportError_(BaseModel):
    row: int
    error: str
    fields: dict[str, str] = {}


class ImportSummary(BaseModel):
    total: int
    successful: int
    failed: int
    errors: list[ImportError_]
