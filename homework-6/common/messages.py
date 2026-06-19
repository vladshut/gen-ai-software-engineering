"""Message envelope passed between agents on every hop + PII masking.

Envelope schema (frozen contract):
    {
      "message_id": "uuid4",
      "timestamp": "ISO-8601Z",
      "source_agent": "...",
      "target_agent": "...",
      "message_type": "transaction",
      "data": { "transaction_id": "...", "status": "...", ... }
    }
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def _utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_default(value: Any) -> Any:
    """Serialize Decimals as strings to preserve exact money values."""
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON-serializable: {type(value).__name__}")


def mask_account(account: str | None) -> str:
    """Mask an account/PII string to its last 4 characters (e.g. ****1001).

    Never log raw source_account / destination_account / names.
    """
    if not account:
        return "****"
    tail = str(account)[-4:]
    return f"****{tail}"


@dataclass
class Message:
    """A single inter-agent message envelope."""

    source_agent: str
    target_agent: str
    data: dict[str, Any]
    message_type: str = "transaction"
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "message_type": self.message_type,
            "data": self.data,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_default)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Message":
        msg = cls(
            source_agent=payload["source_agent"],
            target_agent=payload["target_agent"],
            data=payload["data"],
            message_type=payload.get("message_type", "transaction"),
        )
        # Preserve identity/time when re-hydrating a persisted message.
        if "message_id" in payload:
            msg.message_id = payload["message_id"]
        if "timestamp" in payload:
            msg.timestamp = payload["timestamp"]
        return msg

    @classmethod
    def from_json(cls, raw: str) -> "Message":
        return cls.from_dict(json.loads(raw))


def safe_log_view(transaction: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a transaction dict with PII fields masked, for logging."""
    safe = dict(transaction)
    for key in ("source_account", "destination_account"):
        if key in safe:
            safe[key] = mask_account(safe[key])
    for name_key in ("source_name", "destination_name", "name"):
        if name_key in safe:
            safe[name_key] = "****"
    return safe
