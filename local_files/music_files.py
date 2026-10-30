from pathlib import Path
from local_files.music_file import MusicFile

AUDIO_FILES_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".wav"}


def get_music_files(directory: Path, recursive: bool = True) -> list[MusicFile]:
    """Get all music files in directory and optionally subdirectories."""
    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    music_files = [
        MusicFile(f) for f in files if f.is_file() and f.suffix.lower() in AUDIO_FILES_EXTENSIONS
    ]

    # Sort files alphabetically by name (case-insensitive)
    return sorted(music_files, key=lambda x: x.path.name.lower())
