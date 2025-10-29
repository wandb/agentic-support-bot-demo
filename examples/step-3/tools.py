"""Custom tools for the W&B support bot - Final polished version."""

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
    """Create a new support ticket for a user's problem or request.
    
    **When to use this tool:**
    - User reports a bug, error, or problem with W&B
    - User requests help or assistance with something
    - User describes an issue they're experiencing
    - User asks for a feature or enhancement
    
    **Example user requests:**
    - "I'm getting API timeout errors"
    - "Can you help me with authentication issues?"
    - "Create a ticket for my problem with traces not showing up"
    - "I need help setting up W&B in my project"
    
    Args:
        title: Brief, clear summary of the issue (e.g., "API timeout errors in production")
        description: Detailed description of the problem, including any error messages,
                    steps to reproduce, or context the user provided
        priority: Urgency level - use "high" for critical issues affecting production,
                 "medium" (default) for standard issues, "low" for minor questions
        
    Returns:
        Dictionary containing the created support ticket:
        - id: Unique ticket ID
        - title: Issue title
        - description: Full description
        - status: Current status (always "open" for new tickets)
        - priority: Priority level
        - created_at: ISO timestamp of creation
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


def get_issue(*, issue_id: str) -> dict:
    """Retrieve the current status and details of an existing support ticket.
    
    **When to use this tool:**
    - User asks about the status of a specific ticket/issue
    - User provides an issue ID or ticket number
    - User wants an update on something they previously reported
    
    **Example user requests:**
    - "What's the status of issue #123?"
    - "Can you check ticket abc-def-ghi?"
    - "Is there any update on my problem?"
    
    Args:
        issue_id: The unique identifier of the ticket (the ID from create_issue
                 or provided by the user)
        
    Returns:
        Dictionary containing the ticket details:
        - id: The ticket ID
        - title: Issue title
        - description: Full description
        - status: Current status (e.g., "open", "in_progress", "resolved")
        - priority: Priority level
        - created_at: When the ticket was created
        - updated_at: Last update timestamp
    """
    # Mock issue retrieval for demo purposes
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
                "description": "Create a support ticket for a user's problem or request. Use when user reports a bug, error, or problem with W&B, requests help or assistance, or asks to create a support ticket.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Brief, clear summary of the issue (e.g., 'API timeout errors in production')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the problem, including any error messages, steps to reproduce, or context the user provided"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Urgency level - use 'high' for critical issues affecting production, 'medium' (default) for standard issues, 'low' for minor questions",
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
                "description": "Retrieve the current status and details of an existing support ticket. Use when user asks about the status of a specific ticket/issue, provides an issue ID or ticket number, or wants an update on something they previously reported.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_id": {
                            "type": "string",
                            "description": "The unique identifier of the ticket (the ID from create_issue or provided by the user)"
                        }
                    },
                    "required": ["issue_id"]
                }
            }
        },
        "implementation": get_issue
    }
]

