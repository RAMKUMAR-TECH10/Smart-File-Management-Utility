"""Storage analyzer tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage_analyzer import analyze_folder  # noqa: E402


class TestStorageAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.sub = self.root / "Videos"
        self.sub.mkdir()
        (self.root / "notes.txt").write_bytes(b"a" * 100)
        (self.sub / "clip.mp4").write_bytes(b"b" * 400)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_total_size_and_counts(self) -> None:
        report = analyze_folder(self.root)
        self.assertEqual(report.total_size, 500)
        self.assertEqual(report.file_count, 2)
        self.assertEqual(report.folder_count, 1)
        self.assertEqual(report.errors, [])

    def test_category_distribution(self) -> None:
        report = analyze_folder(self.root)
        self.assertEqual(report.by_category["Documents"], 100)
        self.assertEqual(report.by_category["Videos"], 400)

    def test_largest_items(self) -> None:
        report = analyze_folder(self.root, top=2)
        self.assertEqual(report.largest_files[0].name, "clip.mp4")
        self.assertEqual(report.largest_folders[0][0].name, "Videos")
        self.assertEqual(report.largest_folders[0][1], 400)

    def test_invalid_folder_returns_error(self) -> None:
        report = analyze_folder(self.root / "missing")
        self.assertTrue(report.errors)
        self.assertEqual(report.file_count, 0)


if __name__ == "__main__":
    unittest.main()
