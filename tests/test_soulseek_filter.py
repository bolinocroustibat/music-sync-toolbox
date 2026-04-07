import unittest

from soulseek.search_download import (
    SearchCandidate,
    filter_mp3_exact_bitrate,
)


def _mp3(username: str = "u", br: int | None = 320, fn: str = "a.mp3") -> SearchCandidate:
    f: dict = {"filename": fn, "extension": "mp3"}
    if br is not None:
        f["bitRate"] = br
    return SearchCandidate(username, f, locked=False)


def _flac(username: str = "u", fn: str = "a.flac") -> SearchCandidate:
    return SearchCandidate(
        username,
        {"filename": fn, "extension": "flac", "bitDepth": 16},
        locked=False,
    )


class FilterMp3ExactBitrateTests(unittest.TestCase):
    def test_none_returns_unchanged(self) -> None:
        c = [_mp3(), _flac()]
        self.assertEqual(filter_mp3_exact_bitrate(c, None), c)

    def test_keeps_matching_mp3(self) -> None:
        c = [_mp3(br=320), _mp3(br=128, fn="b.mp3")]
        out = filter_mp3_exact_bitrate(c, 320)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].file["filename"], "a.mp3")

    def test_drops_mp3_without_bitrate_when_filter_active(self) -> None:
        c = [_mp3(br=None)]
        self.assertEqual(filter_mp3_exact_bitrate(c, 320), [])

    def test_flac_passthrough_when_filter_set(self) -> None:
        c = [_flac(), _mp3(br=128)]
        out = filter_mp3_exact_bitrate(c, 320)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].file["extension"], "flac")

    def test_non_numeric_bitrate_drops_mp3(self) -> None:
        bad = SearchCandidate("u", {"filename": "x.mp3", "extension": "mp3", "bitRate": "x"}, locked=False)
        out = filter_mp3_exact_bitrate([bad], 320)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
