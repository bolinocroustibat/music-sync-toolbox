from scripts.playlist_sync import SyncMemory, filter_already_synced, normalize
from scripts.spotify_to_ytmusic import process_tracks as spotify_to_ytmusic
from tests.fakes import FakeYTMusic, yt_track


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

        pending, already = filter_already_synced(source, destination, memory)

        assert [t["name"] for t in pending] == ["New"]
        assert already == 1

    def test_skips_tracks_remembered_from_a_previous_run(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")
        destination = [track("フィルハーモニー", "Haruomi Hosono", "v1")]

        pending, already = filter_already_synced(source, destination, SyncMemory("pl", path))

        assert (pending, already) == ([], 1)

    def test_resyncs_remembered_tracks_removed_from_the_destination(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")

        pending, _ = filter_already_synced(source, [], SyncMemory("pl", path))

        assert pending == source

    def test_memory_is_per_destination_playlist(self, tmp_path):
        path = tmp_path / "memory.json"
        source = [track("Philharmony", "Haruomi Hosono")]
        SyncMemory("pl", path).remember(source[0], "v1")
        destination = [track("フィルハーモニー", "Haruomi Hosono", "v1")]

        pending, _ = filter_already_synced(source, destination, SyncMemory("other", path))

        assert pending == source

    def test_destination_local_files_without_id_do_not_match(self, tmp_path):
        memory = SyncMemory("pl", tmp_path / "memory.json")
        source = [track("A")]

        pending, _ = filter_already_synced(source, [track("Local", track_id=None)], memory)

        assert pending == source


def test_chosen_matches_are_remembered(tmp_path, answer_input, no_sleep):
    ytm = FakeYTMusic(search_results=[yt_track("v1"), yt_track("v2")])
    memory = SyncMemory("pl", tmp_path / "memory.json")
    tracks = [track("A", "X"), track("B", "Y")]
    answer_input("2", "1")

    spotify_to_ytmusic(ytm, tracks, {"v1"}, "pl", memory)

    reloaded = SyncMemory("pl", tmp_path / "memory.json")
    assert reloaded.matches == {"x - a": "v2", "y - b": "v1"}
