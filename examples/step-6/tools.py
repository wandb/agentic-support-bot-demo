"""Starter tools - You'll improve these through the tutorial."""

import os
import random
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import weave
from tinydb import TinyDB, Query

# Load environment variables
load_dotenv()

# Note: Weave initialization is handled by server.py
# Tools are automatically traced when used by a Weave-initialized agent

# Database configuration
# When tools.py is in workspace/, database is in workspace/db/
WORKSPACE_DIR = Path(__file__).parent
DB_DIR = WORKSPACE_DIR / "db"
DB_PATH = os.getenv("TICKETS_DB_PATH", str(DB_DIR / "tickets.json"))

# Initialize database
def _init_database():
    """Initialize the ticket database, ensuring it exists."""
    db_path = Path(DB_PATH)
    # Sample file is at project root db/ directory
    project_root = WORKSPACE_DIR.parent
    sample_path = project_root / "db" / "tickets.sample.json"
    
    # Ensure db directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if database exists
    if not db_path.exists():
        raise FileNotFoundError(
            f"\n{'='*70}\n"
            f"❌ Ticket database not found at: {db_path}\n\n"
            f"Please set up the database by copying the sample data:\n"
            f"  mkdir -p {db_path.parent}\n"
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
    """Create a new support ticket in the system."""
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
    """Retrieve details of an existing support ticket by its ID."""
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
                "description": "Create a new support ticket in the system. Use this when a customer reports a new issue, bug, or feature request that needs to be tracked. Returns the created ticket with its unique ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "A brief, descriptive title summarizing the issue (e.g., 'Login page not loading')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the issue including steps to reproduce, expected behavior, and actual behavior"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Priority level: 'high' for critical/blocking issues, 'medium' for standard issues, 'low' for minor issues or enhancements",
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
                "description": "Retrieve details of an existing support ticket by its ID. Use this to look up ticket status, description, and other details when a customer asks about an existing issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_id": {
                            "type": "string",
                            "description": "The unique 5-digit ticket ID (e.g., '12345')"
                        }
                    },
                    "required": ["issue_id"]
                }
            }
        },
        "implementation": get_issue
    }
]

