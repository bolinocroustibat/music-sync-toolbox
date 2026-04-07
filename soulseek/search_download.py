from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Iterable

from slskd_api import SlskdClient

# Default slskd search network timeout (ms); library default is 15000.
_DEFAULT_SEARCH_TIMEOUT_MS = 45_000


class SearchCandidate:
    """One downloadable file from search results (username + API file payload)."""

    __slots__ = ("username", "file", "locked")

    def __init__(self, username: str, file: dict[str, Any], *, locked: bool) -> None:
        self.username = username
        self.file = file
        self.locked = locked


def _normalize_extension(ext: str) -> str:
    e = (ext or "").strip().lower()
    if e.startswith("."):
        e = e[1:]
    return e


def flatten_search_responses(
    responses: Iterable[dict[str, Any]],
    *,
    extensions: frozenset[str] | None = None,
    include_locked: bool = True,
) -> list[SearchCandidate]:
    """Turn slskd search `responses` into filtered candidates (mp3/flac by default)."""
    if extensions is None:
        extensions = frozenset({"mp3", "flac"})
    out: list[SearchCandidate] = []
    for item in responses:
        username = item.get("username") or ""
        for f in item.get("files") or []:
            if _normalize_extension(str(f.get("extension", ""))) in extensions:
                out.append(SearchCandidate(username, f, locked=False))
        if include_locked:
            for f in item.get("lockedFiles") or []:
                if _normalize_extension(str(f.get("extension", ""))) in extensions:
                    out.append(SearchCandidate(username, f, locked=True))
    return out


def filter_mp3_exact_bitrate(
    candidates: list[SearchCandidate],
    mp3_bitrate_kbps: int | None,
) -> list[SearchCandidate]:
    """Keep all non-MP3 rows; for MP3, keep only those with bitRate equal to mp3_bitrate_kbps.

    If mp3_bitrate_kbps is None, return candidates unchanged.
    MP3 rows without bitRate are dropped when filtering is active.
    """
    if mp3_bitrate_kbps is None:
        return candidates
    out: list[SearchCandidate] = []
    for c in candidates:
        ext = _normalize_extension(str(c.file.get("extension", "")))
        if ext != "mp3":
            out.append(c)
            continue
        br = c.file.get("bitRate")
        if br is None:
            continue
        try:
            if int(br) == mp3_bitrate_kbps:
                out.append(c)
        except (TypeError, ValueError):
            continue
    return out


def format_candidate_label(c: SearchCandidate) -> str:
    """Human-readable line for menus and logs."""
    fn = c.file.get("filename", "")
    size_b = c.file.get("size")
    length_s = c.file.get("length")
    br = c.file.get("bitRate")
    bd = c.file.get("bitDepth")
    parts = [c.username, fn]
    if size_b is not None:
        parts.append(f"{int(size_b) // 1024} KiB")
    if length_s is not None:
        parts.append(f"{length_s}s")
    if br is not None:
        parts.append(f"{br} kbps")
    elif bd is not None:
        parts.append(f"{bd}-bit")
    suffix = " [locked]" if c.locked else ""
    return " | ".join(str(p) for p in parts if p) + suffix


def check_server_ready(client: SlskdClient) -> None:
    """Raise RuntimeError if slskd is not connected and logged in to Soulseek."""
    state = client.server.state()
    if not state.get("isLoggedIn"):
        raise RuntimeError(
            "slskd is not logged in to the Soulseek server. "
            "Check slskd configuration and network."
        )


def wait_for_search(
    client: SlskdClient,
    search_id: str,
    *,
    poll_interval_s: float = 1.5,
    max_wait_s: float = 90.0,
) -> dict[str, Any]:
    """Poll search state until complete or wall-clock timeout; returns last state dict."""
    deadline = time.monotonic() + max_wait_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = client.searches.state(search_id, includeResponses=True)
        if last.get("isComplete"):
            return last
        time.sleep(poll_interval_s)
    return last


def search_and_collect(
    client: SlskdClient,
    search_text: str,
    *,
    search_timeout_ms: int = _DEFAULT_SEARCH_TIMEOUT_MS,
    poll_interval_s: float = 1.5,
    max_poll_wait_s: float = 90.0,
    extensions: frozenset[str] | None = None,
    include_locked: bool = True,
    mp3_bitrate_kbps: int | None = None,
    **search_kwargs: Any,
) -> list[SearchCandidate]:
    """Run a search, wait for results, return filtered candidates."""
    started = client.searches.search_text(
        search_text,
        searchTimeout=search_timeout_ms,
        **search_kwargs,
    )
    search_id = started["id"]
    state = wait_for_search(
        client,
        search_id,
        poll_interval_s=poll_interval_s,
        max_wait_s=max_poll_wait_s,
    )
    responses = state.get("responses") or []
    flat = flatten_search_responses(
        responses,
        extensions=extensions,
        include_locked=include_locked,
    )
    return filter_mp3_exact_bitrate(flat, mp3_bitrate_kbps)


def enqueue_candidates(client: SlskdClient, candidates: list[SearchCandidate]) -> bool:
    """Enqueue downloads, grouping by remote username. Returns True if all succeeded."""
    if not candidates:
        return True
    by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        by_user[c.username].append(c.file)
    ok = True
    for username, files in by_user.items():
        if not client.transfers.enqueue(username, files):
            ok = False
    return ok
