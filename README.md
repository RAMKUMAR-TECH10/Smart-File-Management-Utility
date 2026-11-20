# Smart File Management Utility

A desktop file-management application built with Python and CustomTkinter. It provides an
Explorer-style workspace for browsing files, performing safe file operations, organizing files by
extension, searching, detecting duplicates, analyzing storage, viewing metadata and reviewing an
SQLite operation history.

## 1. Project description

Users often accumulate documents, images, videos and downloads in one place. This utility centralises
the routine work of locating, organising and cleaning up those files. It works on real files and
folders chosen by the user and records every completed action in an audit trail.

## 2. Problem statement

Cluttered folders make files difficult to find, produce duplicates and waste disk space. Manual
cleanup is slow and error-prone. The application solves this with automated previews, safe defaults
and repeatable file operations.

## 3. Objectives

- Browse and navigate the file system from a familiar Explorer-style window.
- Perform create, copy, move, rename and delete operations safely.
- Organise files into category folders after an explicit preview and confirmation.
- Search recursively with name, extension, category, size and date filters.
- Detect duplicate files using SHA-256 hashing and delete only user-selected copies.
- Analyse folder sizes, category distribution and the largest files/folders.
- View file metadata and keep a persistent operation history.

## 4. Key features

| Feature | Description |
| --- | --- |
| File Explorer | Breadcrumb navigation, back/forward/up, quick locations, detailed file table, double-click to open |
| File operations | Create folder, rename, copy, move, safe delete, delete empty folder, right-click menu |
| Auto Organizer | Extension categories, selectable rules, preview table, conflict detection, confirmed apply |
| Search | Recursive keyword/extension/category search with size and modified-date filters |
| Duplicate Finder | Size grouping + SHA-256 hashing, duplicate groups, wasted-space report, manual deletion |
| Storage Analyzer | Total size, file/folder counts, category distribution, largest files/folders, bar chart |
| Metadata | Name, type, extension, size, path, created/modified/accessed times, permissions |
| History | SQLite audit log of operations with timestamps, status and destination |
| Safety | Confirmation dialogs, overwrite warnings, protected-folder blocking, symlink skipping, recovery folder |
| Interface | Light/dark themes, multi-select table, properties panel, status bar, progress indicator |

## 5. Technologies used

- Python 3.10+
- CustomTkinter (GUI)
- `pathlib`, `os`, `shutil` (file handling)
- `hashlib` (SHA-256 duplicate detection)
- `sqlite3` (operation history)
- `datetime`, `logging`, `unittest`
- `tkinter.ttk` for the detailed file table

## 6. Project folder structure

```text
Smart_File_Manager/
├── main.py                 # Entry point
├── gui.py                  # Explorer-style CustomTkinter interface
├── file_explorer.py        # Directory browsing and navigation
├── file_operations.py      # Copy, move, rename, create, safe delete
├── file_organizer.py       # Category preview and organization
├── file_search.py          # Search and filters
├── duplicate_finder.py     # SHA-256 duplicate detection
├── storage_analyzer.py     # Storage reports
├── file_metadata.py        # Metadata, type labels, size formatting, category rules
├── history_manager.py      # Audit-history API
├── database.py             # SQLite connection and table
├── validation.py           # Path, name and operation validation
├── error_handler.py        # Friendly errors and standard results
├── logger.py               # File and console logging
├── file_manager.db         # Created automatically on first run
├── requirements.txt
├── README.md
├── .gitignore
├── tests/                  # 32 unit/integration tests
├── screenshots/
└── logs/                   # app.log, created automatically
```

## 7. Module workflow

Example: organising a Downloads folder.

1. `gui.py` collects the folder and selected categories.
2. `validation.py` checks the path and protects system folders.
3. `file_explorer.py` lists the files.
4. `file_organizer.py` builds a preview using category rules from `file_metadata.py`.
5. The user approves the preview in the GUI.
6. `file_operations.py` moves files into category folders.
7. `history_manager.py` and `database.py` store each completed operation.
8. `gui.py` displays the result; `logger.py` records technical details.

## 8. Installation

```powershell
cd Smart_File_Manager
python -m pip install -r requirements.txt
```

Python 3.10 or newer is required. On Windows, the standard Python installer includes Tkinter.
On Linux, install `python3-tk` if the GUI reports that Tkinter is missing.

## 9. Running the application

```powershell
python main.py
```

The database (`file_manager.db`) and log file (`logs/app.log`) are created automatically.

## 10. Using the interface

- Pick a folder in the left navigation pane or type a path into the address bar.
- Double-click a folder to enter it, or a file to open it with its default application.
- Use the toolbar for new folder, rename, copy, move, delete and open.
- Switch modes with the segmented control at the top:
  - **Organizer** – select categories, click *Preview changes*, review, then *Apply approved plan*.
  - **Duplicates** – scan, review groups, select the copies to remove, then delete them.
  - **Storage** – analyse the current folder and view the category bar chart.
  - **History** – review recorded operations or clear the audit log.
- Type in the search box and press Enter to search the current folder and its subfolders.
- Right-click a file for its context menu; press F2 to rename, Delete to remove, Ctrl+N for a new folder.

## 11. Screenshots

Screenshots of the running interface can be placed in the `screenshots/` folder:

- `screenshots/explorer.png` – Explorer workspace
- `screenshots/organizer.png` – organization preview
- `screenshots/duplicates.png` – duplicate scan results
- `screenshots/storage.png` – storage analysis and chart

## 12. Testing

Run the complete suite from the project folder:

```powershell
python -m unittest discover -s tests -v
```

Test modules cover validation, file operations, organizer previews and conflicts, duplicate hashing
and manual deletion, storage totals, search filters and SQLite history. All tests use temporary
directories; none of them modify real Documents or Downloads content.

Result: **32 tests passing**.

## 13. Safety design

- Deletion always requires confirmation and moves items to `~/.smart_file_manager/recycle_bin` by default.
- Existing destinations are never overwritten without an explicit overwrite answer.
- Folders cannot be moved into themselves; drive roots and OS folders are blocked.
- Recursive scans skip symbolic links and inaccessible files, and report what was skipped.
- Bulk organization requires a preview and separate confirmation.
- The history is an audit trail, not an undo system; safe-deleted files can be restored via `restore_from_recycle`.

## 14. Future enhancements

- Undo for eligible rename/move operations.
- Bulk renaming with prefixes, numbering and replacement rules.
- ZIP compression/extraction and drag-and-drop support.
- Threaded scans with detailed progress for very large folders.
- Optional Matplotlib pie chart export for storage reports.
