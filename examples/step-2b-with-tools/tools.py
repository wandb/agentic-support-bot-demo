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


def create_issue(title: str, description: str, priority: str = "medium") -> dict:
    """Create a new support ticket.
    
    Use this tool when the user reports a problem or requests help.
    
    Args:
        title: Brief title of the issue
        description: Detailed description of the problem
        priority: Priority level (low, medium, high). Defaults to medium.
        
    Returns:
        Dictionary containing the created issue details
    """
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


def get_issue(issue_id: str) -> dict:
    """Retrieve an existing support ticket by ID.
    
    Use this tool when the user asks about the status of a specific issue.
    
    Args:
        issue_id: The unique identifier of the issue
        
    Returns:
        Dictionary containing the issue details
    """
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


# Export tools for Tyler
TOOLS = [create_issue, get_issue]

