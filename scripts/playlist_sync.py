"""Skip source tracks that are already in the destination playlist when syncing playlists.

A source track counts as already synced when either:
- a destination track has the same normalized title and artist, or
- it was matched to a destination track during a previous run (remembered in
  MEMORY_PATH) and that track is still in the destination playlist.
"""

import json
import re
import unicodedata
from pathlib import Path

MEMORY_PATH = Path("scripts") / ".playlist_sync_memory.json"

# "(2019 Remastering)", "[Live]", ...
_BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
# Spotify style suffixes: "Song - 2019 Remaster", "Song - Remastered 2011"
_REMASTER_SUFFIX = re.compile(r"\s+-\s+[^-]*remaster[^-]*$")
_FEAT = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s+.*$")
_NON_WORD = re.compile(r"[\W_]+")
# Ligatures that Unicode normalization does not decompose
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})


def normalize(text: str) -> str:
    """Lowercase, strip accents, bracketed mentions, remaster suffixes and featurings."""
    text = unicodedata.normalize("NFKD", text.casefold().translate(_LIGATURES))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _BRACKETS.sub(" ", text)
    text = _REMASTER_SUFFIX.sub("", text)
    text = _FEAT.sub("", text)
    return _NON_WORD.sub(" ", text).strip()


def track_key(track: dict) -> str:
    return f"{normalize(track['artist'])} - {normalize(track['name'])}"


class SyncMemory:
    """Source track -> destination track ID matches chosen for one destination playlist."""

    def __init__(self, playlist_id: str, path: Path = MEMORY_PATH) -> None:
        self.path = path
        self.playlist_id = playlist_id
        try:
            self._all: dict[str, dict[str, str]] = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self._all = {}
        self.matches = self._all.setdefault(playlist_id, {})

    def remember(self, track: dict, destination_id: str) -> None:
        """Record a match and save right away, so an interrupted sync keeps its progress."""
        self.matches[track_key(track)] = destination_id
        self.path.write_text(json.dumps(self._all, ensure_ascii=False, indent=2))


def filter_already_synced(
    tracks: list[dict], destination_tracks: list[dict], memory: SyncMemory
) -> tuple[list[dict], int]:
    """Return the source tracks still to sync, and how many were already synced."""
    destination_keys = {track_key(t) for t in destination_tracks}
    destination_ids = {t["id"] for t in destination_tracks if t["id"]}
    pending = [
        track
        for track in tracks
        if track_key(track) not in destination_keys
        and memory.matches.get(track_key(track), "") not in destination_ids
    ]
    return pending, len(tracks) - len(pending)
