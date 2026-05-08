# Implementation Plan: Intelligent Customer Support System

**Branch**: `homework-2-submission` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-customer-support-system/spec.md`

## Summary

Build a Python/FastAPI REST API for customer support ticket management with CRUD operations, multi-format bulk import (CSV/JSON/XML), keyword-based auto-classification with confidence scoring, comprehensive tests (>85% coverage), and multi-level documentation with Mermaid diagrams. Uses SQLite for persistence and Pydantic for validation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, Uvicorn, Pydantic v2, python-multipart, defusedxml, aiofiles
**Storage**: SQLite via aiosqlite (lightweight, persistent, no external DB server)
**Testing**: pytest, pytest-asyncio, pytest-cov, httpx (for async test client)
**Target Platform**: Local development / macOS / Linux
**Project Type**: web-service (REST API)
**Performance Goals**: Single ticket CRUD < 1s, 50-ticket bulk import < 5s, 20+ concurrent requests without errors
**Constraints**: Educational project, single-instance, no auth, file uploads < 10MB
**Scale/Scope**: Demo-scale (hundreds of tickets, single user)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is an unfilled template — no concrete principles or gates defined. Proceeding without violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-customer-support-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (via /speckit-tasks)
```

### Source Code (repository root)

```text
homework-2/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ticket.py        # Pydantic models for Ticket, ClassificationResult, ImportSummary
│   │   └── enums.py         # Category, Priority, Status, Source, DeviceType enums
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── tickets.py       # CRUD endpoints
│   │   ├── import_router.py # Bulk import endpoint
│   │   └── classify.py      # Auto-classification endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ticket_service.py    # Business logic for ticket operations
│   │   ├── import_service.py    # File parsing (CSV, JSON, XML)
│   │   └── classify_service.py  # Keyword-based classification engine
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py      # SQLite connection & initialization
│   │   └── repository.py    # Data access layer
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures, test client setup
│   ├── test_ticket_api.py   # API endpoint tests (11 tests)
│   ├── test_ticket_model.py # Data validation tests (9 tests)
│   ├── test_import_csv.py   # CSV parsing tests (6 tests)
│   ├── test_import_json.py  # JSON parsing tests (5 tests)
│   ├── test_import_xml.py   # XML parsing tests (5 tests)
│   ├── test_categorization.py # Classification tests (10 tests)
│   ├── test_integration.py  # End-to-end workflow tests (5 tests)
│   ├── test_performance.py  # Benchmark tests (5 tests)
│   └── fixtures/
│       ├── sample_tickets.csv   # 50 valid tickets
│       ├── sample_tickets.json  # 20 valid tickets
│       ├── sample_tickets.xml   # 30 valid tickets
│       ├── invalid_tickets.csv  # Malformed CSV
│       ├── invalid_tickets.json # Malformed JSON
│       └── invalid_tickets.xml  # Malformed XML
├── docs/
│   ├── screenshots/
│   │   └── .gitkeep
│   ├── README.md
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   └── TESTING_GUIDE.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── .gitignore
```

**Structure Decision**: Single-project web service layout under `homework-2/`. Source code in `src/` with layered architecture (routers → services → repository → database). Tests mirror the structure specified in the homework requirements. Documentation in `docs/`.

## Architecture

### Component Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│   Routers    │────▶│   Services   │────▶│   Repository    │────▶│  SQLite  │
│ (endpoints)  │     │ (logic)      │     │ (data access)   │     │   DB     │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────┘
  tickets.py          ticket_service       repository.py           tickets.db
  import_router.py    import_service
  classify.py         classify_service
```

### Key Design Decisions

1. **Layered architecture**: Routers handle HTTP concerns, services contain business logic, repository handles data access. Clean separation enables unit testing at each layer.
2. **SQLite with aiosqlite**: Provides persistence that survives restarts without requiring a DB server. Async interface matches FastAPI's async nature.
3. **Pydantic v2 models**: Leverage FastAPI's built-in validation. Request/response models provide automatic OpenAPI documentation.
4. **Keyword-based classification**: Simple dictionary lookup with scoring rather than ML. Deterministic, testable, and meets the 80% accuracy target for clear-keyword tickets.
5. **File parsing strategy**: Separate parser per format (CSV, JSON, XML) with a common interface. defusedxml for safe XML parsing.

## Complexity Tracking

No constitution violations to justify.
