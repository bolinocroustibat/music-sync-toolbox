import sys
from pathlib import Path

from local_files import logger, get_music_files, MusicFile, rename_file


def rename_files_from_tags(media_path: Path) -> None:
    """Rename music files based on their ID3 tags.

    For each file under ``media_path``, extracts artist and title from metadata
    and renames to ``artist - title.ext``. Prompts before each rename.

    Raises:
        SystemExit: If the media directory doesn't exist or has no audio files.
    """
    if not media_path.is_dir():
        logger.error(f"Media directory not found: {media_path}")
        sys.exit(1)

    logger.info(f"Using media directory: {media_path}")

    audio_files: list[MusicFile] = get_music_files(media_path)
    if not audio_files:
        logger.error("No audio files found")
        sys.exit(1)

    logger.info(f"Found {len(audio_files)} audio files")

    renamed = 0
    skipped = 0
    already_correct = 0
    for music_file in audio_files:
        if music_file.artist and music_file.title:
            was_renamed, was_skipped = rename_file(music_file)
            if was_renamed:
                renamed += 1
            elif was_skipped:
                skipped += 1
            else:
                already_correct += 1
        else:
            logger.warning(f"Missing artist or title tags in: {music_file.path}")
            skipped += 1

    logger.info("\nSummary:")
    logger.success(f"Files renamed: {renamed}")
    logger.info(f"Files already correctly named: {already_correct}")
    logger.warning(f"Files skipped: {skipped}")


if __name__ == "__main__":
    import argparse

    from cli_helpers import activate_argcomplete, add_media_path_argument

    parser = argparse.ArgumentParser(
        description="Rename music files from ID3 tags (artist - title.ext).",
    )
    add_media_path_argument(parser, required=True)
    activate_argcomplete(parser)
    ns = parser.parse_args()
    path = ns.path.expanduser().resolve()
    rename_files_from_tags(path)
