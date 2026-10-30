"""Shared fixtures.

Project modules read ``config.toml`` and open log files relative to the
current working directory at import time, so before any of them is imported
we move into a throwaway sandbox holding a copy of ``config.toml.example``.
"""

import os
import shutil
import struct
import tempfile
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC

REPO_ROOT = Path(__file__).resolve().parent.parent


def pytest_sessionstart(session):
    # Runs after pytest has resolved testpaths but before test modules are imported.
    sandbox = Path(tempfile.mkdtemp(prefix="music-sync-tests-"))
    shutil.copy(REPO_ROOT / "config.toml.example", sandbox / "config.toml")
    for log_dir in ("spotify", "ytmusic", "local_files", "scripts"):
        (sandbox / log_dir).mkdir()
    os.chdir(sandbox)


# MPEG-1 Layer III, 128 kbps, 44.1 kHz frame: 4-byte header + 413 bytes payload
_MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413


def _flac_stream() -> bytes:
    """Minimal valid FLAC: magic + a single (last) STREAMINFO block, no audio."""
    streaminfo = struct.pack(">HH", 4096, 4096) + b"\x00" * 6
    # 20 bits sample rate | 3 bits channels-1 | 5 bits bits-per-sample-1 | 36 bits samples
    streaminfo += ((44100 << 44) | (1 << 41) | (15 << 36)).to_bytes(8, "big")
    streaminfo += b"\x00" * 16  # MD5
    return b"fLaC" + bytes([0x80, 0, 0, len(streaminfo)]) + streaminfo


@pytest.fixture
def make_mp3(tmp_path):
    def _make(name: str = "track.mp3", directory: Path | None = None, **tags: str) -> Path:
        path = (directory or tmp_path) / name
        path.write_bytes(_MP3_FRAME * 20)
        if tags:
            id3 = EasyID3()
            for key, value in tags.items():
                id3[key] = value
            id3.save(path)
        return path

    return _make


@pytest.fixture
def make_flac(tmp_path):
    def _make(name: str = "track.flac", directory: Path | None = None, **tags: str) -> Path:
        path = (directory or tmp_path) / name
        path.write_bytes(_flac_stream())
        if tags:
            audio = FLAC(path)
            for key, value in tags.items():
                audio[key] = value
            audio.save()
        return path

    return _make


@pytest.fixture
def no_sleep(monkeypatch):
    """Make time.sleep a no-op everywhere (rate-limit waits, retries)."""
    monkeypatch.setattr("time.sleep", lambda *_: None)


@pytest.fixture
def answer_input(monkeypatch):
    """Call with the successive answers builtins.input should return."""

    def _answer(*answers: str) -> None:
        replies = iter(answers)
        monkeypatch.setattr("builtins.input", lambda *_: next(replies))

    return _answer
