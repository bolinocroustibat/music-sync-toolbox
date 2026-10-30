import pytest

from tests.fakes import FakeYTMusic, yt_track
from ytmusic import (
    add_track_to_ytmusic,
    get_playlist_track_details,
    get_playlist_track_ids,
    list_user_playlists,
    search_track,
    select_match,
)


class TestGetPlaylistTrackIds:
    def test_collects_video_ids(self):
        ytm = FakeYTMusic(playlist=[yt_track("v1"), yt_track("v2"), {"videoId": None}])
        assert get_playlist_track_ids(ytm, "pl") == {"v1", "v2"}

    @pytest.mark.xfail(reason="get_playlist defaults to limit=100")
    def test_fetches_whole_playlist(self):
        ytm = FakeYTMusic(playlist=[yt_track(f"v{i}") for i in range(150)])
        assert len(get_playlist_track_ids(ytm, "pl")) == 150


class TestGetPlaylistTrackDetails:
    def test_returns_title_and_first_artist(self):
        ytm = FakeYTMusic(playlist=[yt_track("v1", "One", "A"), yt_track("v2", "Two", artist=None)])
        assert get_playlist_track_details(ytm, "pl") == [{"name": "One", "artist": "A"}]

    def test_reads_liked_music(self):
        ytm = FakeYTMusic(liked=[yt_track("v1", "Liked", "A")])
        assert get_playlist_track_details(ytm, "LM") == [{"name": "Liked", "artist": "A"}]

    def test_empty_playlist_exits(self):
        with pytest.raises(SystemExit):
            get_playlist_track_details(FakeYTMusic(), "pl")

    @pytest.mark.xfail(reason="get_playlist defaults to limit=100")
    def test_fetches_whole_playlist(self):
        ytm = FakeYTMusic(playlist=[yt_track(f"v{i}") for i in range(150)])
        assert len(get_playlist_track_details(ytm, "pl")) == 150

    @pytest.mark.xfail(reason="get_liked_songs defaults to limit=100")
    def test_fetches_all_liked_music(self):
        ytm = FakeYTMusic(liked=[yt_track(f"v{i}") for i in range(150)])
        assert len(get_playlist_track_details(ytm, "LM")) == 150


class TestListUserPlaylists:
    def test_includes_liked_music_and_sorts(self):
        ytm = FakeYTMusic(library=[{"title": "zed", "playlistId": "z", "count": 1}])
        assert [p["id"] for p in list_user_playlists(ytm)] == ["LM", "z"]

    @pytest.mark.xfail(reason="track_count is len() of the response dict, not of its tracks")
    def test_liked_music_track_count(self):
        ytm = FakeYTMusic(liked=[yt_track(f"v{i}") for i in range(12)])
        liked = next(p for p in list_user_playlists(ytm) if p["id"] == "LM")
        assert liked["track_count"] == 12

    @pytest.mark.xfail(reason="get_library_playlists defaults to limit=25")
    def test_returns_all_library_playlists(self):
        ytm = FakeYTMusic(
            library=[{"title": f"p{i}", "playlistId": f"p{i}", "count": 0} for i in range(40)]
        )
        assert len(list_user_playlists(ytm)) == 41  # + Liked Music


class TestSearchTrack:
    def test_formats_and_caps_matches(self):
        ytm = FakeYTMusic(
            search_results=[yt_track(f"v{i}") for i in range(5)] + [{"title": "no id"}]
        )
        matches = search_track(ytm, "Song", "Artist")
        assert [m["id"] for m in matches] == ["v0", "v1", "v2", "v3"]

    def test_missing_tags_skip_search(self):
        assert search_track(FakeYTMusic(), "Song", "") is None


class TestSelectMatch:
    matches = [{"id": "v1", "name": "A", "artist": "X"}, {"id": "v2", "name": "B", "artist": "Y"}]

    @pytest.mark.parametrize(("answer", "expected"), [("", "v1"), ("2", "v2"), ("s", None), ("7", None)])
    def test_choice(self, answer, expected, answer_input):
        answer_input(answer)
        assert select_match(self.matches) == expected

    def test_auto_first_does_not_prompt(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        assert select_match(self.matches, auto_first=True) == "v1"


class TestAddTrack:
    def test_adds_to_playlist(self, no_sleep):
        ytm = FakeYTMusic()
        assert add_track_to_ytmusic(ytm, "v1", "pl", 5) == (True, 5)
        assert ytm.added == [("pl", ["v1"])]

    def test_liked_music_likes_the_song(self, no_sleep):
        ytm = FakeYTMusic()
        add_track_to_ytmusic(ytm, "v1", "LM", 5)
        assert ytm.rated == [("v1", "LIKE")] and ytm.added == []
