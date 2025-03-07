"""Configuration file for pytest."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """For configuring pytest with custom markers."""
    config.addinivalue_line(
        "markers", "config: custom marker for Jekyll config file tests."
    )
    config.addinivalue_line(
        "markers", "debug: custom marker for debugging tests."
    )
    config.addinivalue_line(
        "markers", "fixture: custom marker for fixture tests."
    )
    config.addinivalue_line("markers", "git: custom marker for git tests.")
    config.addinivalue_line("markers", "jekyll: custom marker for git tests.")
    config.addinivalue_line(
        "markers", "make: custom marker for Makefile tests."
    )
    config.addinivalue_line(
        "markers", "utils: custom marker for utility tests."
    )
    config.addinivalue_line(
        "markers", "website: custom marker for website tests."
    )
