from pathlib import Path

from logger import FileLogger

logger = FileLogger(Path("spotify") / "spotify.log")
