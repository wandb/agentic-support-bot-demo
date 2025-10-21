"""Custom tools for the agent - Step 2b with good docstrings."""

import os
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv
import weave

# Load environment variables
load_dotenv()

# Initialize Weave for observability if API key is present
if os.getenv("WANDB_API_KEY"):
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
    except Exception as e:
        print(f"Warning: Failed to initialize Weave: {e}")


def create_issue(*, title: str, description: str, priority: str = "medium") -> dict:
    # TODO: Add a better description explaining when to use this tool
    issue_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    return {
        "id": issue_id,
        "title": title,
        "description": description,
        "status": "open",
        "priority": priority,
        "created_at": created_at,
    }


def get_issue(*, issue_id: str) -> dict:
    # TODO: Add a better description explaining when to use this tool
    created_at = datetime.now(timezone.utc).isoformat()
    updated_at = datetime.now(timezone.utc).isoformat()
    
    return {
        "id": issue_id,
        "title": f"Mock Issue {issue_id}",
        "description": f"This is a mock issue retrieved for ID: {issue_id}",
        "status": "in_progress",
        "priority": "medium",
        "created_at": created_at,
        "updated_at": updated_at,
    }


# Export tools for Slide framework
TOOLS = [
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-create_issue",
                "description": "Create a support ticket",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Brief summary"},
                        "description": {"type": "string", "description": "Details"},
                        "priority": {
                            "type": "string",
                            "description": "Urgency",
                            "enum": ["low", "medium", "high"],
                            "default": "medium"
                        }
                    },
                    "required": ["title", "description"]
                }
            }
        },
        "implementation": create_issue
    },
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-get_issue",
                "description": "Get ticket status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string", "description": "Ticket ID"}
                    },
                    "required": ["issue_id"]
                }
            }
        },
        "implementation": get_issue
    }
]

