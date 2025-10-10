"""Custom tools for the support bot agent."""

from datetime import datetime, timezone
from uuid import uuid4


def create_issue(title: str, description: str, priority: str = "medium") -> dict:
    """
    Create a new support issue (stub implementation).
    
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
    Retrieve an issue by ID (stub implementation).
    
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


def get_tools() -> list:
    """
    Get the list of custom tools for the agent.
    
    Returns:
        List of tool definitions in Tyler format.
    """
    return [
        {
            "definition": {
                "type": "function",
                "function": {
                    "name": "create_issue",
                    "description": "Create a new support issue with a title, description, and optional priority level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the issue"
                            },
                            "description": {
                                "type": "string",
                                "description": "A detailed description of the issue"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority level: low, medium, or high",
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
                    "name": "get_issue",
                    "description": "Retrieve an existing issue by its unique identifier",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "issue_id": {
                                "type": "string",
                                "description": "The unique identifier of the issue to retrieve"
                            }
                        },
                        "required": ["issue_id"]
                    }
                }
            },
            "implementation": get_issue
        }
    ]

