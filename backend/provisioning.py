
from datetime import datetime, timezone
from uuid import uuid4

from database import db


def create_software_request(
    software_name: str,
    employee: str = "Employee",
) -> dict:
    """Create a mock software request and provisioning record."""

    if db is None:
        raise RuntimeError("Database is not configured.")

    software_name = software_name.strip()
    employee = employee.strip() or "Employee"

    if not software_name:
        raise ValueError("Software name is required.")

    now = datetime.now(timezone.utc)
    request_number = "REQ" + uuid4().hex[:6].upper()

    
    request_record = {
        "request_number": request_number,
        "employee": employee,
        "software_name": software_name,
        "status": "Provisioning",
        "provisioning_mode": "MOCK",
        "message": (
            f"{software_name} provisioning has been simulated. "
            "No software was installed on the employee's device."
        ),
        "created_at": now,
        "updated_at": now,
    }

    result = db["software_requests"].insert_one(request_record)

    # Convert MongoDB ObjectId into a JSON-friendly string.
    request_record["_id"] = str(result.inserted_id)
    request_record["created_at"] = now.isoformat()
    request_record["updated_at"] = now.isoformat()

    return request_record

def list_software_requests() -> list[dict]:
    """Return recent software provisioning requests."""

    if db is None:
        raise RuntimeError("Database is not configured.")

    requests = []

    for item in db["software_requests"].find().sort(
        "created_at", -1
    ).limit(50):
        item["_id"] = str(item["_id"])

        for field in ("created_at", "updated_at"):
            if isinstance(item.get(field), datetime):
                item[field] = item[field].isoformat()

        requests.append(item)

    return requests
