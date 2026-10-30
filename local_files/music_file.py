from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen._file import File
from mutagen.id3._util import ID3NoHeaderError

from local_files.logger import logger


class MusicFile:
    """Represents a music file with metadata extraction capabilities.

    This class provides a unified interface for reading artist and title tags
    from various audio file formats including MP3, FLAC, and M4A.

    Attributes:
        path: The file path of the music file.
        suffix: The file extension (e.g., '.mp3', '.flac').
        artist: The artist name extracted from the file tags.
        title: The track title extracted from the file tags.
    """

    def __init__(self, path: Path) -> None:
        """Initialize a MusicFile instance and extract metadata.

        Args:
            path: Path to the music file to process.

        Note:
            Automatically calls _get_tags() to extract artist and title
            information from the file upon initialization.
        """
        self.path: Path = path
        self.suffix: str = path.suffix
        self.artist: str = ""
        self.title: str = ""
        self._get_tags()

    def _get_tags(self) -> None:
        """Extract artist and title tags from music files.

        Reads metadata from the music file based on its format. Supports
        FLAC, MP3, M4A, OGG, and WAV files. Sets the artist and title attributes
        if the tags are successfully read.

        Note:
            - FLAC: Reads from FLAC metadata tags
            - MP3: Uses EasyID3 first (more reliable), then falls back to generic ID3 tags
            - M4A: Reads from MP4 metadata tags
            - OGG: Reads from Ogg Vorbis tags
            - WAV: Reads from WAV metadata tags (limited support)
            - Generic fallback: Uses mutagen.File for any format
            - Logs errors if tag reading fails for any format
        """
        # Try format-specific handlers first
        suffix = self.suffix.lower()
        if suffix == ".flac":
            try:
                audio = FLAC(self.path)
                if audio.get("artist") and audio.get("title"):
                    self.artist = audio["artist"][0]
                    self.title = audio["title"][0]
                    return
            except Exception as e:
                logger.error(f"Error reading FLAC tags: {e}")

        elif suffix == ".mp3":
            # Try EasyID3 first (more reliable for MP3)
            try:
                tags = EasyID3(self.path)
                if tags is not None:
                    artist = tags.get("artist", [""])[0]
                    title = tags.get("title", [""])[0]
                    if artist and title:
                        self.artist = artist
                        self.title = title
                        return
            except ID3NoHeaderError:
                pass
            except Exception as e:
                logger.error(f"Error reading MP3 EasyID3 tags: {e}")

        elif suffix == ".m4a":
            try:
                audio = MP4(self.path)
                if audio.get("\xa9ART") and audio.get("\xa9nam"):
                    self.artist = audio["\xa9ART"][0]
                    self.title = audio["\xa9nam"][0]
                    return
            except Exception as e:
                logger.error(f"Error reading M4A tags: {e}")

        elif suffix == ".ogg":
            try:
                audio = OggVorbis(self.path)
                if audio.get("artist") and audio.get("title"):
                    self.artist = audio["artist"][0]
                    self.title = audio["title"][0]
                    return
            except Exception as e:
                logger.error(f"Error reading OGG tags: {e}")

        elif suffix == ".wav":
            try:
                audio = WAVE(self.path)
                # WAV files typically don't have embedded metadata tags
                # This will likely result in empty artist/title
                if hasattr(audio, "tags") and audio.tags:
                    # Try to extract any available metadata
                    pass
            except Exception as e:
                logger.error(f"Error reading WAV tags: {e}")

        # Generic fallback using mutagen.File
        try:
            audio = File(self.path)
            if audio is None:
                logger.error(f"Could not read audio file: {self.path}")
                return

            # Try generic tags
            if hasattr(audio, "tags") and audio.tags is not None:
                try:
                    artist = audio.tags.get("TPE1", [""])[0]
                    title = audio.tags.get("TIT2", [""])[0]
                    if artist and title:
                        self.artist = artist
                        self.title = title
                        return
                except (IndexError, TypeError):
                    pass

        except Exception as e:
            logger.error(f"Error reading generic tags from {self.path}: {e}")

        # If we get here, we couldn't extract tags
        logger.warning(f"Missing artist or title tags in: {self.path}")
