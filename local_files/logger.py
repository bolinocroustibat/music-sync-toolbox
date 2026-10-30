from pathlib import Path

from logger import FileLogger

logger = FileLogger(Path("local_files") / "local_files.log")
