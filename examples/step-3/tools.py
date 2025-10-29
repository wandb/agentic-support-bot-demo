"""Custom tools for the W&B support bot - Final polished version."""

import os
import random
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import weave
from tinydb import TinyDB, Query

# Load environment variables
load_dotenv()

# Initialize Weave for observability if API key is present
if os.getenv("WANDB_API_KEY"):
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
    except Exception as e:
        print(f"Warning: Failed to initialize Weave: {e}")

# Database configuration
PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = os.getenv("TICKETS_DB_PATH", str(DB_DIR / "tickets.json"))

# Initialize database
def _init_database():
    """Initialize the ticket database, ensuring it exists."""
    db_path = Path(DB_PATH)
    sample_path = DB_DIR / "tickets.sample.json"
    
    # Ensure db directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if database exists
    if not db_path.exists():
        raise FileNotFoundError(
            f"\n{'='*70}\n"
            f"❌ Ticket database not found at: {db_path}\n\n"
            f"Please set up the database by copying the sample data:\n"
            f"  cp {sample_path} {db_path}\n\n"
            f"This will give you 15 realistic sample tickets to work with.\n"
            f"{'='*70}\n"
        )
    
    print(f"Using ticket database at {db_path}")

# Initialize on module load
_init_database()

# Get database instance
def _get_db():
    """Get a TinyDB instance for the ticket database."""
    return TinyDB(DB_PATH)


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
    # Validate priority
    if priority not in ["low", "medium", "high"]:
        priority = "medium"
    
    # Generate a simple 5-digit ticket ID
    issue_id = str(random.randint(10000, 99999))
    created_at = datetime.now(timezone.utc).isoformat()
    
    ticket = {
        "id": issue_id,
        "title": title,
        "description": description,
        "status": "open",
        "priority": priority,
        "created_at": created_at,
        "updated_at": created_at,
    }
    
    # Persist to database
    db = _get_db()
    db.insert(ticket)
    db.close()
    
    return ticket


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
        
        Or if not found:
        - error: Error message
        - id: The requested ticket ID
    """
    # Query database for ticket
    db = _get_db()
    TicketQuery = Query()
    results = db.search(TicketQuery.id == issue_id)
    db.close()
    
    if results:
        # Return the first (and should be only) matching ticket
        return results[0]
    else:
        # Ticket not found
        print(f"Ticket not found: {issue_id}")
        return {
            "error": "Ticket not found",
            "id": issue_id
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

