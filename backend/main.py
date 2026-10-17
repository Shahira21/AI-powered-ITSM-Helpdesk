from provisioning import create_software_request, list_software_requests

from self_healing import run_password_reset

from servicenow_mock import (
    create_mock_incident,
    update_mock_incident
)

from faiss_search import search_articles

from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import db, check_database
from semantic_search import (
    create_embedding,
    article_to_text,
    find_relevant_articles,
)
from llm_service import generate_grounded_answer


app = FastAPI(
    title="AI-Powered ITSM Helpdesk",
    description="AI-powered IT support and automation platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "AI-ITSM Helpdesk Backend is running!"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI-ITSM Helpdesk",
    }


@app.post("/api/analyze")
def analyze_ticket(request: dict):
    description = request.get("description", "").strip()

    if not description:
        return {
            "error": "Please enter an issue description."
        }

    # Temporary classification for testing.
    # We will replace this with AI and RAG later.
    text = description.lower()

    if "vpn" in text:
        intent = "Incident"
        category = "Network / VPN"
        priority = "P2"
        assignment_group = "Network Support"
        resolution = "Check VPN connectivity and authentication."
    elif "password" in text:
        intent = "Automatable Issue"
        category = "Account / Password"
        priority = "P2"
        assignment_group = "IT Support"
        resolution = "Check the approved password reset procedure."
    elif "install" in text or "software" in text:
        intent = "Service Request"
        category = "Software"
        priority = "P3"
        assignment_group = "IT Support"
        resolution = "Check the software catalogue."
    else:
        intent = "Knowledge Question"
        category = "General IT"
        priority = "P3"
        assignment_group = "IT Support"
        resolution = (
            "No verified solution is available yet. "
            "Knowledge search and escalation will be added next."
        )

    return {
        "description": description,
        "intent": intent,
        "category": category,
        "priority": priority,
        "assignment_group": assignment_group,
        "suggested_resolution": resolution,
        "confidence": None,
        "sources": [],
        "ticket_reference": None,
        "status": "Analyzed - not yet submitted",
    }
@app.get("/api/database-health")
def database_health():
    return check_database()

	

@app.post("/api/tickets")
def create_ticket(request: dict):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    # Step 1: Read the employee's issue.
    description = str(request.get("description", "")).strip()

    if not description:
        raise HTTPException(
            status_code=400,
            detail="Please enter a ticket description."
        )

    # Step 2: Classify the issue.
    text = description.lower()

    if "vpn" in text:
        intent = "Incident"
        category = "Network / VPN"
        priority = "P2"
        assignment_group = "Network Support"
        resolution = (
            "Check VPN connectivity and authentication. "
            "If the issue continues, escalate to Network Support."
        )

    elif "password" in text:
        intent = "Automatable Issue"
        category = "Account / Password"
        priority = "P2"
        assignment_group = "IT Support"
        resolution = (
            "Follow the approved password reset procedure. "
            "Verify the employee's identity before resetting."
        )

    elif "install" in text or "software" in text:
        intent = "Service Request"
        category = "Software"
        priority = "P3"
        assignment_group = "IT Support"
        resolution = (
            "Check the approved software catalogue and "
            "confirm authorization before installation."
        )

    else:
        intent = "Knowledge Question"
        category = "General IT"
        priority = "P3"
        assignment_group = "IT Support"
        resolution = (
            "No verified solution is available yet. "
            "Review the knowledge base or escalate to IT Support."
        )

    # Step 3: Generate a unique ticket reference.
    ticket_reference = "ITSM-" + uuid4().hex[:8].upper()
    created_at = datetime.now(timezone.utc)

    # Step 4: Prepare the ticket.
    ticket = {
        "ticket_reference": ticket_reference,
        "description": description,
        "intent": intent,
        "category": category,
        "priority": priority,
        "assignment_group": assignment_group,
        "suggested_resolution": resolution,
        "status": "Open",
        "created_at": created_at,
        "updated_at": created_at,
        "source": "Employee Portal"
    }

    # Step 5: Save the ticket in MongoDB.
    try:
        db["tickets"].insert_one(ticket)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not save the ticket. Please try again."
        ) from exc

    # Step 6: Create the mock ServiceNow incident.
    try:
        incident = create_mock_incident(ticket)

        db["tickets"].update_one(
            {"ticket_reference": ticket_reference},
            {
                "$set": {
                    "servicenow_number": incident["number"],
                    "servicenow_status": incident["state"],
                    "servicenow_integration": "MOCK"
                }
            }
        )

        ticket["servicenow_number"] = incident["number"]
        ticket["servicenow_status"] = incident["state"]
        ticket["servicenow_integration"] = "MOCK"

    except Exception as exc:
        print(f"Mock ServiceNow integration failed: {exc}")

        db["tickets"].update_one(
            {"ticket_reference": ticket_reference},
            {
                "$set": {
                    "servicenow_status": "Failed",
                    "servicenow_integration": "MOCK"
                }
            }
        )

        ticket["servicenow_status"] = "Failed"
        ticket["servicenow_integration"] = "MOCK"

    # Step 7: Prepare the JSON response.
    ticket.pop("_id", None)
    ticket["created_at"] = ticket["created_at"].isoformat()
    ticket["updated_at"] = ticket["updated_at"].isoformat()

    return {
        "message": "Ticket created successfully.",
        "ticket": ticket
    }



@app.get("/api/tickets")
def get_tickets():
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    try:
        collection = db["tickets"]
        tickets = list(
            collection.find({}).sort("created_at", -1)
        )

        for ticket in tickets:
            ticket["_id"] = str(ticket["_id"])

        return {
            "total": len(tickets),
            "tickets": tickets
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve tickets."
        ) from exc


@app.patch("/api/tickets/{ticket_reference}/status")
def update_ticket_status(ticket_reference: str, request: dict):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    new_status = str(request.get("status", "")).strip().title()
    allowed_statuses = ["Open", "In Progress", "Resolved"]

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be Open, In Progress, or Resolved."
        )

    try:
        # Find the existing ticket.
        ticket = db["tickets"].find_one(
            {"ticket_reference": ticket_reference}
        )

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found."
            )

        # Update the ticket in MongoDB.
        db["tickets"].update_one(
            {"ticket_reference": ticket_reference},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        # Map the portal status to the mock ServiceNow state.
        service_state = {
            "Open": "New",
            "In Progress": "In Progress",
            "Resolved": "Resolved"
        }[new_status]

        servicenow_updated = False
        incident_number = ticket.get("servicenow_number")

        if incident_number:
            servicenow_updated = update_mock_incident(
                incident_number,
                service_state
            )

        # Record the integration result on the ticket.
        integration_status = (
            service_state if servicenow_updated
            else ticket.get("servicenow_status", "Unavailable")
        )

        db["tickets"].update_one(
            {"ticket_reference": ticket_reference},
            {
                "$set": {
                    "servicenow_status": integration_status
                }
            }
        )

        return {
            "message": "Ticket status updated successfully.",
            "ticket_reference": ticket_reference,
            "status": new_status,
            "servicenow_number": incident_number,
            "servicenow_status": integration_status,
            "servicenow_updated": servicenow_updated
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"Status update failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not update ticket status."
        ) from exc


# -----------------------------------------
# KNOWLEDGE BASE API
# -----------------------------------------

DEFAULT_ARTICLES = [
    {
        "title": "Troubleshooting VPN Connection Problems",
        "category": "Network",
        "keywords": ["vpn", "network", "remote access", "connection"],
        "content": (
            "If you cannot connect to the company VPN, first check that "
            "your internet connection is working. Verify that you are "
            "using the approved VPN application and company login details. "
            "Disconnect and reconnect to the VPN. If the problem continues, "
            "restart the VPN application and check for any displayed error. "
            "Do not share your password. If these steps fail, contact "
            "Network Support and include the error message."
        ),
    },
    {
        "title": "Password Reset and Expired Passwords",
        "category": "Account Access",
        "keywords": ["password", "expired", "login", "account", "reset"],
        "content": (
            "If your company password has expired, use the organization's "
            "approved password reset portal or self-service password reset "
            "process. Follow the identity verification steps. Choose a "
            "strong, unique password and never share it with anyone. If "
            "you cannot complete the reset or your account is locked, "
            "contact IT Support for identity verification and assistance."
        ),
    },
    {
        "title": "Troubleshooting Microsoft Outlook",
        "category": "Email",
        "keywords": ["outlook", "email", "mail", "inbox", "send"],
        "content": (
            "If Outlook is not sending or receiving email, check your "
            "internet connection and whether Outlook displays a connection "
            "warning. Restart Outlook and check that your mailbox is not "
            "full. If messages remain stuck in the Outbox, record any error "
            "message and contact IT Support. Never share your password or "
            "email verification codes."
        ),
    },

    
    {
        "title": "Troubleshooting Wi-Fi Connectivity",
        "category": "Network",
        "keywords": ["wifi", "wi-fi", "wireless", "internet", "network"],
        "content": (
            "If Wi-Fi is not working, check that Wi-Fi is enabled and "
            "airplane mode is disabled. Confirm that the device is "
            "connected to the correct network. Disconnect and reconnect "
            "to the network, then restart the device if needed. If the "
            "problem continues, contact IT Support."
        ),
    },
    {
        "title": "Improving Laptop Performance",
        "category": "Hardware",
        "keywords": ["slow laptop", "performance", "freezing", "memory"],
        "content": (
            "If the laptop is running slowly, save your work and close "
            "unnecessary applications. Restart the laptop if appropriate. "
            "Check available storage and install approved updates. Do not "
            "delete company files or change managed settings without "
            "authorization. Contact IT Support if the issue continues."
        ),
    },
    {
        "title": "Requesting Software Installation",
        "category": "Software",
        "keywords": [
            "install software", "application", "software request",
            "visual studio code", "installation"
        ],
        "content": (
            "Employees should request software through the approved "
            "company software catalogue or IT service portal. Include "
            "the software name and business purpose. IT may need to "
            "review licensing, security, and approval requirements "
            "before provisioning. Do not install unapproved software."
        ),
    },
    {
        "title": "Requesting Application Access",
        "category": "Account Access",
        "keywords": [
            "application access", "permission", "login",
            "access denied", "account access"
        ],
        "content": (
            "If you cannot access a company application, confirm that "
            "you are using the correct work account. Check whether the "
            "application displays an access or permission error. Submit "
            "an access request through the approved IT portal and include "
            "the application name and the error message. Access may "
            "require manager or application-owner approval."
        ),
    },

]


def ensure_default_articles():
    """Insert missing demo articles without duplicating existing ones."""
    collection = db["knowledge_articles"]

    for article in DEFAULT_ARTICLES:
        result = collection.update_one(
            {"title": article["title"]},
            {"$setOnInsert": article},
            upsert=True,
        )

        if result.upserted_id is not None:
            print("DEBUG: Inserted:", article["title"])

    print("DEBUG: MongoDB articles after:", collection.count_documents({}))


def ensure_article_embeddings():
    """Save an embedding for every knowledge article that needs one."""
    collection = db["knowledge_articles"]

    articles = list(collection.find({}))

    for article in articles:
        embedding = article.get("embedding")

        if not isinstance(embedding, list) or len(embedding) != 384:
            text = article_to_text(article)
            embedding = create_embedding(text)

            collection.update_one(
                {"_id": article["_id"]},
                {"$set": {"embedding": embedding}},
            )

@app.get("/api/knowledge-base")
def get_knowledge_articles():
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    try:
        collection = db["knowledge_articles"]

        # Add demo articles only if the collection is empty.
        # Repeated requests will not add duplicate seed articles.
        ensure_default_articles()
        # Generate and save embeddings in MongoDB.
        ensure_article_embeddings()

        articles = list(
            collection.find(
                {},
                {"title": 1, "category": 1, "keywords": 1, "content": 1}
            ).sort("title", 1)
        )

        for article in articles:
            article["_id"] = str(article["_id"])

        return {
            "total": len(articles),
            "articles": articles
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve knowledge articles."
        ) from exc



# -----------------------------------------
# KNOWLEDGE BASE CHATBOT API
# -----------------------------------------
@app.post("/api/chat")
def knowledge_chat(payload: dict):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    question = str(payload.get("question", "")).strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    try:
        collection = db["knowledge_articles"]

        # Insert default articles only when the collection is empty.
        ensure_default_articles()

        # Make sure every article has a saved embedding.
        ensure_article_embeddings()

        articles = list(collection.find({}))

        # Step 1: Retrieve relevant articles using semantic search.
        results = search_articles(
            question=question,
            articles=articles,
            top_k=3,
            minimum_score=0.40,
        )
        # Step 2: Escalate if no article is sufficiently relevant.
        
        if not results:
            return {
                "answer": (
                    "I could not find a sufficiently relevant article "
                    "in the knowledge base. Please contact IT Support "
                    "or create a support ticket for further assistance."
                ),
                "sources": [],
                "confidence": 0.0,
                "escalation_recommended": True,
            }


        # Step 3: Prepare context from the retrieved articles.
        context_parts = []

        for result in results:
            article = result["article"]

            context_parts.append(
                f"Title: {article.get('title', '')}\n"
                f"Category: {article.get('category', '')}\n"
                f"Content: {article.get('content', '')}"
            )

        context = "\n\n".join(context_parts)

        # Step 4: Ask the local Ollama model to generate an answer.
        try:
            answer = generate_grounded_answer(
                question=question,
                context=context
            )

            source_results = results

        except Exception:
            # If Ollama is unavailable, return the best article instead.
            best_article = results[0]["article"]

            answer = best_article.get(
                "content",
                "No article content is available."
            )

            source_results = [results[0]]

                # Step 5: Return the answer and its knowledge-base sources.
        sources = [
            {
                "title": result["article"].get("title", ""),
                "category": result["article"].get("category", "")
            }
            for result in source_results
        ]

        best_score = float(source_results[0]["score"])

        return {
            "answer": answer,
            "sources": sources,
            "confidence": round(best_score, 2),
            "escalation_recommended": False
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The knowledge chatbot could not process your question."
        ) from exc


    
@app.post("/api/self-healing/password-reset")
def password_reset_workflow(request: dict):
    description = str(request.get("description", "")).strip()
    ticket_reference = request.get("ticket_reference")

    if not description:
        raise HTTPException(
            status_code=400,
            detail="Please enter a password-related issue."
        )

    if ticket_reference is not None:
        ticket_reference = str(ticket_reference).strip()

    try:
        return run_password_reset(
            description=description,
            ticket_reference=ticket_reference or None,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        print(f"Self-healing workflow failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not complete the self-healing workflow."
        ) from exc

@app.post("/api/provisioning")
def create_provisioning_request(request: dict):
    software_name = str(
        request.get("software_name", "")
    ).strip()

    employee = str(
        request.get("employee", "Employee")
    ).strip()

    if not software_name:
        raise HTTPException(
            status_code=400,
            detail="Please provide a software name."
        )

    try:
        result = create_software_request(
            software_name=software_name,
            employee=employee or "Employee",
        )

        return {
            "message": "Software request created successfully.",
            "request": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        print(f"Provisioning request failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not create the software request."
        ) from exc


@app.get("/api/provisioning")
def get_provisioning_requests():
    try:
        requests = list_software_requests()

        return {
            "total": len(requests),
            "requests": requests,
        }

    except Exception as exc:
        print(f"Could not load provisioning requests: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not load software requests."
        ) from exc
