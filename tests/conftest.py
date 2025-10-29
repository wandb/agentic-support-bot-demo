"""Pytest configuration and fixtures to prevent real API calls."""

import os
import pytest
from unittest.mock import patch
from tinydb import TinyDB


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables to prevent real API calls."""
    with patch.dict(
        os.environ,
        {
            "WANDB_API_KEY": "test-wandb-key",
            "OPENAI_API_KEY": "test-openai-key",
            "PLAYGROUND_API_KEY": "dummy",  # For playground server authentication tests
        },
        clear=True,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_weave():
    """Mock weave.init to prevent real Weave API calls."""
    with patch("weave.init"):
        yield


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for isolated testing.
    
    Each test gets its own temporary database file that is cleaned up
    automatically after the test completes.
    """
    db_path = tmp_path / "test_tickets.json"
    yield str(db_path)
    # Cleanup handled automatically by tmp_path


@pytest.fixture
def seeded_db(tmp_path):
    """Provide a database pre-populated with 5 sample tickets.
    
    Returns:
        tuple: (db_path: str, ticket_ids: list[str]) where ticket_ids contains
               the IDs of the pre-seeded tickets for easy retrieval in tests.
    """
    db_path = tmp_path / "seeded_tickets.json"
    db = TinyDB(str(db_path))
    
    # Create 5 realistic sample tickets
    sample_tickets = [
        {
            "id": "10234",
            "title": "API timeout errors in production",
            "description": "Getting 504 errors when calling /api/v1/runs endpoint",
            "status": "open",
            "priority": "high",
            "created_at": "2025-10-29T10:00:00Z",
            "updated_at": "2025-10-29T10:00:00Z",
        },
        {
            "id": "10567",
            "title": "Authentication issues with OIDC",
            "description": "Users unable to log in via SSO",
            "status": "in_progress",
            "priority": "high",
            "created_at": "2025-10-29T09:00:00Z",
            "updated_at": "2025-10-29T11:00:00Z",
        },
        {
            "id": "10892",
            "title": "Traces not showing up in UI",
            "description": "Trace data is being logged but not visible in the web interface",
            "status": "open",
            "priority": "medium",
            "created_at": "2025-10-29T08:00:00Z",
            "updated_at": "2025-10-29T08:00:00Z",
        },
        {
            "id": "11234",
            "title": "Need help with custom metrics",
            "description": "How do I log custom evaluation metrics to Weave?",
            "status": "resolved",
            "priority": "low",
            "created_at": "2025-10-28T15:00:00Z",
            "updated_at": "2025-10-29T09:00:00Z",
        },
        {
            "id": "11789",
            "title": "Dataset upload failing",
            "description": "Large dataset uploads timing out after 5 minutes",
            "status": "open",
            "priority": "medium",
            "created_at": "2025-10-29T07:00:00Z",
            "updated_at": "2025-10-29T07:00:00Z",
        },
    ]
    
    for ticket in sample_tickets:
        db.insert(ticket)
    
    db.close()
    
    ticket_ids = [t["id"] for t in sample_tickets]
    yield str(db_path), ticket_ids
    # Cleanup handled automatically by tmp_path

