"""Smart File Manager - application entry point."""

from __future__ import annotations

from gui import FileManagerApp
from logger import setup_logger

LOG = setup_logger()


def main() -> None:
    LOG.info("Starting Smart File Manager")
    app = FileManagerApp()
    app.mainloop()
    LOG.info("Smart File Manager closed")


if __name__ == "__main__":
    main()
