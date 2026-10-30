import importlib

import pytest

from scripts.manage_spotify_duplicates import find_duplicates, remove_duplicates
from spotify import (
    add_track,
    get_playlist_track_details,
    get_playlist_track_ids,
    list_user_playlists,
    search_track,
    select_match,
)
from tests.fakes import FakeSpotify, spotify_item, spotify_playlist


def search_hit(track_id, name="Song", artist="Artist"):
    return {"id": track_id, "name": name, "artists": [{"name": artist}]}


class TestGetPlaylistTrackIds:
    def test_paginates_regular_playlist(self):
        sp = FakeSpotify(playlist=[spotify_item(f"t{i}") for i in range(250)])
        assert get_playlist_track_ids(sp, "pl") == {f"t{i}" for i in range(250)}

    def test_paginates_liked_songs(self):
        sp = FakeSpotify(liked=[spotify_item(f"t{i}") for i in range(45)])
        assert len(get_playlist_track_ids(sp, "liked")) == 45

    def test_skips_removed_tracks(self):
        sp = FakeSpotify(playlist=[spotify_item("t1"), spotify_item(None, name=None)])
        assert get_playlist_track_ids(sp, "pl") == {"t1"}


class TestGetPlaylistTrackDetails:
    def test_returns_name_and_first_artist(self):
        sp = FakeSpotify(
            playlist=[
                spotify_item("t1", "One", "A"),
                spotify_item("t2", "Two", artist=None),
                spotify_item("t3", name=None),
            ]
        )
        assert get_playlist_track_details(sp, "pl") == [{"id": "t1", "name": "One", "artist": "A"}]

    def test_empty_playlist_exits(self):
        with pytest.raises(SystemExit):
            get_playlist_track_details(FakeSpotify(), "pl")


class TestSearchTrack:
    def test_builds_field_query_and_caps_results(self):
        sp = FakeSpotify(search_results=[search_hit(f"t{i}") for i in range(5)])

        matches = search_track(sp, "Song", "Artist")

        assert sp.searches == ["track:Song artist:Artist"]
        assert [m["id"] for m in matches] == ["t0", "t1", "t2", "t3"]
        assert matches[0] == {"id": "t0", "name": "Song", "artist": "Artist"}

    def test_missing_tags_skip_search(self):
        sp = FakeSpotify()
        assert search_track(sp, "", "Artist", "file.mp3") is None
        assert sp.searches == []

    def test_no_results_returns_none(self):
        assert search_track(FakeSpotify(), "Song", "Artist") is None


class TestSelectMatch:
    matches = [{"id": "t1", "name": "A", "artist": "X"}, {"id": "t2", "name": "B", "artist": "Y"}]

    @pytest.mark.parametrize(
        ("answer", "expected"),
        [("", "t1"), ("1", "t1"), ("2", "t2"), ("s", None), ("9", None), ("x", None)],
    )
    def test_choice(self, answer, expected, answer_input):
        answer_input(answer)
        assert select_match(self.matches) == expected


class TestAddTrack:
    def test_adds_to_playlist(self, no_sleep):
        sp = FakeSpotify()
        assert add_track(sp, "t1", "pl", 5) == (True, 5)
        assert sp.added == [("pl", ["t1"])]

    def test_liked_saves_to_library(self, no_sleep):
        sp = FakeSpotify()
        add_track(sp, "t1", "liked", 5)
        assert sp.saved == ["t1"] and sp.added == []

    def test_retries_with_backoff_on_rate_limit(self, no_sleep):
        sp = FakeSpotify()
        calls = []

        def flaky(playlist_id, items):
            calls.append(items)
            if len(calls) == 1:
                raise RuntimeError("Rate/request limit exceeded")

        sp.playlist_add_items = flaky
        assert add_track(sp, "t1", "pl", 5) == (True, 10)
        assert len(calls) == 2

    def test_other_errors_fail_without_retry(self, no_sleep):
        sp = FakeSpotify()
        sp.playlist_add_items = lambda *_: (_ for _ in ()).throw(Exception("boom"))
        assert add_track(sp, "t1", "pl", 5) == (False, 5)


class TestListUserPlaylists:
    def test_liked_songs_first_then_sorted_case_insensitively(self):
        sp = FakeSpotify(
            liked=[spotify_item("t1"), spotify_item("t2")],
            playlists=[spotify_playlist("b", "beta"), spotify_playlist("a", "Alpha")],
        )

        playlists = list_user_playlists(sp)

        assert [p["id"] for p in playlists] == ["liked", "a", "b"]
        assert playlists[0] == {"name": "Liked Songs", "id": "liked", "track_count": 2}

    def test_returns_all_pages(self):
        sp = FakeSpotify(playlists=[spotify_playlist(f"p{i}") for i in range(70)])
        assert len(list_user_playlists(sp)) == 71  # + Liked Songs

    def test_excludes_playlists_only_followed(self):
        sp = FakeSpotify(
            playlists=[
                spotify_playlist("mine"),
                spotify_playlist("followed", owner="someone"),
                spotify_playlist("shared", owner="someone", collaborative=True),
            ]
        )
        assert [p["id"] for p in list_user_playlists(sp)] == ["liked", "mine", "shared"]


class TestDuplicates:
    def playlist(self):
        return [
            spotify_item("a", added_at="2024-01-01T00:00:00Z"),
            spotify_item("b", added_at="2024-01-02T00:00:00Z"),
            spotify_item("a", added_at="2024-01-03T00:00:00Z"),
            spotify_item("c", added_at="2024-01-04T00:00:00Z"),
            spotify_item("a", added_at="2024-01-05T00:00:00Z"),
        ]

    def test_finds_duplicates_across_pages(self):
        items = self.playlist() + [spotify_item(f"x{i}") for i in range(150)] + [spotify_item("b")]
        duplicates = find_duplicates(FakeSpotify(playlist=items), "pl")

        assert set(duplicates) == {"a", "b"}
        assert len(duplicates["a"]) == 3

    def test_liked_songs_have_no_duplicates(self):
        assert find_duplicates(FakeSpotify(), "liked") == {}

    def test_remove_keeps_one_copy_of_each_track(self, no_sleep):
        sp = FakeSpotify(playlist=self.playlist())

        remove_duplicates(sp, "pl", find_duplicates(sp, "pl"))

        assert sp.remaining_ids() == ["a", "b", "c"]

    def test_remove_keeps_oldest_copy_wherever_it_sits(self, no_sleep):
        sp = FakeSpotify(
            playlist=[
                spotify_item("a", added_at="2024-03-01T00:00:00Z"),
                spotify_item("b"),
                spotify_item("a", added_at="2024-01-01T00:00:00Z"),
            ]
        )

        remove_duplicates(sp, "pl", find_duplicates(sp, "pl"))

        assert sp.remaining_ids() == ["b", "a"]

    def test_remove_preserves_order_of_interleaved_duplicates(self, no_sleep):
        ids = ["x", "a", "b", "a", "y", "c", "b", "c", "z", "a"]
        sp = FakeSpotify(playlist=[spotify_item(i) for i in ids])

        remove_duplicates(sp, "pl", find_duplicates(sp, "pl"))

        assert sp.remaining_ids() == ["x", "a", "b", "y", "c", "z"]

    def test_remove_handles_more_than_one_api_batch(self, no_sleep):
        sp = FakeSpotify(playlist=[spotify_item(f"t{i % 160}") for i in range(400)])

        remove_duplicates(sp, "pl", find_duplicates(sp, "pl"))

        assert sp.remaining_ids() == [f"t{i}" for i in range(160)]

    def test_failed_re_add_reports_missing_tracks(self, no_sleep, capsys):
        sp = FakeSpotify(playlist=[spotify_item(i) for i in ["a", "b", "a"]])
        sp.playlist_add_items = lambda *_, **__: (_ for _ in ()).throw(Exception("boom"))

        remove_duplicates(sp, "pl", find_duplicates(sp, "pl"))

        assert "Add these tracks back manually: a" in capsys.readouterr().out

    def test_local_files_are_not_duplicates(self):
        items = [spotify_item(None, name="Local 1"), spotify_item(None, name="Local 2")]
        assert find_duplicates(FakeSpotify(playlist=items), "pl") == {}


class TestSetupSpotify:
    @staticmethod
    def _client(monkeypatch, *outcomes):
        """Patch spotipy.Spotify so successive current_user() calls raise or return `outcomes`."""
        module = importlib.import_module("spotify.setup_spotify")

        calls = iter(outcomes)

        class Client:
            def __init__(self, **_):
                pass

            def current_user(self):
                outcome = next(calls)
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome

        monkeypatch.setattr(module.spotipy, "Spotify", Client)
        return module

    def test_expired_cached_token_is_discarded_and_login_retried(self, monkeypatch, tmp_path):
        from spotipy.oauth2 import SpotifyOauthError

        expired = SpotifyOauthError(
            "expired", error="invalid_grant", error_description="Refresh token expired"
        )
        module = self._client(monkeypatch, expired, {"display_name": "me"})
        cache = tmp_path / ".spotify_token_cache"
        cache.write_text("{}")
        monkeypatch.setattr(module, "TOKEN_CACHE_PATH", cache)

        assert module.setup_spotify() is not None
        assert not cache.exists()

    def test_rejected_credentials_exit_cleanly(self, monkeypatch):
        from spotipy.oauth2 import SpotifyOauthError

        module = self._client(monkeypatch, SpotifyOauthError("bad", error="invalid_client"))
        with pytest.raises(SystemExit):
            module.setup_spotify()

    def test_localhost_redirect_uri_exits_before_opening_browser(self):
        module = importlib.import_module("spotify.setup_spotify")
        with pytest.raises(SystemExit):
            module.check_redirect_uri("http://localhost:8888/callback")
        module.check_redirect_uri("http://127.0.0.1:8888/callback")
