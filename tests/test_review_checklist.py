import os

os.environ["LLM_PROVIDER"] = "mock"

from src.review_checklist import generate_checklist  # noqa: E402


def test_checklist_always_includes_testing_item():
    items = generate_checklist("Refactored a utility function for formatting dates.")
    categories = [i.category for i in items]
    assert "Testing" in categories


def test_checklist_flags_security_for_auth_changes():
    items = generate_checklist("Added a new token-based auth check to the login flow.")
    categories = [i.category for i in items]
    assert "Security" in categories
    security_item = next(i for i in items if i.category == "Security")
    assert security_item.severity == "high"


def test_checklist_flags_migration_for_schema_changes():
    items = generate_checklist("Added a new database migration for the accounts table.")
    categories = [i.category for i in items]
    assert "Migration" in categories
