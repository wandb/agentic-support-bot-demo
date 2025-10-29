"""Tests for support ticket tools with TinyDB persistence."""

from pathlib import Path
from tinydb import TinyDB, Query
from unittest.mock import patch
import sys


class TestCreateIssue:
    """Tests for create_issue function."""
    
    def test_create_issue_generates_valid_id(self, temp_db_path, monkeypatch):
        """AC: Created ticket should have a valid ID."""
        # Set the environment variable before import
        monkeypatch.setenv("TICKETS_DB_PATH", temp_db_path)
        
        # Clear modules to force reimport with new env var
        for mod in list(sys.modules.keys()):
            if mod.startswith("examples"):
                del sys.modules[mod]
        
        # Import tools with env var set
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from examples.step_3.tools import create_issue
            
            result = create_issue(
                title="Test Issue",
                description="Test description"
            )
            
            assert "id" in result
            assert isinstance(result["id"], str)
            assert len(result["id"]) > 0
    
    def test_create_issue_persists(self, temp_db_path):
        """AC1: Create ticket saves to tickets.json with all required fields."""
        with patch("examples.step_3.tools.DB_PATH", temp_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import create_issue
            
            result = create_issue(
                title="Persistent Test",
                description="This should be saved",
                priority="high"
            )
            
            # Verify the ticket was actually saved to the database
            db = TinyDB(temp_db_path)
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
    
    def test_create_issue_validates_priority(self, temp_db_path):
        """Input validation: priority should be validated."""
        with patch("examples.step_3.tools.DB_PATH", temp_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import create_issue
            
            # Valid priority should work
            result = create_issue(
                title="Test",
                description="Test",
                priority="low"
            )
            assert result["priority"] == "low"
            
            result = create_issue(
                title="Test",
                description="Test",
                priority="medium"
            )
            assert result["priority"] == "medium"
            
            result = create_issue(
                title="Test",
                description="Test",
                priority="high"
            )
            assert result["priority"] == "high"


class TestGetIssue:
    """Tests for get_issue function."""
    
    def test_get_issue_returns_created_ticket(self, temp_db_path):
        """AC2: Get ticket returns exact created data."""
        with patch("examples.step_3.tools.DB_PATH", temp_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import create_issue, get_issue
            
            # Create a ticket
            created = create_issue(
                title="Integration Test",
                description="Testing create then get",
                priority="medium"
            )
            
            # Retrieve it
            retrieved = get_issue(issue_id=created["id"])
            
            # Should return exact same data
            assert retrieved["id"] == created["id"]
            assert retrieved["title"] == created["title"]
            assert retrieved["description"] == created["description"]
            assert retrieved["status"] == created["status"]
            assert retrieved["priority"] == created["priority"]
            assert retrieved["created_at"] == created["created_at"]
    
    def test_get_issue_not_found(self, temp_db_path):
        """AC3: Get non-existent ticket returns error."""
        with patch("examples.step_3.tools.DB_PATH", temp_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import get_issue
            
            result = get_issue(issue_id="non-existent-id")
            
            assert "error" in result
            assert result["id"] == "non-existent-id"
            assert "not found" in result["error"].lower()
    
    def test_get_preseeded_tickets(self, seeded_db):
        """AC4: Pre-seeded tickets are retrievable."""
        db_path, ticket_ids = seeded_db
        
        with patch("examples.step_3.tools.DB_PATH", db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import get_issue
            
            # Should be able to retrieve all pre-seeded tickets
            for ticket_id in ticket_ids:
                result = get_issue(issue_id=ticket_id)
                
                assert "error" not in result
                assert result["id"] == ticket_id
                assert "title" in result
                assert "description" in result


class TestMultipleTickets:
    """Tests for multiple ticket handling."""
    
    def test_multiple_tickets_isolated(self, temp_db_path):
        """AC5: Multiple tickets don't cross-contaminate."""
        with patch("examples.step_3.tools.DB_PATH", temp_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import create_issue, get_issue
            
            # Create 3 different tickets
            ticket1 = create_issue(
                title="Ticket 1",
                description="Description 1",
                priority="low"
            )
            ticket2 = create_issue(
                title="Ticket 2",
                description="Description 2",
                priority="medium"
            )
            ticket3 = create_issue(
                title="Ticket 3",
                description="Description 3",
                priority="high"
            )
            
            # Retrieve each and verify they're distinct
            retrieved1 = get_issue(issue_id=ticket1["id"])
            retrieved2 = get_issue(issue_id=ticket2["id"])
            retrieved3 = get_issue(issue_id=ticket3["id"])
            
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
    """Tests for database initialization and sample data."""
    
    def test_db_auto_creates(self, tmp_path):
        """AC6: DB initializes if missing."""
        new_db_path = str(tmp_path / "new_tickets.json")
        
        # DB file should not exist yet
        assert not Path(new_db_path).exists()
        
        with patch("examples.step_3.tools.DB_PATH", new_db_path):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import create_issue
            
            # Creating a ticket should initialize the DB
            result = create_issue(
                title="First Ticket",
                description="Should create DB"
            )
            
            # DB file should now exist
            assert Path(new_db_path).exists()
            
            # And ticket should be saved
            db = TinyDB(new_db_path)
            TicketQuery = Query()
            saved = db.search(TicketQuery.id == result["id"])
            assert len(saved) == 1
            db.close()
    
    def test_sample_data_copied_on_first_run(self, tmp_path):
        """Verify sample data is copied to working DB on first import."""
        # Create a sample data file
        sample_path = tmp_path / "tickets.sample.json"
        db_path = tmp_path / "tickets.json"
        
        # Pre-populate sample file
        sample_db = TinyDB(str(sample_path))
        sample_db.insert({
            "id": "sample-ticket-1",
            "title": "Sample Issue",
            "description": "From sample data",
            "status": "open",
            "priority": "medium",
            "created_at": "2025-10-29T10:00:00Z",
            "updated_at": "2025-10-29T10:00:00Z",
        })
        sample_db.close()
        
        # Working DB should not exist yet
        assert not db_path.exists()
        
        # Mock both paths
        with patch("examples.step_3.tools.DB_PATH", str(db_path)), \
             patch("examples.step_3.tools.SAMPLE_DB_PATH", str(sample_path)):
            if "examples.step_3.tools" in sys.modules:
                del sys.modules["examples.step_3.tools"]
            from examples.step_3.tools import get_issue
            
            # Working DB should now exist (copied from sample)
            assert db_path.exists()
            
            # Should be able to retrieve sample ticket
            result = get_issue(issue_id="sample-ticket-1")
            assert result["title"] == "Sample Issue"

