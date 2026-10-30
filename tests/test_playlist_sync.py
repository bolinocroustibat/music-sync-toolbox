import pytest

from scripts.playlist_sync import (
    SyncMemory,
    filter_already_synced,
    normalize,
    select_tracks_to_sync,
)
from scripts.spotify_to_ytmusic import process_tracks as spotify_to_ytmusic
from scripts.ytmusic_to_spotify import process_tracks as ytmusic_to_spotify
from tests.fakes import FakeSpotify, FakeYTMusic, yt_track


def track(name, artist="Artist", track_id=None):
    return {"id": track_id, "name": name, "artist": artist}


class TestNormalize:
    def test_ignores_case_accents_and_punctuation(self):
        assert normalize("Cœur d'Eau") == normalize("coeur d eau")
        assert normalize("Théo") == "theo"

    def test_ignores_remaster_and_bracketed_mentions(self):
        assert normalize("Philharmony - 2019 Remaster") == "philharmony"
        assert normalize("Philharmony (2019 Remastering)") == "philharmony"
        assert normalize("Song [Live]") == "song"

    def test_ignores_featurings(self):
        assert normalize("Song feat. Someone") == "song"

    def test_keeps_meaningful_suffixes(self):
        assert normalize("Song - Original Mix") != normalize("Song")


class TestFilterAlreadySynced:
    def test_skips_tracks_with_same_title_and_artist(self, tmp_path):
        memory = SyncMemory("pl", tmp_path / "memory.json")
        source = [track("Coeur d'eau", "Limousine"), track("New", "Limousine")]
        destination = [track("Cœur d'Eau", "LIMOUSINE", "v1")]

        pending, already, _ = filter_already_synced(source, destination, memory)

        assert [t["name"] for t in pending] == ["New"]
        assert already == 1

    def test_skips_tracks_remembered_from_a_previous_run(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")
        destination = [track("フィルハーモニー", "Haruomi Hosono", "v1")]

        pending, already, _ = filter_already_synced(source, destination, SyncMemory("pl", path))

        assert (pending, already) == ([], 1)

    def test_resyncs_remembered_tracks_removed_from_the_destination(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")

        pending, _, _ = filter_already_synced(source, [], SyncMemory("pl", path))

        assert pending == source

    def test_memory_is_per_destination_playlist(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")
        destination = [track("フィルハーモニー", "Haruomi Hosono", "v1")]

        pending, _, _ = filter_already_synced(source, destination, SyncMemory("other", path))

        assert pending == source

    def test_destination_local_files_without_id_do_not_match(self, tmp_path):
        memory = SyncMemory("pl", tmp_path / "memory.json")
        source = [track("A")]

        pending, _, _ = filter_already_synced(source, [track("Local", track_id=None)], memory)

        assert pending == source


def test_chosen_matches_are_remembered(tmp_path, answer_input, no_sleep):
    ytm = FakeYTMusic(search_results=[yt_track("v1"), yt_track("v2")])
    memory = SyncMemory("pl", tmp_path / "memory.json")
    tracks = [track("A", "X"), track("B", "Y")]
    answer_input("2", "1")

    spotify_to_ytmusic(ytm, tracks, {"v1"}, "pl", memory)

    reloaded = SyncMemory("pl", tmp_path / "memory.json")
    assert reloaded.matches == {"x - a": "v2", "y - b": "v1"}


class TestSkippedTracks:
    def test_skipped_tracks_are_set_aside(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("A"), track("B")]
        SyncMemory("pl", path).remember(source[0], None)

        pending, already, skipped = filter_already_synced(source, [], SyncMemory("pl", path))

        assert (pending, already, skipped) == ([source[1]], 0, [source[0]])

    def test_previously_skipped_tracks_are_not_asked_again_by_default(self, tmp_path, answer_input):
        memory = SyncMemory("pl", tmp_path / "memory.json")
        source = [track("A"), track("B")]
        memory.remember(source[0], None)
        answer_input("")

        pending, _, previously_skipped = select_tracks_to_sync(source, [], memory)

        assert (pending, previously_skipped) == ([source[1]], 1)

    def test_previously_skipped_tracks_can_be_asked_again(self, tmp_path, answer_input):
        path = tmp_path / "memory.json"
        memory = SyncMemory("pl", path)
        source = [track("A"), track("B"), track("C")]
        memory.remember(source[1], None)
        answer_input("y")

        pending, _, previously_skipped = select_tracks_to_sync(source, [], memory)

        assert (pending, previously_skipped) == (source, 0)
        assert SyncMemory("pl", path).matches == {}

    def test_no_question_without_previously_skipped_tracks(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        memory = SyncMemory("pl", tmp_path / "memory.json")

        assert select_tracks_to_sync([track("A")], [], memory) == ([track("A")], 0, 0)


def test_spotify_to_ytmusic_remembers_explicit_skips_only(tmp_path, answer_input, no_sleep):
    ytm = FakeYTMusic(search_results=[yt_track("v1")])
    memory = SyncMemory("pl", tmp_path / "memory.json")
    answer_input("s", "9")  # skip, then an invalid choice

    spotify_to_ytmusic(ytm, [track("A", "X"), track("B", "Y")], set(), "pl", memory)

    assert memory.matches == {"x - a": None}


def test_ytmusic_to_spotify_remembers_explicit_skips_only(tmp_path, answer_input, no_sleep):
    hit = {"id": "t1", "name": "Song", "artists": [{"name": "Artist"}]}
    sp = FakeSpotify(search_results=[hit])
    memory = SyncMemory("pl", tmp_path / "memory.json")
    answer_input("s", "9")

    ytmusic_to_spotify(sp, [track("A", "X"), track("B", "Y")], set(), "pl", memory)

    assert memory.matches == {"x - a": None}
