import pytest

import soulseek.config
from soulseek import (
    Config,
    SearchCandidate,
    SoulseekConfigError,
    check_server_ready,
    enqueue_candidates,
    flatten_search_responses,
    format_candidate_label,
    search_and_collect,
)


def response(username, files=(), locked=()):
    return {"username": username, "files": list(files), "lockedFiles": list(locked)}


def file(name, ext, **extra):
    return {"filename": name, "extension": ext, **extra}


class FakeSlskd:
    def __init__(self, logged_in=True, states=()):
        self.server = self
        self.searches = self
        self.transfers = self
        self.logged_in = logged_in
        self.states = list(states)
        self.enqueued = []

    def state(self, search_id=None, includeResponses=False):
        if search_id is None:
            return {"isLoggedIn": self.logged_in}
        return self.states.pop(0)

    def search_text(self, text, **kwargs):
        self.search_args = (text, kwargs)
        return {"id": "s1"}

    def enqueue(self, username, files):
        self.enqueued.append((username, files))
        return username != "flaky"


class TestFlattenSearchResponses:
    def test_filters_extensions_case_and_dot_insensitively(self):
        responses = [
            response("u1", [file("a.mp3", "MP3"), file("b.flac", ".flac"), file("c.ogg", "ogg")]),
            response("u2", locked=[file("d.mp3", "mp3")]),
        ]

        out = flatten_search_responses(responses)

        assert [(c.username, c.file["filename"], c.locked) for c in out] == [
            ("u1", "a.mp3", False),
            ("u1", "b.flac", False),
            ("u2", "d.mp3", True),
        ]

    def test_can_exclude_locked_and_restrict_extensions(self):
        responses = [
            response("u", [file("a.mp3", "mp3"), file("b.flac", "flac")], [file("c.flac", "flac")])
        ]

        out = flatten_search_responses(
            responses, extensions=frozenset({"flac"}), include_locked=False
        )

        assert [c.file["filename"] for c in out] == ["b.flac"]


class TestFormatCandidateLabel:
    def test_mp3_with_bitrate(self):
        c = SearchCandidate(
            "u", file("a.mp3", "mp3", size=2048, length=180, bitRate=320), locked=False
        )
        assert format_candidate_label(c) == "u | a.mp3 | 2 KiB | 180s | 320 kbps"

    def test_locked_flac_with_bit_depth(self):
        c = SearchCandidate("u", file("a.flac", "flac", bitDepth=24), locked=True)
        assert format_candidate_label(c) == "u | a.flac | 24-bit [locked]"


class TestServer:
    def test_not_logged_in_raises(self):
        with pytest.raises(RuntimeError):
            check_server_ready(FakeSlskd(logged_in=False))

    def test_search_waits_for_completion_then_filters(self, no_sleep):
        client = FakeSlskd(
            states=[
                {"isComplete": False},
                {
                    "isComplete": True,
                    "responses": [
                        response("u", [file("a.mp3", "mp3", bitRate=128), file("b.flac", "flac")])
                    ],
                },
            ]
        )

        out = search_and_collect(client, "query", mp3_bitrate_kbps=320)

        assert [c.file["filename"] for c in out] == ["b.flac"]
        assert client.search_args == ("query", {"searchTimeout": 45_000})

    def test_enqueue_groups_by_user_and_reports_failures(self):
        client = FakeSlskd()
        candidates = [
            SearchCandidate("u1", file("a", "mp3"), locked=False),
            SearchCandidate("flaky", file("b", "mp3"), locked=False),
            SearchCandidate("u1", file("c", "mp3"), locked=False),
        ]

        assert enqueue_candidates(client, candidates) is False
        assert client.enqueued == [
            ("u1", [file("a", "mp3"), file("c", "mp3")]),
            ("flaky", [file("b", "mp3")]),
        ]


class TestConfig:
    @pytest.fixture
    def write_config(self, tmp_path, monkeypatch):
        path = tmp_path / "config.toml"
        monkeypatch.setattr(soulseek.config, "TOML_PATH", path)
        return path.write_text

    def test_defaults(self, write_config):
        write_config('[soulseek]\nhost = "http://h"\napi_key = "k"\n')
        cfg = Config()
        assert (cfg.host, cfg.api_key, cfg.url_base, cfg.verify_ssl, cfg.request_timeout) == (
            "http://h",
            "k",
            "/",
            True,
            None,
        )

    def test_legacy_slskd_section(self, write_config):
        write_config('[slskd]\nhost = "http://h"\napi_key = "k"\nrequest_timeout = 5\n')
        assert Config().request_timeout == 5.0

    @pytest.mark.parametrize("content", ["", '[soulseek]\nhost = "http://h"\n'])
    def test_missing_settings_raise(self, write_config, content):
        write_config(content)
        with pytest.raises(SoulseekConfigError):
            Config()
