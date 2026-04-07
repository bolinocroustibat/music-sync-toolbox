"""Soulseek downloads via a running slskd instance (REST API)."""

from soulseek.client import make_client
from soulseek.config import Config, SoulseekConfigError
from soulseek.search_download import (
    SearchCandidate,
    check_server_ready,
    enqueue_candidates,
    filter_mp3_exact_bitrate,
    flatten_search_responses,
    format_candidate_label,
    search_and_collect,
    wait_for_search,
)

__all__ = [
    "Config",
    "SoulseekConfigError",
    "SearchCandidate",
    "check_server_ready",
    "enqueue_candidates",
    "filter_mp3_exact_bitrate",
    "flatten_search_responses",
    "format_candidate_label",
    "make_client",
    "search_and_collect",
    "wait_for_search",
]
