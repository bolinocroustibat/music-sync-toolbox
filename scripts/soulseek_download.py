import sys
from pathlib import Path

import inquirer
from requests.exceptions import RequestException

from logger import FileLogger
from soulseek.client import make_client
from soulseek.config import Config as SoulseekConfig, SoulseekConfigError
from soulseek.search_download import (
    check_server_ready,
    enqueue_candidates,
    format_candidate_label,
    search_and_collect,
)

logger = FileLogger(Path("scripts") / "soulseek_download.log")


def _parse_optional_bitrate(raw: str) -> int | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        v = int(s)
    except ValueError:
        raise ValueError("not an integer") from None
    if v <= 0:
        raise ValueError("must be positive")
    return v


def main() -> None:
    try:
        cfg = SoulseekConfig()
    except SoulseekConfigError as e:
        logger.error(str(e))
        sys.exit(1)

    client = make_client(cfg)

    try:
        check_server_ready(client)
    except (RuntimeError, RequestException) as e:
        logger.error(f"Cannot reach slskd or Soulseek is not ready: {e}")
        sys.exit(1)

    questions = [
        inquirer.Text(
            "query",
            message="Search Soulseek",
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers or not (answers.get("query") or "").strip():
        logger.error("Search cancelled or empty query")
        sys.exit(1)

    query = answers["query"].strip()

    format_questions = [
        inquirer.Checkbox(
            "formats",
            message="File types to include in results",
            choices=[("mp3", "mp3"), ("flac", "flac")],
            default=["mp3", "flac"],
        ),
    ]
    format_answers = inquirer.prompt(format_questions)
    if not format_answers:
        logger.error("Cancelled")
        sys.exit(1)

    fmt_list = format_answers.get("formats") or []
    if not fmt_list:
        logger.error("Select at least one file type (mp3 or flac).")
        sys.exit(1)

    extensions = frozenset(str(x).lower() for x in fmt_list)

    br_questions = [
        inquirer.Text(
            "bitrate",
            message="Exact MP3 bitrate in kbps (leave empty to skip; FLAC rows ignore this)",
            default="",
        ),
    ]
    br_answers = inquirer.prompt(br_questions)
    if br_answers is None:
        logger.error("Cancelled")
        sys.exit(1)

    try:
        mp3_bitrate_kbps = _parse_optional_bitrate(br_answers.get("bitrate") or "")
    except ValueError:
        logger.error("Invalid bitrate: enter a positive integer or leave empty.")
        sys.exit(1)

    ext_label = ", ".join(sorted(extensions))
    br_label = f", MP3 bitrate == {mp3_bitrate_kbps} kbps" if mp3_bitrate_kbps else ""
    logger.info(f"Searching: {query!r} ({ext_label}{br_label}) …")

    try:
        candidates = search_and_collect(
            client,
            query,
            extensions=extensions,
            mp3_bitrate_kbps=mp3_bitrate_kbps,
        )
    except RequestException as e:
        logger.error(f"Search request failed: {e}")
        sys.exit(1)

    if not candidates:
        logger.warning("No files match your filters in search results.")
        sys.exit(0)

    choices: list[tuple[str, int]] = [
        (format_candidate_label(c), i) for i, c in enumerate(candidates)
    ]
    pick_questions = [
        inquirer.Checkbox(
            "indices",
            message="Select files to download (space toggles, enter confirms)",
            choices=choices,
        ),
    ]
    pick_answers = inquirer.prompt(pick_questions)
    if not pick_answers:
        logger.error("Selection cancelled")
        sys.exit(1)

    indices = sorted(pick_answers.get("indices") or [])
    if not indices:
        logger.warning("No files selected.")
        sys.exit(0)

    selected = [candidates[i] for i in indices]
    logger.info(f"Enqueueing {len(selected)} download(s) via slskd…")

    try:
        ok = enqueue_candidates(client, selected)
    except RequestException as e:
        logger.error(f"Enqueue failed: {e}")
        sys.exit(1)

    if ok:
        logger.success("Download(s) enqueued. Check slskd for transfer progress.")
    else:
        logger.warning(
            "One or more enqueue calls returned false; check slskd logs and transfers."
        )


if __name__ == "__main__":
    main()
