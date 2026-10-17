
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "itsm_helpdesk")

client = None
db = None

if MONGODB_URI:
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
    )
    db = client[DATABASE_NAME]


def check_database():
    if client is None:
        return {
            "connected": False,
            "message": "MONGODB_URI is not configured.",
        }

    try:
        client.admin.command("ping")
        return {
            "connected": True,
            "database": DATABASE_NAME,
        }
    except Exception:
        return {
            "connected": False,
            "message": "Database connection failed. Check your configuration.",
        }
