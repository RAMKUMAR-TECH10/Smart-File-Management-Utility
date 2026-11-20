"""Validation layer tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation import (  # noqa: E402
    ensure_within_scope,
    is_protected_path,
    validate_delete,
    validate_destination,
    validate_extension,
    validate_file,
    validate_filename,
    validate_folder,
    validate_move,
    validate_search_keyword,
    validate_file_size,
)


class TestValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.folder = self.root / "Documents"
        self.folder.mkdir()
        self.file = self.folder / "notes.txt"
        self.file.write_text("hello")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_existing_folder_and_file(self) -> None:
        self.assertTrue(validate_folder(self.folder))
        self.assertTrue(validate_file(self.file))
        self.assertFalse(validate_folder(self.file))
        self.assertFalse(validate_file(self.folder))
        self.assertFalse(validate_folder(self.root / "missing"))

    def test_valid_and_invalid_filenames(self) -> None:
        self.assertTrue(validate_filename("Python_Project.py"))
        self.assertTrue(validate_filename("my notes.docx"))
        self.assertFalse(validate_filename(""))
        self.assertFalse(validate_filename("Invalid/File.py"))
        self.assertFalse(validate_filename("bad:name?.txt"))
        self.assertFalse(validate_filename("trailing."))
        self.assertFalse(validate_filename(".."))

    def test_extensions_keywords_sizes_and_destination(self) -> None:
        self.assertTrue(validate_extension(".py"))
        self.assertTrue(validate_extension("tar.gz"))
        self.assertFalse(validate_extension("bad extension"))
        self.assertFalse(validate_search_keyword("   "))
        self.assertTrue(validate_search_keyword("Python"))
        self.assertTrue(validate_file_size(0))
        self.assertFalse(validate_file_size(-1))
        self.assertTrue(validate_destination(self.folder))
        self.assertFalse(validate_destination(self.root / "missing"))

    def test_protected_paths_and_scope(self) -> None:
        self.assertTrue(is_protected_path(self.root.anchor))
        self.assertFalse(is_protected_path(self.folder))
        self.assertTrue(ensure_within_scope(self.file, self.root))
        outside = self.root.parent / "unrelated_path_xyz"
        self.assertFalse(ensure_within_scope(outside, self.root))
        allowed, _ = validate_delete(self.file)
        self.assertTrue(allowed)
        denied, _ = validate_delete(self.root.anchor)
        self.assertFalse(denied)

    def test_move_into_itself_is_rejected(self) -> None:
        allowed, reason = validate_move(self.folder, self.folder / "child")
        self.assertFalse(allowed)
        self.assertIn("into itself", reason)
        allowed, _ = validate_move(self.file, self.root / "copy.txt")
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
