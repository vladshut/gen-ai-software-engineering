import logging
from typing import Optional

from src.models.ticket import ClassificationResult
from src.models.enums import Category, Priority

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    Category.account_access: [
        "login", "password", "2fa", "locked", "can't access", "account access",
        "sign in", "authentication", "forgot password", "reset password",
        "locked out", "access denied",
    ],
    Category.technical_issue: [
        "bug", "error", "crash", "broken", "not working", "glitch", "malfunction",
        "freezing", "slow", "timeout", "exception", "stack trace",
    ],
    Category.billing_question: [
        "payment", "invoice", "refund", "charge", "billing", "subscription",
        "pricing", "receipt", "overcharged", "credit card", "plan upgrade",
    ],
    Category.feature_request: [
        "suggest", "enhance", "wish", "add", "feature request", "improvement",
        "would like", "could you add", "new feature", "please add",
    ],
    Category.bug_report: [
        "defect", "reproduce", "regression", "steps to reproduce",
        "expected behavior", "actual behavior", "found a bug",
        "report a bug", "issue with",
    ],
}

PRIORITY_URGENT = [
    "can't access", "critical", "production down", "security", "urgent",
    "emergency", "breach", "data loss",
]
PRIORITY_HIGH = [
    "important", "blocking", "asap", "high priority", "blocker", "deadline",
]
PRIORITY_LOW = [
    "minor", "cosmetic", "suggestion", "nice to have", "low priority",
    "when you get a chance",
]


def classify_ticket(subject: str, description: str) -> ClassificationResult:
    """Classify a support ticket based on keyword matching in subject + description."""
    text = (subject + " " + description).lower()

    # --- Category detection ---
    best_category: Optional[Category] = None
    best_count = 0
    best_keywords: list[str] = []
    total_keywords_checked = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text]
        total_keywords_checked += len(keywords)
        if len(matched) > best_count:
            best_count = len(matched)
            best_category = category
            best_keywords = matched

    if best_category is None or best_count == 0:
        category = Category.other
        confidence = 0.1
        keywords_found: list[str] = []
    else:
        category = best_category
        # Confidence relative to the winning category's keyword list length
        category_keyword_count = len(CATEGORY_KEYWORDS[category])
        confidence = min(best_count / category_keyword_count, 1.0)
        keywords_found = best_keywords

    # --- Priority detection ---
    priority_reason = "default medium priority"

    if any(kw in text for kw in PRIORITY_URGENT):
        priority = Priority.urgent
        matched_urgent = [kw for kw in PRIORITY_URGENT if kw in text]
        priority_reason = f"urgent keywords: {matched_urgent}"
    elif any(kw in text for kw in PRIORITY_HIGH):
        priority = Priority.high
        matched_high = [kw for kw in PRIORITY_HIGH if kw in text]
        priority_reason = f"high-priority keywords: {matched_high}"
    elif any(kw in text for kw in PRIORITY_LOW):
        priority = Priority.low
        matched_low = [kw for kw in PRIORITY_LOW if kw in text]
        priority_reason = f"low-priority keywords: {matched_low}"
    else:
        priority = Priority.medium

    # --- Reasoning string ---
    if category == Category.other:
        reasoning = (
            f"No category keywords matched. "
            f"Priority set to '{priority.value}' based on {priority_reason}."
        )
    else:
        reasoning = (
            f"Matched {best_count} keywords for category '{category.value}': "
            f"{keywords_found}. "
            f"Priority set to '{priority.value}' based on {priority_reason}."
        )

    result = ClassificationResult(
        category=category,
        priority=priority,
        confidence=confidence,
        reasoning=reasoning,
        keywords_found=keywords_found,
    )

    logger.info(
        "Ticket classified — category=%s priority=%s confidence=%.2f keywords=%s",
        category.value,
        priority.value,
        confidence,
        keywords_found,
    )

    return result


async def auto_classify_ticket(ticket_id: str) -> ClassificationResult | None:
    """Fetch a ticket by ID, classify it, persist the new category/priority, and return the result."""
    from src.db.repository import get_ticket_by_id, update_ticket  # local import to avoid circular deps

    ticket = await get_ticket_by_id(ticket_id)
    if ticket is None:
        logger.warning("auto_classify_ticket: ticket '%s' not found", ticket_id)
        return None

    result = classify_ticket(
        subject=ticket.get("subject", ""),
        description=ticket.get("description", ""),
    )

    await update_ticket(ticket_id, {
        "category": result.category.value,
        "priority": result.priority.value,
    })

    logger.info(
        "auto_classify_ticket: ticket '%s' updated — category=%s priority=%s",
        ticket_id,
        result.category.value,
        result.priority.value,
    )

    return result
