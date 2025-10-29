"""Tests for support ticket tools with TinyDB persistence."""

import importlib.util
from pathlib import Path
from tinydb import TinyDB, Query
import tempfile
import os


def load_tools_module(db_path):
    """Load tools module with a specific DB path."""
    # Set env var before loading
    os.environ["TICKETS_DB_PATH"] = str(db_path)
    
    # Load the tools module directly
    tools_path = Path(__file__).parent.parent / "examples" / "step-3" / "tools.py"
    spec = importlib.util.spec_from_file_location("tools", tools_path)
    tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    return tools


class TestCreateIssue:
    """Tests for create_issue function."""
    
    def test_create_issue_generates_valid_id(self):
        """AC: Created ticket should have a valid ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            result = tools.create_issue(
                title="Test Issue",
                description="Test description"
            )
            
            assert "id" in result
            assert isinstance(result["id"], str)
            assert len(result["id"]) == 5  # 5-digit ID
            assert result["id"].isdigit()
    
    def test_create_issue_persists(self):
        """AC1: Create ticket saves to tickets.json with all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            result = tools.create_issue(
                title="Persistent Test",
                description="This should be saved",
                priority="high"
            )
            
            # Verify the ticket was actually saved to the database
            db = TinyDB(str(db_path))
            TicketQuery = Query()
            saved_ticket = db.search(TicketQuery.id == result["id"])
            
            assert len(saved_ticket) == 1
            assert saved_ticket[0]["title"] == "Persistent Test"
            assert saved_ticket[0]["description"] == "This should be saved"
            assert saved_ticket[0]["status"] == "open"
            assert saved_ticket[0]["priority"] == "high"
            assert "created_at" in saved_ticket[0]
            assert "updated_at" in saved_ticket[0]
            
            db.close()
    
    def test_create_issue_validates_priority(self):
        """Input validation: priority should be validated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            # Valid priority should work
            result = tools.create_issue(
                title="Test",
                description="Test",
                priority="low"
            )
            assert result["priority"] == "low"
            
            result = tools.create_issue(
                title="Test",
                description="Test",
                priority="medium"
            )
            assert result["priority"] == "medium"
            
            result = tools.create_issue(
                title="Test",
                description="Test",
                priority="high"
            )
            assert result["priority"] == "high"


class TestGetIssue:
    """Tests for get_issue function."""
    
    def test_get_issue_returns_created_ticket(self):
        """AC2: Get ticket returns exact created data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            # Create a ticket
            created = tools.create_issue(
                title="Integration Test",
                description="Testing create then get",
                priority="medium"
            )
            
            # Retrieve it
            retrieved = tools.get_issue(issue_id=created["id"])
            
            # Should return exact same data
            assert retrieved["id"] == created["id"]
            assert retrieved["title"] == created["title"]
            assert retrieved["description"] == created["description"]
            assert retrieved["status"] == created["status"]
            assert retrieved["priority"] == created["priority"]
            assert retrieved["created_at"] == created["created_at"]
    
    def test_get_issue_not_found(self):
        """AC3: Get non-existent ticket returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            result = tools.get_issue(issue_id="99999")
            
            assert "error" in result
            assert result["id"] == "99999"
            assert "not found" in result["error"].lower()
    
    def test_get_preseeded_tickets(self):
        """AC4: Pre-seeded tickets are retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "seeded_tickets.json"
            
            # Create seeded DB
            db = TinyDB(str(db_path))
            ticket_ids = ["10234", "10567", "10892", "11234", "11789"]
            for ticket_id in ticket_ids:
                db.insert({
                    "id": ticket_id,
                    "title": f"Ticket {ticket_id}",
                    "description": "Test ticket",
                    "status": "open",
                    "priority": "medium",
                    "created_at": "2025-10-29T10:00:00Z",
                    "updated_at": "2025-10-29T10:00:00Z",
                })
            db.close()
            
            tools = load_tools_module(db_path)
            
            # Should be able to retrieve all pre-seeded tickets
            for ticket_id in ticket_ids:
                result = tools.get_issue(issue_id=ticket_id)
                
                assert "error" not in result
                assert result["id"] == ticket_id
                assert "title" in result
                assert "description" in result


class TestMultipleTickets:
    """Tests for multiple ticket handling."""
    
    def test_multiple_tickets_isolated(self):
        """AC5: Multiple tickets don't cross-contaminate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module(db_path)
            
            # Create 3 different tickets
            ticket1 = tools.create_issue(
                title="Ticket 1",
                description="Description 1",
                priority="low"
            )
            ticket2 = tools.create_issue(
                title="Ticket 2",
                description="Description 2",
                priority="medium"
            )
            ticket3 = tools.create_issue(
                title="Ticket 3",
                description="Description 3",
                priority="high"
            )
            
            # Retrieve each and verify they're distinct
            retrieved1 = tools.get_issue(issue_id=ticket1["id"])
            retrieved2 = tools.get_issue(issue_id=ticket2["id"])
            retrieved3 = tools.get_issue(issue_id=ticket3["id"])
            
            assert retrieved1["title"] == "Ticket 1"
            assert retrieved1["description"] == "Description 1"
            assert retrieved1["priority"] == "low"
            
            assert retrieved2["title"] == "Ticket 2"
            assert retrieved2["description"] == "Description 2"
            assert retrieved2["priority"] == "medium"
            
            assert retrieved3["title"] == "Ticket 3"
            assert retrieved3["description"] == "Description 3"
            assert retrieved3["priority"] == "high"
            
            # All should have unique IDs
            assert ticket1["id"] != ticket2["id"]
            assert ticket2["id"] != ticket3["id"]
            assert ticket1["id"] != ticket3["id"]


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_db_raises_error_if_missing(self):
        """AC6: DB raises clear error if not set up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "new_tickets.json"
            
            # DB file should not exist
            assert not db_path.exists()
            
            # Should raise FileNotFoundError with helpful message
            try:
                tools = load_tools_module(db_path)
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError as e:
                assert "Ticket database not found" in str(e)
                assert "cp" in str(e)  # Should suggest copy command
