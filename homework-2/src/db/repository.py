import json
from datetime import datetime, timezone

from src.db.database import get_db


def row_to_dict(row) -> dict:
    """Convert an aiosqlite.Row to a plain dict, parsing tags from JSON string to list."""
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d


async def create_ticket(ticket_data: dict) -> dict:
    """INSERT a new ticket row and return it as a dict."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO tickets (
                id, customer_id, customer_email, customer_name,
                subject, description, category, priority, status,
                created_at, updated_at, resolved_at, assigned_to,
                tags, source, browser, device_type
            ) VALUES (
                :id, :customer_id, :customer_email, :customer_name,
                :subject, :description, :category, :priority, :status,
                :created_at, :updated_at, :resolved_at, :assigned_to,
                :tags, :source, :browser, :device_type
            )
            """,
            {
                "id": ticket_data.get("id"),
                "customer_id": ticket_data.get("customer_id"),
                "customer_email": ticket_data.get("customer_email"),
                "customer_name": ticket_data.get("customer_name"),
                "subject": ticket_data.get("subject"),
                "description": ticket_data.get("description"),
                "category": ticket_data.get("category"),
                "priority": ticket_data.get("priority", "medium"),
                "status": ticket_data.get("status", "new"),
                "created_at": ticket_data.get("created_at"),
                "updated_at": ticket_data.get("updated_at"),
                "resolved_at": ticket_data.get("resolved_at"),
                "assigned_to": ticket_data.get("assigned_to"),
                "tags": json.dumps(ticket_data.get("tags", [])),
                "source": ticket_data.get("source", "api"),
                "browser": ticket_data.get("browser"),
                "device_type": ticket_data.get("device_type"),
            },
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_data["id"],)
        )
        row = await cursor.fetchone()
        return row_to_dict(row)


async def get_ticket_by_id(ticket_id: str) -> dict | None:
    """SELECT a ticket by its id; return dict or None if not found."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        )
        row = await cursor.fetchone()
        return row_to_dict(row) if row is not None else None


async def get_all_tickets(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> tuple[list[dict], int]:
    """Return a paginated list of tickets and the total count matching the filters."""
    conditions: list[str] = []
    params: list = []

    if category is not None:
        conditions.append("category = ?")
        params.append(category)
    if priority is not None:
        conditions.append("priority = ?")
        params.append(priority)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    offset = (page - 1) * page_size

    async with get_db() as db:
        # Total count
        count_cursor = await db.execute(
            f"SELECT COUNT(*) FROM tickets {where_clause}", params
        )
        count_row = await count_cursor.fetchone()
        total = count_row[0] if count_row else 0

        # Paginated rows
        rows_cursor = await db.execute(
            f"SELECT * FROM tickets {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        )
        rows = await rows_cursor.fetchall()

    return [row_to_dict(r) for r in rows], total


async def update_ticket(ticket_id: str, update_data: dict) -> dict | None:
    """Update a ticket's fields dynamically; return the updated dict or None if not found."""
    # Filter out None values — only update supplied fields
    fields = {k: v for k, v in update_data.items() if v is not None}

    if not fields:
        return await get_ticket_by_id(ticket_id)

    now = datetime.now(timezone.utc).isoformat()
    fields["updated_at"] = now

    # If status is being changed to "resolved", stamp resolved_at
    if fields.get("status") == "resolved":
        fields.setdefault("resolved_at", now)

    # Serialize tags to JSON if present
    if "tags" in fields and isinstance(fields["tags"], list):
        fields["tags"] = json.dumps(fields["tags"])

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [ticket_id]

    async with get_db() as db:
        cursor = await db.execute(
            f"UPDATE tickets SET {set_clause} WHERE id = ?", values
        )
        await db.commit()

        if cursor.rowcount == 0:
            return None

        row_cursor = await db.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        )
        row = await row_cursor.fetchone()
        return row_to_dict(row) if row is not None else None


async def delete_ticket(ticket_id: str) -> bool:
    """DELETE a ticket by id; return True if a row was deleted."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM tickets WHERE id = ?", (ticket_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
