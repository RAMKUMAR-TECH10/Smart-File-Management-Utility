"""Search and SQLite history integration tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from file_search import SearchFilters, search_files  # noqa: E402
from history_manager import HistoryManager  # noqa: E402


class TestSearchAndHistory(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "Python_Basics.pdf").write_text("pdf")
        (self.root / "notes.txt").write_text("notes")
        nested = self.root / "sub"
        nested.mkdir()
        (nested / "Python_Project.py").write_text("print('hello')")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_by_keyword_and_extension(self) -> None:
        results = search_files(self.root, SearchFilters(keyword="Python"))
        self.assertEqual(len(results), 2)
        results = search_files(self.root, SearchFilters(keyword="Python", extension="py"))
        self.assertEqual([item.name for item in results], ["Python_Project.py"])
        self.assertEqual(search_files(self.root, SearchFilters(keyword="missing")), [])

    def test_recursive_flag_and_category(self) -> None:
        results = search_files(self.root, SearchFilters(keyword="Python", recursive=False))
        self.assertEqual([item.name for item in results], ["Python_Basics.pdf"])
        results = search_files(self.root, SearchFilters(category="Documents"))
        self.assertEqual(len(results), 2)

    def test_invalid_filters(self) -> None:
        valid, _ = SearchFilters().validate()
        self.assertFalse(valid)
        valid, _ = SearchFilters(keyword="a", min_size_mb=-1).validate()
        self.assertFalse(valid)
        valid, _ = SearchFilters(keyword="a", min_size_mb=5, max_size_mb=1).validate()
        self.assertFalse(valid)

    def test_history_round_trip(self) -> None:
        history = HistoryManager(self.root / "history.db")
        self.assertTrue(history.record("Rename", self.root / "old.txt", destination=self.root / "new.txt"))
        self.assertTrue(history.record("Delete", self.root / "bad.pdf", status="Failed"))
        records = history.get_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["operation"], "Delete")
        self.assertEqual(records[1]["status"], "Success")
        self.assertEqual(len(history.search("old")), 1)
        self.assertTrue(history.clear())
        self.assertEqual(history.get_all(), [])
        history.close()


if __name__ == "__main__":
    unittest.main()
