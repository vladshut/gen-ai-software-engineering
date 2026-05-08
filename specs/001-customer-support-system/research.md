# Research: Intelligent Customer Support System

## Technology Decisions

### FastAPI + Pydantic v2
- **Decision**: Use FastAPI as the web framework with Pydantic v2 for data validation
- **Rationale**: Built-in async support, automatic OpenAPI docs, excellent validation with Pydantic, native support for file uploads via python-multipart
- **Alternatives considered**: Flask (simpler but no async, no built-in validation), Django REST Framework (too heavy for this scope)

### SQLite via aiosqlite
- **Decision**: Use SQLite for persistent storage with async access
- **Rationale**: Zero-config, file-based, survives restarts, no external DB server needed. aiosqlite provides async interface compatible with FastAPI's async handlers
- **Alternatives considered**: In-memory dict (no persistence), PostgreSQL (overkill for demo), TinyDB (no SQL querying)

### Keyword-Based Classification
- **Decision**: Implement classification using keyword dictionaries with weighted scoring
- **Rationale**: Deterministic, fully testable, no ML dependencies. Each category has a keyword set; matching produces a confidence score based on keyword frequency and specificity
- **Alternatives considered**: ML/NLP models (too complex, non-deterministic for tests), regex-only (too brittle)

### XML Parsing with defusedxml
- **Decision**: Use defusedxml instead of stdlib xml.etree for XML import
- **Rationale**: Prevents XML entity expansion attacks (XXE). Safe by default even though this is an educational project
- **Alternatives considered**: xml.etree.ElementTree (vulnerable to XXE), lxml (heavier dependency)

### Test Framework
- **Decision**: pytest + httpx for async test client + pytest-cov for coverage
- **Rationale**: pytest is the Python standard. httpx's AsyncClient works with FastAPI's TestClient for async endpoint testing. pytest-cov integrates with pytest for coverage reporting
- **Alternatives considered**: unittest (more verbose), requests (no async support for test client)

## Best Practices Applied

### File Upload Handling
- Use `UploadFile` from FastAPI for multipart file handling
- Detect format from file extension or content-type header
- Read file content into memory (files < 10MB per assumption)
- Validate format before attempting to parse records

### Pagination Pattern
- Offset-based: `?page=1&page_size=20`
- Return metadata: `{ page, page_size, total, items: [...] }`
- Default page_size=20, max page_size=100
- Page numbers start at 1

### Error Response Format
- Consistent error schema: `{ detail: string }` for simple errors
- Validation errors: `{ detail: [{ loc: [...], msg: string, type: string }] }` (FastAPI default)
- Bulk import errors: per-record error array with row number and reason
