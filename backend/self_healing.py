
from datetime import datetime, timezone
from uuid import uuid4

from database import db


def write_audit_log(
    workflow_id: str,
    action: str,
    status: str,
    details: str,
    ticket_reference: str | None = None,
) -> dict:
    """Record one workflow step and return JSON-safe data."""

    entry = {
        "workflow_id": workflow_id,
        "ticket_reference": ticket_reference,
        "action": action,
        "status": status,
        "details": details,
        "created_at": datetime.now(timezone.utc),
    }

    result = db["audit_logs"].insert_one(entry)

    # MongoDB creates an ObjectId; convert it to a string.
    entry["_id"] = str(result.inserted_id)
    entry["created_at"] = entry["created_at"].isoformat()

    return entry


def find_password_knowledge() -> list[dict]:
    """Find existing password-related articles in MongoDB."""

    matches = []

    try:
        collection_names = db.list_collection_names()

        for collection_name in collection_names:
            if "knowledge" not in collection_name.lower():
                continue

            for article in db[collection_name].find({}):
                searchable_text = " ".join(
                    str(article.get(field, ""))
                    for field in ("title", "content", "body", "description")
                ).lower()

                if "password" in searchable_text:
                    matches.append({
                        "title": article.get("title", "Password guidance"),
                        "collection": collection_name,
                    })

    except Exception as exc:
        print(f"Knowledge search failed: {exc}")

    return matches


def run_password_reset(
    description: str,
    ticket_reference: str | None = None,
) -> dict:
    """Run a simulated password-reset workflow; no real password is changed."""

    if db is None:
        raise RuntimeError("Database is not configured.")

    workflow_id = "WF-" + uuid4().hex[:8].upper()
    audit = []

    def record(action: str, status: str, details: str) -> None:
        audit.append(
            write_audit_log(
                workflow_id,
                action,
                status,
                details,
                ticket_reference,
            )
        )

    if not description.strip():
        raise ValueError("Please provide a password-related issue.")

    if "password" not in description.lower():
        raise ValueError("This workflow is only for password-related issues.")

    record(
        "Identify",
        "Completed",
        "Identified a password-related issue.",
    )

    record(
        "Diagnose",
        "Completed",
        "Classified the issue for simulated password-reset assistance.",
    )

    articles = find_password_knowledge()

    if articles:
        article_titles = [article["title"] for article in articles]
        record(
            "Knowledge Search",
            "Completed",
            "Found password-related knowledge articles: "
            + ", ".join(article_titles[:5]),
        )
    else:
        record(
            "Knowledge Search",
            "Warning",
            "No password-related article was found. IT Support review is recommended.",
        )

    record(
        "Determine Automation",
        "Completed",
        "Selected the simulated password-reset workflow. "
        "Real account changes require an approved identity-verification system.",
    )

    # Safe demonstration only: no real password or account is changed.
    record(
        "Execute",
        "Simulated",
        "Mock password-reset action executed. No real credentials were changed.",
    )

    # This validates the simulation, not a real employee account.
    validation_passed = True

    record(
        "Validate",
        "Simulated",
        "Mock workflow completed successfully. "
        "Real account validation was not performed.",
    )

    ticket_updated = False
    servicenow_updated = False

    if ticket_reference:
        ticket = db["tickets"].find_one(
            {"ticket_reference": ticket_reference}
        )

        if ticket:
            db["tickets"].update_one(
                {"ticket_reference": ticket_reference},
                {
                    "$set": {
                        "status": "Resolved",
                        "updated_at": datetime.now(timezone.utc),
                        "self_healing_workflow_id": workflow_id,
                    }
                },
            )
            ticket_updated = True

            incident_number = ticket.get("servicenow_number")

            if incident_number:
                try:
                    from servicenow_mock import update_mock_incident

                    servicenow_updated = update_mock_incident(
                        incident_number,
                        "Resolved",
                    )

                    if servicenow_updated:
                        db["tickets"].update_one(
                            {"ticket_reference": ticket_reference},
                            {
                                "$set": {
                                    "servicenow_status": "Resolved"
                                }
                            },
                        )

                except Exception as exc:
                    print(f"ServiceNow status update failed: {exc}")

            record(
                "Update ServiceNow",
                "Completed" if servicenow_updated else "Warning",
                (
                    "Mock incident status updated to Resolved."
                    if servicenow_updated
                    else "Mock incident was not updated. "
                    "Check the incident reference and integration."
                ),
            )

        else:
            record(
                "Update Ticket",
                "Warning",
                "Ticket reference was not found; no ticket was changed.",
            )
    else:
        record(
            "Update Ticket",
            "Skipped",
            "No ticket reference was supplied.",
        )

    record(
        "Workflow Complete",
        "Completed",
        "Simulated password-reset workflow finished. "
        "This does not prove that a real account password was reset.",
    )

    return {
        "message": "Simulated password-reset workflow completed.",
        "workflow_id": workflow_id,
        "workflow_status": "Completed",
        "simulation_only": True,
        "real_password_changed": False,
        "validation_passed": validation_passed,
        "ticket_reference": ticket_reference,
        "ticket_updated": ticket_updated,
        "servicenow_updated": servicenow_updated,
        "knowledge_articles_found": len(articles),
        "audit_log": audit,
    }
