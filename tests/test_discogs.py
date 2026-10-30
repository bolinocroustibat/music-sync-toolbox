from types import SimpleNamespace

import pytest
from discogs_client.exceptions import HTTPError
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3

from discogs import DTag, clean
from scripts.update_tags_from_discogs import update_tags_from_discogs


def make_config(**overrides):
    defaults = dict(
        token="t",
        overwrite_year=False,
        overwrite_genre=False,
        embed_cover=True,
        overwrite_cover=False,
        rename_file=False,
    )
    return SimpleNamespace(**{**defaults, **overrides})


def master(title="Title", year=1999, genres=("House", "Electronic"), images=None, **data):
    return SimpleNamespace(
        title=title,
        genres=list(genres),
        images=images if images is not None else [{"uri": "https://img/cover.jpg"}],
        data={"year": year, **data},
    )


class FakeResults:
    """Mimics discogs_client's lazy PaginatedList; counts pages fetched."""

    def __init__(self, items, per_page=50):
        self.items = list(items)
        self.per_page = per_page
        self.pages_fetched: set[int] = set()

    @property
    def count(self):
        return len(self.items)

    def page(self, n):
        self.pages_fetched.add(n)
        start = (n - 1) * self.per_page
        return self.items[start : start + self.per_page]

    def __iter__(self):
        for i, item in enumerate(self.items):
            self.pages_fetched.add(i // self.per_page + 1)
            yield item

    def __getitem__(self, i):
        self.pages_fetched.add(i // self.per_page + 1)
        return self.items[i]


class FakeDiscogs:
    def __init__(self, *responses):
        """Each response is a FakeResults or an exception to raise."""
        self.responses = list(responses)
        self.calls = []

    def identity(self):
        return "tester"

    def search(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def fake_cover(monkeypatch):
    """Serve a fake JPEG for cover downloads; returns the kwargs of each request."""
    requests_made = []

    def get(url, **kwargs):
        requests_made.append(kwargs)
        return SimpleNamespace(content=b"\xff\xd8jpeg", raise_for_status=lambda: None)

    monkeypatch.setattr("discogs.dtag.requests.get", get)
    return requests_made


class FakeMP4(dict):
    """Stands in for mutagen's MP4: building a real .m4a needs an encoder."""

    saved: dict = {}

    def __init__(self, path):
        super().__init__(FakeMP4.saved)

    def save(self):
        FakeMP4.saved = dict(self)


class TestClean:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("One More Time (Radio Edit)", "One More Time"),
            ("Artist (feat. Someone)", "Artist"),
            ("Simon, Garfunkel", "Simon"),
            ("Simon & Garfunkel", "Simon"),
            ("Don't Stop", "Dont Stop"),
            ("Plain", "Plain"),
        ],
    )
    def test_clean(self, raw, expected):
        assert clean(raw) == expected


class TestDTagInit:
    def test_reads_extra_tags_and_cleans_artist_title(self, make_mp3):
        path = make_mp3(artist="A & B", title="Song (Remix)", genre="Rock", date="2018")
        tag = DTag(path, path.name, make_config(), ds=None)

        assert (tag.search_artist, tag.search_title) == ("A", "Song")
        assert (tag.artist, tag.title) == ("A & B", "Song (Remix)")
        assert (tag.local_genres, tag.local_year) == ("Rock", "2018")

    def test_searches_with_cleaned_tags(self, make_mp3, no_sleep):
        path = make_mp3(artist="A & B", title="Hello, Goodbye (Remix)")
        ds = FakeDiscogs(FakeResults([master()]))

        DTag(path, path.name, make_config(), ds).search()

        assert ds.calls == [{"type": "master", "artist": "A", "track": "Hello"}]


class TestDTagSearch:
    def test_populates_genres_year_and_image(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        ds = FakeDiscogs(FakeResults([master(year=1997)]))
        tag = DTag(path, path.name, make_config(), ds)

        tag.search()

        assert ds.calls == [{"type": "master", "artist": "Artist", "track": "Title"}]
        assert tag.genres == "Electronic, House"
        assert tag.year == "1997"
        assert tag.image == "https://img/cover.jpg"

    def test_picks_best_fuzzy_match(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        results = FakeResults(
            [master(title="Something Else", year=2005), master(title="Title Artist", year=1997)]
        )
        tag = DTag(path, path.name, make_config(), FakeDiscogs(results))

        tag.search()

        assert tag.year == "1997"

    def test_best_match_is_not_just_the_first_result(self, make_mp3, no_sleep):
        path = make_mp3(artist="Daft Punk", title="One More Time")
        results = FakeResults(
            [
                master(title="Daft Punk - Around The World", year=1997),
                master(title="Daft Punk - One More Time", year=2000),
            ]
        )
        tag = DTag(path, path.name, make_config(), FakeDiscogs(results))

        tag.search()

        assert tag.year == "2000"

    def test_not_found_returns_false(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        tag = DTag(path, path.name, make_config(), FakeDiscogs(FakeResults([])))

        assert tag.search() is False

    def test_handles_results_carrying_an_artist_field(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        results = FakeResults([master(artist=[{"name": "Artist"}])])
        tag = DTag(path, path.name, make_config(), FakeDiscogs(results))

        tag.search()

        assert tag.year_found

    def test_exhausted_retries_are_not_reported_as_found(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        ds = FakeDiscogs(HTTPError("rate limited", 429))
        tag = DTag(path, path.name, make_config(), ds)

        assert tag.search() is not None
        assert len(ds.calls) == 3

    def test_missing_artist_does_not_search(self, make_mp3, no_sleep):
        path = make_mp3(title="Title")
        ds = FakeDiscogs(FakeResults([master()]))
        tag = DTag(path, path.name, make_config(), ds)

        assert tag.search() is False
        assert ds.calls == []

    def test_only_fetches_first_page_of_results(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        results = FakeResults([master(title=f"Other {i}") for i in range(150)])
        tag = DTag(path, path.name, make_config(), FakeDiscogs(results))

        tag.search()

        assert results.pages_fetched == {1}

    def test_match_without_year_still_sets_genres(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        tag = DTag(path, path.name, make_config(), FakeDiscogs(FakeResults([master(year=None)])))

        assert tag.search() is True
        assert tag.genres_found and not tag.year_found

    def test_zero_retries_returns_false(self, make_mp3, no_sleep):
        path = make_mp3(artist="Artist", title="Title")
        tag = DTag(path, path.name, make_config(), FakeDiscogs(FakeResults([master()])))

        assert tag.search(retry=0) is False


class TestDTagSave:
    def found(self, path, config, genres="House", year="1997"):
        tag = DTag(path, path.name, config, ds=None)
        tag.genres, tag.genres_found = genres, True
        tag.year, tag.year_found = year, True
        return tag

    def test_fills_empty_tags(self, make_mp3):
        path = make_mp3(artist="A", title="T")
        tag = self.found(path, make_config())

        tag.save()

        saved = EasyID3(path)
        assert (saved["genre"], saved["date"]) == (["House"], ["1997"])
        assert tag.genres_updated and tag.year_updated

    def test_keeps_existing_tags_without_overwrite(self, make_mp3):
        path = make_mp3(artist="A", title="T", genre="Rock", date="2018")
        tag = self.found(path, make_config())

        tag.save()

        saved = EasyID3(path)
        assert (saved["genre"], saved["date"]) == (["Rock"], ["2018"])
        assert not tag.genres_updated and not tag.year_updated

    def test_overwrites_existing_tags_when_enabled(self, make_flac):
        path = make_flac(artist="A", title="T", genre="Rock", date="2018")
        tag = self.found(path, make_config(overwrite_genre=True, overwrite_year=True))

        tag.save()

        saved = FLAC(path)
        assert (saved["genre"], saved["date"]) == (["House"], ["1997"])

    def test_nothing_found_leaves_file_untouched(self, make_mp3):
        path = make_mp3(artist="A", title="T")
        before = path.read_bytes()
        tag = DTag(path, path.name, make_config(), ds=None)

        tag.save()

        assert path.read_bytes() == before

    def test_embeds_cover_in_mp3(self, make_mp3, fake_cover):
        path = make_mp3(artist="A", title="T")
        tag = self.found(path, make_config())
        tag.image = "https://img/cover.jpg"

        tag.save()

        assert ID3(path).getall("APIC")[0].data == b"\xff\xd8jpeg"
        assert tag.cover_updated

    def test_embeds_cover_in_flac(self, make_flac, fake_cover):
        path = make_flac(artist="A", title="T")
        tag = self.found(path, make_config())
        tag.image = "https://img/cover.jpg"

        tag.save()

        assert FLAC(path).pictures[0].data == b"\xff\xd8jpeg"

    def test_uppercase_extension_is_read_and_saved(self, make_mp3):
        path = make_mp3("TRACK.MP3", artist="A", title="T", genre="Rock")
        tag = self.found(path, make_config(overwrite_genre=True))
        assert tag.local_genres == "Rock"

        tag.save()

        assert EasyID3(path)["genre"] == ["House"]

    def test_cover_download_has_a_timeout(self, make_mp3, fake_cover):
        tag = self.found(make_mp3(artist="A", title="T"), make_config())
        tag.image = "https://img/cover.jpg"

        tag.save()

        assert fake_cover and all(r.get("timeout") for r in fake_cover)

    def test_failed_cover_download_still_saves_tags(self, make_mp3, monkeypatch):
        def fail(*_, **__):
            raise ConnectionError("timed out")

        monkeypatch.setattr("discogs.dtag.requests.get", fail)
        path = make_mp3(artist="A", title="T")
        tag = self.found(path, make_config())
        tag.image = "https://img/cover.jpg"

        tag.save()

        assert EasyID3(path)["genre"] == ["House"]
        assert not tag.cover_updated

    def test_existing_cover_kept_without_overwrite(self, make_mp3, fake_cover):
        tag = self.found(make_mp3(artist="A", title="T"), make_config())
        tag.image, tag.cover_embedded = "https://img/cover.jpg", True

        tag.save()

        assert fake_cover == [] and not tag.cover_updated

    @pytest.mark.parametrize(
        ("existing", "overwrite", "embedded"),
        [({}, False, True), ({"covr": ["old"]}, False, False), ({"covr": ["old"]}, True, True)],
    )
    def test_m4a_cover(self, tmp_path, monkeypatch, fake_cover, existing, overwrite, embedded):
        monkeypatch.setattr("discogs.dtag.MP4", FakeMP4)
        FakeMP4.saved = dict(existing)
        path = tmp_path / "track.m4a"
        path.write_bytes(b"")
        tag = self.found(path, make_config(overwrite_cover=overwrite))
        tag.image = "https://img/cover.jpg"

        tag.save()

        assert tag.cover_updated is embedded
        assert (FakeMP4.saved["covr"] != ["old"]) is embedded

    def test_unsupported_format_does_not_crash(self, tmp_path):
        path = tmp_path / "track.ogg"
        path.write_bytes(b"not really ogg")
        tag = self.found(path, make_config())

        tag.save()


class TestUpdateTagsFromDiscogs:
    def test_tags_every_file(self, tmp_path, make_mp3, monkeypatch, no_sleep):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        path = make_mp3(artist="Artist", title="Title")
        ds = FakeDiscogs(FakeResults([master()]))

        update_tags_from_discogs(tmp_path, make_config(embed_cover=False), ds)

        assert EasyID3(path)["genre"] == ["Electronic, House"]

    def test_rename_option_keeps_full_title(self, tmp_path, make_mp3, monkeypatch, no_sleep):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        make_mp3("old.mp3", artist="A & B", title="Hello, Goodbye (Remix)")
        ds = FakeDiscogs(FakeResults([master()]))

        update_tags_from_discogs(tmp_path, make_config(embed_cover=False, rename_file=True), ds)

        assert (tmp_path / "A & B - Hello, Goodbye (Remix).mp3").is_file()

    def test_scans_uppercase_extensions_and_skips_directories(
        self, tmp_path, make_mp3, monkeypatch, no_sleep
    ):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        (tmp_path / "folder.mp3").mkdir()
        path = make_mp3("LOUD.MP3", artist="Artist", title="Title")
        ds = FakeDiscogs(FakeResults([master()]))

        update_tags_from_discogs(tmp_path, make_config(embed_cover=False), ds)

        assert len(ds.calls) == 1
        assert EasyID3(path)["genre"] == ["Electronic, House"]

    def test_rename_option_still_saves_tags(self, tmp_path, make_mp3, monkeypatch, no_sleep):
        monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("prompted"))
        make_mp3("old name.mp3", artist="Artist", title="Title")
        ds = FakeDiscogs(FakeResults([master()]))

        update_tags_from_discogs(tmp_path, make_config(embed_cover=False, rename_file=True), ds)

        assert EasyID3(tmp_path / "Artist - Title.mp3")["genre"] == ["Electronic, House"]
