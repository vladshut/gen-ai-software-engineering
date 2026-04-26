# API Requirements Quality Checklist: Banking Transactions API

**Purpose**: Validate completeness, clarity, and consistency of API requirements before implementation
**Created**: 2026-04-26
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Are error response formats specified for ALL endpoints, not just POST /transactions? [Completeness, Gap]
- [ ] CHK002 - Are request Content-Type requirements documented (e.g., must send application/json)? [Completeness, Gap]
- [ ] CHK003 - Are response Content-Type headers specified for each endpoint (JSON vs CSV)? [Completeness, Gap]
- [ ] CHK004 - Is the GET /transactions response format specified — bare array or wrapped in an object? [Clarity, Spec §FR-003]
- [ ] CHK005 - Are pagination requirements defined or explicitly excluded for GET /transactions? [Completeness, Gap]
- [ ] CHK006 - Is the balance response structure specified when an account has transactions in multiple currencies? [Clarity, Spec §FR-005]

## Requirement Clarity

- [ ] CHK007 - Is "positive number" in FR-006 clarified to exclude zero explicitly? [Clarity, Spec §FR-006]
- [ ] CHK008 - Is the ACC-XXXXX format case-sensitivity defined (ACC-abcde vs ACC-ABCDE vs mixed)? [Ambiguity, Spec §FR-007]
- [ ] CHK009 - Are the "from" and "to" date range filter boundaries specified as inclusive or exclusive? [Ambiguity, Spec §FR-013]
- [ ] CHK010 - Is the ISO 8601 date format for filters specified precisely (date-only YYYY-MM-DD vs full datetime)? [Clarity, Spec §FR-013]
- [ ] CHK011 - Is "most recent transaction date" in the summary defined — creation time or last status change? [Clarity, Spec §FR-015]

## Requirement Consistency

- [ ] CHK012 - Is the transaction status lifecycle consistent between FR-002 (defaults to "completed") and the Transaction model (supports pending/completed/failed)? [Consistency, Spec §FR-002]
- [ ] CHK013 - Are validation error messages consistent between the spec's error response example and FR-010's requirements? [Consistency, Spec §FR-010]
- [ ] CHK014 - Is the currency allowlist in FR-008 consistent with any currencies used in acceptance scenarios? [Consistency, Spec §FR-008]

## Scenario Coverage

- [ ] CHK015 - Are requirements defined for what happens when GET /transactions has no matching filter results — empty array or 404? [Coverage, Gap]
- [ ] CHK016 - Are requirements defined for invalid query parameter names (e.g., ?foo=bar) — ignore or reject? [Coverage, Gap]
- [ ] CHK017 - Are requirements defined for malformed JSON in POST body? [Coverage, Exception Flow, Gap]
- [ ] CHK018 - Are requirements defined for missing required fields (empty POST body)? [Coverage, Spec §FR-001]
- [ ] CHK019 - Are requirements specified for duplicate transaction submissions (idempotency)? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK020 - Is behavior defined when fromAccount equals toAccount in a transfer? [Edge Case, Gap]
- [ ] CHK021 - Is behavior defined for very large amounts (e.g., Number.MAX_SAFE_INTEGER)? [Edge Case, Gap]
- [ ] CHK022 - Is CSV field escaping defined for values containing commas or quotes? [Edge Case, Spec §FR-016]
- [ ] CHK023 - Is behavior defined when accountId filter value doesn't match ACC-XXXXX format? [Edge Case, Gap]
- [ ] CHK024 - Is behavior defined for empty string or null values in optional fields (fromAccount for deposits)? [Edge Case, Spec §FR-017]

## Non-Functional Requirements

- [ ] CHK025 - Are concurrent request handling requirements defined or explicitly out of scope? [Non-Functional, Gap]
- [ ] CHK026 - Are maximum request body size limits defined? [Non-Functional, Gap]
- [ ] CHK027 - Are CORS requirements defined or explicitly excluded? [Non-Functional, Gap]

## Dependencies & Assumptions

- [ ] CHK028 - Is the assumption "all transactions default to completed" validated against the homework requirements in TASKS.md? [Assumption, Spec §Assumptions]
- [ ] CHK029 - Is the Node.js minimum version requirement (18+) documented in deliverable requirements? [Dependency, Gap]
- [ ] CHK030 - Are the chosen additional features (Summary + CSV Export) explicitly confirmed as the Task 4 selections? [Assumption]

## Notes

- Items referencing [Gap] indicate requirements that may need to be added to the spec
- Items referencing [Ambiguity] indicate requirements that need clarification
- Focus: Standard depth, Reviewer (PR) audience
- Created new file: `checklists/api.md` with 30 items
