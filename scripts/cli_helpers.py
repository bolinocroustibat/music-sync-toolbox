"""Shared argparse helpers for media path and optional shell completion."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_media_path_argument(
    parser: argparse.ArgumentParser,
    *,
    required: bool,
) -> None:
    """Register --path / -p with optional directory tab-completion (argcomplete)."""
    kwargs: dict = {
        "dest": "path",
        "type": Path,
        "metavar": "DIR",
        "help": "Directory containing music files.",
    }
    if required:
        kwargs["required"] = True
    else:
        kwargs["required"] = False
        kwargs["default"] = None

    action = parser.add_argument("--path", "-p", **kwargs)
    try:
        from argcomplete.completers import DirectoriesCompleter

        action.completer = DirectoriesCompleter()
    except ImportError:
        pass


def activate_argcomplete(parser: argparse.ArgumentParser) -> None:
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass
