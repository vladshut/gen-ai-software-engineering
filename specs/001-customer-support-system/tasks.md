# Tasks: Intelligent Customer Support System

**Input**: Design documents from `specs/001-customer-support-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included — spec requires >85% coverage (FR-022) with specific test file structure.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and configuration

<!-- parallel-group: 1 (max 3 concurrent) -->
- [ ] T001 [P] Create project directory structure per plan.md layout in homework-2/
- [ ] T002 [P] Create pyproject.toml with project metadata and tool configuration in homework-2/pyproject.toml
- [ ] T003 [P] Create .gitignore for Python project in homework-2/.gitignore

<!-- parallel-group: 2 (max 3 concurrent) -->
- [ ] T004 [P] Create requirements.txt with runtime dependencies (fastapi, uvicorn, pydantic, python-multipart, defusedxml, aiosqlite, aiofiles) in homework-2/requirements.txt
- [ ] T005 [P] Create requirements-dev.txt with dev dependencies (pytest, pytest-asyncio, pytest-cov, httpx) in homework-2/requirements-dev.txt
- [ ] T006 [P] Create all __init__.py files for src/, src/models/, src/routers/, src/services/, src/db/, src/utils/, tests/ packages

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database, enums, base models, and app skeleton that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

<!-- parallel-group: 3 (max 3 concurrent) -->
- [ ] T007 [P] Create enum definitions (Category, Priority, Status, Source, DeviceType) in homework-2/src/models/enums.py
- [ ] T008 [P] Create SQLite database module with connection management, table creation, and async context in homework-2/src/db/database.py
- [ ] T009 [P] Create Pydantic models for Ticket (create request, update request, response, DB model), Metadata, pagination response in homework-2/src/models/ticket.py

<!-- sequential -->
- [ ] T010 Create data access repository with CRUD operations (create, get_by_id, get_all with filters/pagination, update, delete) in homework-2/src/db/repository.py
- [ ] T011 Create FastAPI application entry point with lifespan (DB init), CORS, and router includes in homework-2/src/main.py
- [ ] T012 Create shared test fixtures (async test client, test DB setup/teardown, sample ticket data) in homework-2/tests/conftest.py

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Create and Manage Support Tickets (Priority: P1) 🎯 MVP

**Goal**: Full CRUD API for support tickets with validation, filtering, and pagination

**Independent Test**: Create a ticket, retrieve it, update status, list with filters, delete — all via API

### Tests for User Story 1

<!-- parallel-group: 4 (max 3 concurrent) -->
- [ ] T013 [P] [US1] Create API endpoint tests (11 tests: create valid/invalid, get by id/not found, list with filters/pagination, update valid/invalid/not found, delete/not found) in homework-2/tests/test_ticket_api.py
- [ ] T014 [P] [US1] Create data validation tests (9 tests: email format, subject length bounds, description length bounds, enum validation for category/priority/status/source/device_type, required fields, tags array, metadata object) in homework-2/tests/test_ticket_model.py

### Implementation for User Story 1

- [ ] T015 [US1] Create ticket service with business logic (create with UUID/timestamps, get, list with filtering/pagination, update with timestamp, delete) in homework-2/src/services/ticket_service.py
- [ ] T016 [US1] Create tickets router with CRUD endpoints (POST /tickets, GET /tickets, GET /tickets/{id}, PUT /tickets/{id}, DELETE /tickets/{id}) in homework-2/src/routers/tickets.py

**Checkpoint**: Ticket CRUD is fully functional and independently testable

---

## Phase 4: User Story 2 — Bulk Import Tickets from Files (Priority: P1)

**Goal**: Import tickets from CSV, JSON, and XML files with validation and summary reporting

**Independent Test**: Upload a CSV with valid/invalid records and verify import summary counts and error details

### Tests for User Story 2

<!-- parallel-group: 5 (max 3 concurrent) -->
- [ ] T017 [P] [US2] Create CSV parsing tests (6 tests: valid 50-row file, missing required fields, invalid email, extra columns, empty file, malformed CSV) in homework-2/tests/test_import_csv.py
- [ ] T018 [P] [US2] Create JSON parsing tests (5 tests: valid 20-item array, invalid field values, empty array, malformed JSON, nested object handling) in homework-2/tests/test_import_json.py
- [ ] T019 [P] [US2] Create XML parsing tests (5 tests: valid 30-element file, missing elements, invalid values, empty file, malformed XML) in homework-2/tests/test_import_xml.py

### Implementation for User Story 2

- [ ] T020 [US2] Create import service with format-specific parsers (parse_csv, parse_json, parse_xml) and unified validate-and-import logic returning ImportSummary in homework-2/src/services/import_service.py
- [ ] T021 [US2] Create import router with POST /tickets/import endpoint (multipart file upload, format detection by extension, delegates to import_service) in homework-2/src/routers/import_router.py

### Sample Data for User Story 2

<!-- parallel-group: 6 (max 3 concurrent) -->
- [ ] T022 [P] [US2] Create sample_tickets.csv with 50 valid realistic tickets in homework-2/tests/fixtures/sample_tickets.csv
- [ ] T023 [P] [US2] Create sample_tickets.json with 20 valid realistic tickets in homework-2/tests/fixtures/sample_tickets.json
- [ ] T024 [P] [US2] Create sample_tickets.xml with 30 valid realistic tickets in homework-2/tests/fixtures/sample_tickets.xml

<!-- parallel-group: 7 (max 3 concurrent) -->
- [ ] T025 [P] [US2] Create invalid_tickets.csv with malformed data (bad emails, missing fields, invalid enums) in homework-2/tests/fixtures/invalid_tickets.csv
- [ ] T026 [P] [US2] Create invalid_tickets.json with malformed data in homework-2/tests/fixtures/invalid_tickets.json
- [ ] T027 [P] [US2] Create invalid_tickets.xml with malformed data in homework-2/tests/fixtures/invalid_tickets.xml

**Checkpoint**: All three file formats can be imported with validation and error reporting

---

## Phase 5: User Story 3 — Auto-Classify Tickets (Priority: P2)

**Goal**: Keyword-based auto-classification engine that assigns category, priority, and confidence score

**Independent Test**: Create a ticket with "can't access account" description, trigger auto-classify, verify category=account_access, priority=urgent, confidence>0.5

### Tests for User Story 3

- [ ] T028 [US3] Create classification tests (10 tests: each category keyword match, priority keyword escalation, multi-keyword scoring, vague text→other, confidence score range, manual override persistence, auto-classify on creation flag, empty description, mixed category keywords, reasoning text content) in homework-2/tests/test_categorization.py

### Implementation for User Story 3

- [ ] T029 [US3] Create classification service with keyword dictionaries per category, priority rules, confidence scoring algorithm, and reasoning generator in homework-2/src/services/classify_service.py
- [ ] T030 [US3] Create classify router with POST /tickets/{id}/auto-classify endpoint in homework-2/src/routers/classify.py
- [ ] T031 [US3] Integrate auto-classify flag into ticket creation (update tickets router POST /tickets to check auto_classify field and run classification) in homework-2/src/routers/tickets.py

**Checkpoint**: Auto-classification works standalone and integrated with ticket creation

---

## Phase 6: User Story 4 — Comprehensive Test Suite (Priority: P2)

**Goal**: Integration tests, performance benchmarks, and >85% overall code coverage

**Independent Test**: Run full test suite and verify coverage report shows >85%

### Tests for User Story 4

<!-- parallel-group: 8 (max 2 concurrent) -->
- [ ] T032 [P] [US4] Create integration tests (5 tests: complete ticket lifecycle create→update→resolve→close, bulk import then auto-classify all, concurrent 20+ simultaneous ticket creates, combined category+priority+status filtering with pagination, import→classify→filter end-to-end) in homework-2/tests/test_integration.py
- [ ] T033 [P] [US4] Create performance benchmark tests (5 tests: single CRUD operation latency <1s, 50-ticket bulk import <5s, classification response time, 20 concurrent requests throughput, list pagination response time) in homework-2/tests/test_performance.py

**Checkpoint**: Full test suite passes with >85% coverage

---

## Phase 7: User Story 5 — Multi-Level Documentation (Priority: P3)

**Goal**: Four documentation files for different audiences with Mermaid diagrams

**Independent Test**: Verify all 4 docs exist with required sections and ≥3 Mermaid diagrams total

<!-- parallel-group: 9 (max 3 concurrent) -->
- [ ] T034 [P] [US5] Create README.md with project overview, features, architecture diagram (Mermaid), installation/setup, how to run tests, and project structure in homework-2/docs/README.md
- [ ] T035 [P] [US5] Create API_REFERENCE.md with all endpoints, request/response examples, data models, error formats, and cURL examples for every endpoint in homework-2/docs/API_REFERENCE.md
- [ ] T036 [P] [US5] Create ARCHITECTURE.md with high-level architecture diagram (Mermaid), component descriptions, data flow sequence diagrams (Mermaid), design decisions, security/performance considerations in homework-2/docs/ARCHITECTURE.md

<!-- sequential -->
- [ ] T037 [US5] Create TESTING_GUIDE.md with test pyramid diagram (Mermaid), how to run tests, sample data locations, manual testing checklist, performance benchmarks table in homework-2/docs/TESTING_GUIDE.md

**Checkpoint**: All documentation complete with ≥3 Mermaid diagrams

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and coverage verification

- [ ] T038 Run full test suite with coverage report (pytest --cov=src --cov-report=html --cov-report=term) and verify >85% coverage
- [ ] T039 Capture test coverage screenshot and save to homework-2/docs/screenshots/test_coverage.png
- [ ] T040 Validate all sample data files exist and match spec counts (CSV=50, JSON=20, XML=30)
- [ ] T041 Run quickstart.md validation — verify server starts and sample cURL commands work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP target
- **US2 (Phase 4)**: Depends on Foundational + US1 (reuses ticket creation)
- **US3 (Phase 5)**: Depends on Foundational + US1 (needs tickets to classify)
- **US4 (Phase 6)**: Depends on US1 + US2 + US3 (integration tests need all features)
- **US5 (Phase 7)**: Depends on US1 + US2 + US3 (docs describe implemented features)
- **Polish (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational — can start immediately
- **US2 (P1)**: Depends on US1 (needs ticket_service for creating imported tickets)
- **US3 (P2)**: Depends on US1 (needs existing tickets to classify)
- **US4 (P2)**: Depends on US1 + US2 + US3 (integration tests span all features)
- **US5 (P3)**: Can start after US3 (needs all features for accurate docs)

### Within Each User Story

- Tests written first (RED phase)
- Models/services before routers
- Core implementation before integration
- Story complete before next priority

### Parallel Opportunities

- Phase 1: All setup tasks are parallelizable (2 groups of 3)
- Phase 2: Enums, DB, and Pydantic models are parallelizable; then sequential
- Phase 3: Test files T013+T014 are parallelizable
- Phase 4: All 3 format test files parallelizable; all 3 valid fixture files parallelizable; all 3 invalid fixture files parallelizable
- Phase 5: Sequential (classification service → router → integration)
- Phase 6: Integration and performance tests parallelizable
- Phase 7: 3 doc files parallelizable, then 4th sequential

---

## Parallel Example: Phase 4 (Bulk Import)

```bash
# Launch all format tests together:
Task: "CSV parsing tests in tests/test_import_csv.py"
Task: "JSON parsing tests in tests/test_import_json.py"
Task: "XML parsing tests in tests/test_import_xml.py"

# Launch all valid fixture files together:
Task: "sample_tickets.csv (50 tickets)"
Task: "sample_tickets.json (20 tickets)"
Task: "sample_tickets.xml (30 tickets)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 — Ticket CRUD
4. **STOP and VALIDATE**: All CRUD operations work end-to-end
5. Continue to US2 → US3 → US4 → US5

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Ticket CRUD works (MVP!)
3. US2 → Bulk import works for all 3 formats
4. US3 → Auto-classification works standalone and on creation
5. US4 → Full test suite with >85% coverage
6. US5 → All documentation complete
7. Polish → Screenshots, validation, cleanup

---

## Notes

- Total tasks: 41
- US1: 4 tasks (2 test + 2 impl)
- US2: 11 tasks (3 test + 2 impl + 6 fixtures)
- US3: 4 tasks (1 test + 3 impl)
- US4: 2 tasks (integration + performance tests)
- US5: 4 tasks (4 doc files)
- Setup: 6 tasks, Foundational: 6 tasks, Polish: 4 tasks
- [P] tasks = different files, no dependencies
- Commit after each task or logical group
