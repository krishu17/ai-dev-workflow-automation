import os

os.environ["LLM_PROVIDER"] = "mock"

from src.boilerplate import generate_module, write_scaffold  # noqa: E402


def test_generate_module_returns_filename_code_and_test():
    scaffold = generate_module("a Point dataclass with x and y fields")
    assert scaffold.filename.endswith(".py")
    assert "class" in scaffold.code
    assert "def test_" in scaffold.test_code


def test_write_scaffold_creates_both_files(tmp_path):
    scaffold = generate_module("a Counter class with an increment method")
    write_scaffold(scaffold, str(tmp_path))

    module_path = tmp_path / scaffold.filename
    test_path = tmp_path / f"test_{scaffold.filename}"
    assert module_path.exists()
    assert test_path.exists()
    assert module_path.read_text() == scaffold.code
