"""Custom tools for the support bot agent."""

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
        weave.init("agentic-support-bot-demo")
    except Exception as e:
        # Log warning but continue - observability shouldn't block tool usage
        print(f"Warning: Failed to initialize Weave: {e}")


def create_issue(title: str, description: str, priority: str = "medium") -> dict:
    """
    Create a new support issue with a title, description, and optional priority level.
    
    Args:
        title: The title of the issue
        description: A detailed description of the issue
        priority: Priority level (low, medium, high). Defaults to medium.
        
    Returns:
        A dictionary containing the created issue details with id, title,
        description, status, priority, and created_at timestamp.
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
    """
    Retrieve an existing issue by its unique identifier.
    
    Args:
        issue_id: The unique identifier of the issue to retrieve
        
    Returns:
        A dictionary containing the issue details with id, title, description,
        status, priority, created_at, and updated_at timestamps.
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


# Export tools for tyler chat CLI
TOOLS = [create_issue, get_issue]

