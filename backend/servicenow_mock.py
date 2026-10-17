from datetime import datetime, timezone
from uuid import uuid4

from database import db


def create_mock_incident(ticket: dict) -> dict:
    """Create a simulated ServiceNow incident in MongoDB."""

    if db is None:
        raise RuntimeError("Database is not configured.")

    now = datetime.now(timezone.utc)

    incident = {
        "number": "INC" + uuid4().hex[:6].upper(),
        "ticket_reference": ticket["ticket_reference"],
        "short_description": ticket["description"][:120],
        "description": ticket["description"],
        "category": ticket["category"],
        "priority": ticket["priority"],
        "assignment_group": ticket["assignment_group"],
        "state": "New",
        "created_at": now,
        "updated_at": now,
        "integration_type": "MOCK_SERVICENOW",
    }

    db["mock_servicenow_incidents"].insert_one(incident)

    # Return a JSON-friendly response without MongoDB's ObjectId.
    incident["created_at"] = incident["created_at"].isoformat()
    incident["updated_at"] = incident["updated_at"].isoformat()

    return incident


def update_mock_incident(
    incident_number: str,
    new_status: str,
) -> bool:
    """Update the status of a simulated ServiceNow incident."""

    if db is None:
        raise RuntimeError("Database is not configured.")

    result = db["mock_servicenow_incidents"].update_one(
        {"number": incident_number},
        {
            "$set": {
                "state": new_status,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    return result.matched_count > 0