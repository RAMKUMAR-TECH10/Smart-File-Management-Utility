"""Automatic organizer tests (preview before apply)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from file_organizer import apply_organization_plan, build_organization_plan, get_category  # noqa: E402


class TestOrganizer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for name in ("image1.jpg", "document.pdf", "notes.docx", "song.mp3", "program.py", "mystery.xyz"):
            (self.root / name).write_text(name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_categories(self) -> None:
        self.assertEqual(get_category("photo.PNG"), "Images")
        self.assertEqual(get_category("report.pdf"), "Documents")
        self.assertEqual(get_category("song.mp3"), "Audio")
        self.assertEqual(get_category("mystery.xyz"), "Others")

    def test_preview_is_non_destructive(self) -> None:
        items, warnings = build_organization_plan(self.root)
        self.assertEqual(len(items), 6)
        self.assertEqual(warnings, [])
        self.assertTrue((self.root / "image1.jpg").exists())
        self.assertEqual({item.category for item in items},
                         {"Images", "Documents", "Audio", "Code", "Others"})

    def test_selected_categories(self) -> None:
        items, _ = build_organization_plan(self.root, ["Images"])
        self.assertEqual([item.source.name for item in items], ["image1.jpg"])

    def test_apply_requires_confirmation(self) -> None:
        items, _ = build_organization_plan(self.root, ["Documents"])
        summary = apply_organization_plan(items, confirmed=False)
        self.assertEqual(summary.applied, [])
        self.assertTrue((self.root / "document.pdf").exists())

    def test_apply_moves_files_into_category_folders(self) -> None:
        items, _ = build_organization_plan(self.root, ["Images", "Documents"])
        summary = apply_organization_plan(items, confirmed=True)
        self.assertEqual(len(summary.applied), 3)
        self.assertTrue((self.root / "Images" / "image1.jpg").exists())
        self.assertTrue((self.root / "Documents" / "document.pdf").exists())
        self.assertFalse((self.root / "document.pdf").exists())

    def test_conflicts_are_skipped(self) -> None:
        (self.root / "Documents").mkdir()
        (self.root / "Documents" / "document.pdf").write_text("existing")
        items, warnings = build_organization_plan(self.root, ["Documents"])
        self.assertTrue(any("already exists" in warning for warning in warnings))
        self.assertTrue(items[0].conflict)
        summary = apply_organization_plan(items, confirmed=True)
        self.assertEqual(len(summary.applied), 1)
        self.assertEqual(len(summary.skipped), 1)
        self.assertEqual((self.root / "Documents" / "document.pdf").read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
