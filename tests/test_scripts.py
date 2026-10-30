import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.local_to_spotify as local_to_spotify
from logger import FileLogger
from scripts.spotify_to_ytmusic import process_tracks as spotify_to_ytmusic
from scripts.ytmusic_to_spotify import process_tracks as ytmusic_to_spotify
from tests.conftest import REPO_ROOT
from tests.fakes import FakeSpotify, FakeYTMusic, spotify_item, yt_track


def hit(track_id):
    return {"id": track_id, "name": "Song", "artists": [{"name": "Artist"}]}


class TestYTMusicToSpotify:
    tracks = [{"name": f"Song {i}", "artist": "Artist"} for i in range(3)]

    def test_auto_first_answer_applies_to_remaining_tracks(self, answer_input, no_sleep):
        sp = FakeSpotify(search_results=[hit("t1"), hit("t2")])
        answer_input("a")  # a second prompt would raise StopIteration

        added, skipped = ytmusic_to_spotify(sp, self.tracks, set(), "pl")

        assert (added, skipped) == (3, 0)
        assert sp.added == [("pl", ["t1"])] * 3

    def test_skips_tracks_already_in_playlist(self, answer_input, no_sleep):
        sp = FakeSpotify(search_results=[hit("t1")])
        answer_input("", "s", "2")

        added, skipped = ytmusic_to_spotify(sp, self.tracks, {"t1"}, "pl")

        assert (added, skipped) == (0, 3)
        assert sp.added == []


class TestSpotifyToYTMusic:
    def test_adds_selected_matches_and_skips_existing(self, answer_input, no_sleep):
        ytm = FakeYTMusic(search_results=[yt_track("v1"), yt_track("v2")])
        tracks = [{"name": "A", "artist": "X"}, {"name": "B", "artist": "Y"}]
        answer_input("2", "1")

        added, skipped = spotify_to_ytmusic(ytm, tracks, {"v1"}, "pl")

        assert (added, skipped) == (1, 1)
        assert ytm.added == [("pl", ["v2"])]


class TestLocalToSpotify:
    @pytest.fixture
    def run(self, monkeypatch, tmp_path, no_sleep):
        def _run(sp, playlist_id):
            monkeypatch.setattr(local_to_spotify, "setup_spotify", lambda: sp)
            monkeypatch.setattr(local_to_spotify, "select_spotify_playlist", lambda *_: playlist_id)
            monkeypatch.setattr(
                local_to_spotify,
                "get_music_files",
                lambda _: [SimpleNamespace(title="Song", artist="Artist", path=Path("a.mp3"))],
            )
            monkeypatch.setattr("builtins.input", lambda *_: "")
            local_to_spotify.main(tmp_path)

        return _run

    def test_adds_new_track(self, run):
        sp = FakeSpotify(search_results=[hit("t1")])
        run(sp, "pl")
        assert sp.added == [("pl", ["t1"])]

    def test_skips_track_already_in_playlist(self, run):
        sp = FakeSpotify(playlist=[spotify_item("t1")], search_results=[hit("t1")])
        run(sp, "pl")
        assert sp.added == []

    @pytest.mark.xfail(reason="existing tracks fetched via playlist_items, which rejects 'liked'")
    def test_liked_songs_target(self, run):
        sp = FakeSpotify(search_results=[hit("t1")])
        run(sp, "liked")
        assert sp.saved == ["t1"]


@pytest.mark.xfail(reason="all FileLoggers share the 'discogs_tag' logger, so handlers stack")
def test_file_loggers_write_only_to_their_own_file(tmp_path):
    first, second = tmp_path / "first.log", tmp_path / "second.log"
    FileLogger(first)
    FileLogger(second).info("only for second")

    assert "only for second" not in first.read_text()


@pytest.mark.xfail(reason="script modules build SpotifyConfig/YTMusicConfig at import time")
def test_menu_loads_without_spotify_or_ytmusic_config(tmp_path):
    (tmp_path / "config.toml").write_text(
        (REPO_ROOT / "config.toml.example").read_text().split("[spotify]")[0]
    )
    for log_dir in ("spotify", "ytmusic", "local_files", "scripts"):
        (tmp_path / log_dir).mkdir()

    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
