import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("PYTHON2RUST_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("PYTHON2RUST_MAX_FIXES_PER_ATTEMPT", "2")

@pytest.fixture
def test_output_dir():
    """Create and clean up a test output directory."""
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    yield output_dir
    
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)

@pytest.fixture
def mock_verification_rules():
    """Sample verification rules for testing."""
    return {
        "ignorable_differences": [
            "Choice of equivalent libraries/crates",
            "Memory management approaches"
        ],
        "critical_differences": {
            "core": [
                "Algorithm correctness",
                "State management"
            ],
            "routing": {
                "paths": "Must use exact same URL paths"
            },
            "image": {
                "dimensions": "Must match Python's dimensions"
            }
        }
    }