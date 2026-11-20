"""Duplicate detection tests (hash grouping and manual deletion)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from duplicate_finder import delete_duplicates, find_duplicates, hash_file  # noqa: E402


class TestDuplicateFinder(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.nested = self.root / "nested"
        self.nested.mkdir()
        (self.root / "photo1.jpg").write_bytes(b"same image content")
        (self.nested / "photo2.jpg").write_bytes(b"same image content")
        (self.root / "other.jpg").write_bytes(b"different content")

        home_patch = patch.object(Path, "home", return_value=self.root)
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_hash_and_groups(self) -> None:
        expected = hash_file(self.root / "photo1.jpg")
        self.assertEqual(len(expected), 64)
        report = find_duplicates(self.root)
        self.assertEqual(report.files_scanned, 3)
        self.assertEqual(len(report.groups), 1)
        self.assertEqual(report.duplicate_count, 2)
        self.assertEqual(report.groups[0].file_hash, expected)
        self.assertEqual(report.total_wasted_bytes, len(b"same image content"))

    def test_scan_does_not_delete_anything(self) -> None:
        find_duplicates(self.root)
        self.assertTrue((self.root / "photo1.jpg").exists())
        self.assertTrue((self.nested / "photo2.jpg").exists())

    def test_deletion_requires_confirmation(self) -> None:
        duplicate = self.nested / "photo2.jpg"
        results = delete_duplicates([duplicate], confirmed=False)
        self.assertFalse(results[0].success)
        self.assertTrue(duplicate.exists())

    def test_manual_deletion_of_selected_copy(self) -> None:
        duplicate = self.nested / "photo2.jpg"
        results = delete_duplicates([duplicate], confirmed=True)
        self.assertTrue(results[0].success)
        self.assertFalse(duplicate.exists())
        self.assertTrue((self.root / "photo1.jpg").exists())

    def test_minimum_size_filter(self) -> None:
        report = find_duplicates(self.root, min_size=10_000)
        self.assertEqual(report.files_scanned, 0)
        self.assertEqual(report.groups, [])


if __name__ == "__main__":
    unittest.main()
