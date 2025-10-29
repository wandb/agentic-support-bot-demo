"""Starter tools - You'll improve these through the tutorial."""

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
# TODO: Add descriptions and parameter details to help the agent understand when to use these tools
TOOLS = [
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-create_issue",
            }
        },
        "implementation": create_issue
    },
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-get_issue",
            }
        },
        "implementation": get_issue
    }
]


