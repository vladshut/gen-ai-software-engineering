import csv
import io
import json
import xml.etree.ElementTree as _stdlib_etree

import defusedxml.ElementTree as defused_etree
from pydantic import ValidationError

from src.models.ticket import ImportError_, ImportSummary, TicketCreate
from src.services.ticket_service import create_ticket


async def import_from_file(content: bytes, filename: str) -> ImportSummary:
    """Parse *content* according to *filename*'s extension and bulk-create tickets.

    Supported extensions: .csv, .json, .xml.
    Returns an ImportSummary describing successes and per-row failures.
    Raises ValueError for unknown file formats.
    """
    lower = filename.lower()
    if lower.endswith(".csv"):
        records = parse_csv(content)
    elif lower.endswith(".json"):
        records = parse_json(content)
    elif lower.endswith(".xml"):
        records = parse_xml(content)
    else:
        raise ValueError("Unsupported file format")

    errors: list[ImportError_] = []
    successful = 0

    for i, raw in enumerate(records, start=1):
        try:
            ticket_data = TicketCreate(**raw)
            await create_ticket(ticket_data)
            successful += 1
        except ValidationError as e:
            errors.append(ImportError_(row=i, error=str(e.errors()[0]["msg"]), fields={}))
        except Exception as e:
            errors.append(ImportError_(row=i, error=str(e), fields={}))

    return ImportSummary(
        total=len(records),
        successful=successful,
        failed=len(errors),
        errors=errors,
    )


def parse_csv(content: bytes) -> list[dict]:
    """Decode *content* as UTF-8 and parse it as CSV, returning a list of row dicts.

    Special handling:
    - ``tags`` column: first tried as JSON, then split on commas.
    - ``metadata`` prefixed columns (``metadata_source``, ``metadata_browser``,
      ``metadata_device_type``) are folded into a nested ``metadata`` dict.

    Raises ValueError on decode or parse errors.
    """
    if not content.strip():
        return []

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"CSV decode error: {exc}") from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[dict] = []
        for row in reader:
            record: dict = {}
            metadata: dict = {}

            for key, value in row.items():
                if value is None:
                    continue
                value = value.strip()

                if key == "tags":
                    # Try JSON array first, fall back to comma-split
                    try:
                        parsed = json.loads(value)
                        if not isinstance(parsed, list):
                            raise ValueError("tags JSON is not a list")
                        record["tags"] = parsed
                    except (json.JSONDecodeError, ValueError):
                        record["tags"] = [t.strip() for t in value.split(",") if t.strip()]
                elif key in ("metadata_source", "metadata_browser", "metadata_device_type"):
                    sub_key = key[len("metadata_"):]  # source / browser / device_type
                    if value:
                        metadata[sub_key] = value
                else:
                    if value:
                        record[key] = value

            if metadata:
                record["metadata"] = metadata

            rows.append(record)

        return rows
    except csv.Error as exc:
        raise ValueError(f"CSV parse error: {exc}") from exc


def parse_json(content: bytes) -> list[dict]:
    """Parse *content* as JSON, expecting a top-level list of objects.

    Raises ValueError if the content is not valid JSON or not a list.
    """
    if not content.strip():
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON content must be a list of ticket objects")

    return data


def parse_xml(content: bytes) -> list[dict]:
    """Parse *content* as XML, extracting all <ticket> elements into dicts.

    Expected structure::

        <tickets>
          <ticket>
            <customer_id>…</customer_id>
            …
            <tags>
              <tag>billing</tag>
              <tag>urgent</tag>
            </tags>
            <metadata>
              <source>web</source>
              <browser>Chrome</browser>
              <device_type>desktop</device_type>
            </metadata>
          </ticket>
        </tickets>

    Uses defusedxml to guard against XML-based attacks.
    Raises ValueError on parse errors.
    """
    if not content.strip():
        return []

    try:
        root = defused_etree.fromstring(content)
    except Exception as exc:
        raise ValueError(f"XML parse error: {exc}") from exc

    # Support both <tickets><ticket>…</ticket></tickets> and a bare <ticket> root
    if root.tag == "ticket":
        ticket_elements = [root]
    else:
        ticket_elements = root.findall("ticket")

    records: list[dict] = []
    for elem in ticket_elements:
        record: dict = {}
        for child in elem:
            if child.tag == "tags":
                record["tags"] = [
                    tag.text.strip()
                    for tag in child.findall("tag")
                    if tag.text and tag.text.strip()
                ]
            elif child.tag == "metadata":
                metadata: dict = {}
                for meta_child in child:
                    if meta_child.text and meta_child.text.strip():
                        metadata[meta_child.tag] = meta_child.text.strip()
                if metadata:
                    record["metadata"] = metadata
            else:
                if child.text and child.text.strip():
                    record[child.tag] = child.text.strip()

        records.append(record)

    return records
