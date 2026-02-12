"""Basic tests for miniclaw."""

import pytest


def test_import():
    """Test that miniclaw can be imported."""
    import miniclaw

    assert miniclaw.__version__ == "0.1.0"
