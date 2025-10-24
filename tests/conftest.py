"""Pytest configuration and fixtures to prevent real API calls."""

import os
import pytest
from unittest.mock import patch


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
    with patch("weave.init"), patch("tools.weave.init"):
        yield

