"""File operation tests using temporary directories only."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import file_operations  # noqa: E402
from file_operations import (  # noqa: E402
    copy_file,
    create_folder,
    delete_empty_folder,
    delete_file,
    move_file,
    rename_file,
    restore_from_recycle,
)


class RecordingHistory:
    def __init__(self) -> None:
        self.actions: list[tuple] = []

    def record(self, operation: str, path: object, status: str, destination: object = "", details: str = "") -> None:
        self.actions.append((operation, str(path), status, str(destination)))


class TestFileOperations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)
        self.source = self.folder / "source.txt"
        self.source.write_text("Hello Python")
        self.history = RecordingHistory()

        home_patch = patch.object(Path, "home", return_value=self.folder)
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_copy_file(self) -> None:
        destination = self.folder / "copy.txt"
        result = copy_file(self.source, destination, history=self.history)
        self.assertEqual(result, "Copied source.txt successfully")
        self.assertTrue(result.success)
        self.assertTrue(destination.exists())
        self.assertEqual(destination.read_text(), "Hello Python")
        self.assertEqual(self.history.actions[-1][0], "Copy")

    def test_copy_to_folder_and_collision(self) -> None:
        target_folder = self.folder / "backup"
        target_folder.mkdir()
        self.assertTrue(copy_file(self.source, target_folder).success)
        blocked = copy_file(self.source, target_folder)
        self.assertFalse(blocked.success)
        self.assertIn("already exists", str(blocked))
        self.assertTrue(copy_file(self.source, target_folder, overwrite=True).success)

    def test_rename_and_collision_prevention(self) -> None:
        result = rename_file(self.source, "renamed.txt", self.history)
        self.assertTrue(result.success)
        self.assertTrue((self.folder / "renamed.txt").exists())
        (self.folder / "taken.txt").write_text("other")
        blocked = rename_file(self.folder / "renamed.txt", "taken.txt")
        self.assertFalse(blocked.success)
        self.assertIn("already exists", str(blocked))
        self.assertFalse(rename_file(self.source, "bad/name.txt").success)

    def test_move_file(self) -> None:
        destination = self.folder / "moved"
        destination.mkdir()
        result = move_file(self.source, destination, self.history)
        self.assertTrue(result.success)
        self.assertTrue((destination / "source.txt").exists())
        self.assertFalse(self.source.exists())

    def test_create_folder(self) -> None:
        result = create_folder(self.folder, "New Folder", self.history)
        self.assertTrue(result.success)
        self.assertTrue((self.folder / "New Folder").is_dir())
        self.assertFalse(create_folder(self.folder, "New Folder").success)
        self.assertFalse(create_folder(self.folder, "bad:name").success)

    def test_delete_requires_confirmation_and_is_recoverable(self) -> None:
        blocked = delete_file(self.source)
        self.assertFalse(blocked.success)
        self.assertTrue(self.source.exists())
        result = delete_file(self.source, confirmed=True, history=self.history)
        self.assertTrue(result.success)
        self.assertFalse(self.source.exists())
        recovery = Path(result.details["recovery_path"])
        self.assertTrue(recovery.exists())
        restored = restore_from_recycle(recovery, self.folder / "source.txt")
        self.assertTrue(restored.success)
        self.assertTrue((self.folder / "source.txt").exists())

    def test_permanent_delete_and_empty_folder(self) -> None:
        empty = self.folder / "empty"
        empty.mkdir()
        self.assertFalse(delete_empty_folder(empty).success)
        self.assertTrue(delete_empty_folder(empty, confirmed=True).success)
        self.assertFalse(empty.exists())
        result = delete_file(self.source, confirmed=True, safe_delete=False)
        self.assertTrue(result.success)
        self.assertFalse(self.source.exists())

    def test_protected_paths_blocked(self) -> None:
        with patch.object(file_operations, "is_protected_path", return_value=True):
            result = copy_file(self.source, self.folder / "protected.txt")
            self.assertFalse(result.success)
            self.assertIn("Protected", str(result))


if __name__ == "__main__":
    unittest.main()
