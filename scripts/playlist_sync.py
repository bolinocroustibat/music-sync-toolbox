"""Skip source tracks that are already in the destination playlist when syncing playlists.

A source track counts as already synced when either:
- a destination track has the same normalized title and artist, or
- it was matched to a destination track during a previous run (remembered in
  MEMORY_PATH) and that track is still in the destination playlist.

Tracks the user skipped during a previous run are remembered too, and only asked
about again if the user says so.
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
    """Source track -> destination track ID matches chosen for one destination playlist.

    A None destination ID means the user skipped the track.
    """

    def __init__(self, playlist_id: str, path: Path = MEMORY_PATH) -> None:
        self.path = path
        self.playlist_id = playlist_id
        try:
            self._all: dict[str, dict[str, str | None]] = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self._all = {}
        self.matches = self._all.setdefault(playlist_id, {})

    def remember(self, track: dict, destination_id: str | None) -> None:
        """Record a match (None: skipped) and save right away, so an interrupted sync
        keeps its progress."""
        self.matches[track_key(track)] = destination_id
        self._save()

    def forget(self, tracks: list[dict]) -> None:
        for track in tracks:
            self.matches.pop(track_key(track), None)
        self._save()

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._all, ensure_ascii=False, indent=2))


def filter_already_synced(
    tracks: list[dict], destination_tracks: list[dict], memory: SyncMemory
) -> tuple[list[dict], int, list[dict]]:
    """Return the source tracks still to sync, how many were already synced, and the
    tracks skipped during a previous run."""
    destination_keys = {track_key(t) for t in destination_tracks}
    destination_ids = {t["id"] for t in destination_tracks if t["id"]}
    pending: list[dict] = []
    skipped: list[dict] = []
    already_synced = 0
    for track in tracks:
        key = track_key(track)
        if key in destination_keys:
            already_synced += 1
        elif key in memory.matches and memory.matches[key] is None:
            skipped.append(track)
        elif memory.matches.get(key) in destination_ids:
            already_synced += 1
        else:
            pending.append(track)
    return pending, already_synced, skipped


def select_tracks_to_sync(
    tracks: list[dict], destination_tracks: list[dict], memory: SyncMemory
) -> tuple[list[dict], int, int]:
    """Return the source tracks to go through, how many were already synced, and how many
    previously skipped tracks are left out.

    Asks whether previously skipped tracks should be asked about again.
    """
    pending, already_synced, skipped = filter_already_synced(tracks, destination_tracks, memory)
    if skipped:
        answer = input(
            f"\n{len(skipped)} tracks were skipped in previous syncs to this playlist. "
            "Ask about them again? [y/N] "
        )
        if answer.strip().lower() in ("y", "yes"):
            memory.forget(skipped)
            # Back in the source playlist order
            to_sync = {id(t) for t in pending + skipped}
            pending = [t for t in tracks if id(t) in to_sync]
            skipped = []
    return pending, already_synced, len(skipped)
