import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from logger import FileLogger
from scripts import local_to_spotify, local_to_ytmusic
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

        # Every track matched t1: it is added once, then recognized as already there
        assert (added, skipped) == (1, 2)
        assert sp.added == [("pl", ["t1"])]

    def test_skips_tracks_already_in_playlist(self, answer_input, no_sleep):
        sp = FakeSpotify(search_results=[hit("t1")])
        answer_input("", "s", "2")

        added, skipped = ytmusic_to_spotify(sp, self.tracks, {"t1"}, "pl")

        assert (added, skipped) == (0, 3)
        assert sp.added == []


def test_prompts_are_not_drawn_over_by_a_progress_bar(monkeypatch, answer_input, no_sleep):
    # A live display (progress bar) would keep redrawing over the match prompts
    monkeypatch.setattr(
        "rich.live.Live.start", lambda *_, **__: pytest.fail("live display started")
    )
    answer_input("")
    sp = FakeSpotify(search_results=[hit("t1")])

    ytmusic_to_spotify(sp, [{"name": "Song", "artist": "Artist"}], set(), "pl")

    assert sp.added == [("pl", ["t1"])]


def test_shows_a_counter_per_track(answer_input, no_sleep, capsys):
    ytm = FakeYTMusic(search_results=[yt_track("v1")])
    answer_input("s", "s")

    spotify_to_ytmusic(
        ytm, [{"name": "A", "artist": "X"}, {"name": "B", "artist": "Y"}], set(), "pl"
    )

    out = capsys.readouterr().out
    assert "[1/2]" in out and "[2/2]" in out


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

    def test_liked_songs_target(self, run):
        sp = FakeSpotify(search_results=[hit("t1")])
        run(sp, "liked")
        assert sp.saved == ["t1"]


class TestLocalToYTMusic:
    @pytest.fixture
    def run(self, monkeypatch, tmp_path, no_sleep):
        def _run(ytm, playlist_id="pl"):
            monkeypatch.setattr(local_to_ytmusic, "setup_ytmusic", lambda: ytm)
            monkeypatch.setattr(local_to_ytmusic, "select_ytmusic_playlist", lambda *_: playlist_id)
            monkeypatch.setattr(
                local_to_ytmusic,
                "get_music_files",
                lambda _: [SimpleNamespace(title="Song", artist="Artist", path=Path("a.mp3"))],
            )
            monkeypatch.setattr("builtins.input", lambda *_: "")
            local_to_ytmusic.main(tmp_path)

        return _run

    def test_adds_new_track(self, run):
        ytm = FakeYTMusic(search_results=[yt_track("v1")])
        run(ytm)
        assert ytm.added == [("pl", ["v1"])]

    def test_skips_track_beyond_first_100_of_playlist(self, run):
        ytm = FakeYTMusic(
            playlist=[yt_track(f"v{i}") for i in range(150)], search_results=[yt_track("v120")]
        )
        run(ytm)
        assert ytm.added == []


def test_file_loggers_write_only_to_their_own_file(tmp_path):
    first, second = tmp_path / "first.log", tmp_path / "second.log"
    FileLogger(first)
    FileLogger(second).info("only for second")

    assert "only for second" not in first.read_text()


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
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_file_logger_created_twice_writes_each_line_once(tmp_path):
    log_file = tmp_path / "same.log"
    FileLogger(log_file)
    FileLogger(log_file).info("hello")

    assert log_file.read_text().count("hello") == 1


class TestMainMenu:
    @pytest.fixture
    def run(self, monkeypatch, tmp_path):
        """Run main() choosing `action`, from a dir whose config.toml is `config`."""
        calls = {}
        monkeypatch.setattr(
            main, "update_tags_from_discogs", lambda *a: calls.setdefault("discogs", a)
        )
        monkeypatch.setattr(
            main, "download_from_soulseek", lambda: calls.setdefault("soulseek", ())
        )

        def _run(action, config, *argv):
            if config is not None:
                (tmp_path / "config.toml").write_text(config)
            monkeypatch.chdir(tmp_path)
            monkeypatch.setattr(sys, "argv", ["music-sync", *argv])
            monkeypatch.setattr(main.inquirer, "prompt", lambda _: {"action": action})
            main.main()
            return calls

        return _run

    def test_soulseek_runs_without_other_sections(self, run):
        calls = run("soulseek_download", '[soulseek]\nhost = "h"\napi_key = "k"\n')
        assert "soulseek" in calls

    def test_discogs_action_loads_discogs_config(self, run, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        config = (REPO_ROOT / "config.toml.example").read_text().split("[spotify]")[0]

        calls = run("discogs_update", config.replace("your_token", "abc"), "--path", str(music))

        media_path, discogs_config, client = calls["discogs"]
        assert media_path == music.resolve()
        assert discogs_config.token == "abc"
        assert client is not None

    def test_missing_config_exits(self, run):
        with pytest.raises(SystemExit):
            run("soulseek_download", None)
