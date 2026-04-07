import sys
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from local_files import logger, AUDIO_FILES_EXTENSIONS, rename_file
from discogs import DTag, Config as DiscogsConfig
import discogs_client as dc


def update_tags_from_discogs(directory: Path, config=None, ds=None) -> None:
    """Update music file tags using Discogs metadata.

    Main function that processes all audio files in the specified directory,
    searches for matching releases on Discogs, and updates the file tags
    with metadata including genres, year, and cover art.

    The function creates DTag instances for each audio file, searches Discogs
    for matching releases, and updates the file tags based on the configuration
    settings. It also optionally renames files if the rename_file option is enabled.

    Args:
        directory: Path to the directory containing audio files to process.
        config: Configuration object containing Discogs and file processing settings.
        ds: Authenticated Discogs client instance.

    Raises:
        ValueError: If config or ds parameters are not provided.
        SystemExit: If the directory doesn't exist or is invalid.

    Note:
        - Processes all supported audio files recursively in the directory
        - Uses fuzzy matching to find the best Discogs release for each track
        - Updates genres, year, and cover art based on configuration settings
        - Optionally renames files to 'artist - title.ext' format
        - Provides detailed progress tracking and summary statistics
        - Respects API rate limits with built-in delays and retry logic
    """
    if not config or not ds:
        raise ValueError("config and ds parameters are required")

    # check if directory path exists and valid
    if not directory.is_dir():
        logger.error(f'Directory "{directory}" not found.')
        sys.exit(1)

    # create discogs session
    me = ds.identity()
    logger.log(f"Discogs User: {me}")

    logger.log(f"Looking for files in {directory}")
    logger.warning("Indexing audio files... Please wait\n")
    not_found: int = 0
    found: int = 0
    renamed: int = 0
    total: int = 0
    files = {
        DTag(path=p, original_filename=p.name, config=config, ds=ds)
        for p in directory.rglob("*")
        if p.suffix in AUDIO_FILES_EXTENSIONS
    }

    logger.info("\nProcessing files...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        for tag_file in files:
            total += 1
            logger.log(
                "____________________________________________________________________\n"
                + f"File: {tag_file.original_filename}"
            )

            # Rename file
            if config.rename_file and tag_file.artist and tag_file.title:
                was_renamed, was_skipped = rename_file(tag_file, confirm=False)
                if was_renamed:
                    renamed += 1

            # Search on Discogs and update
            if tag_file.search() is None:
                tag_file.save()
                found += 1
            else:
                not_found += 1

            # Print file results info
            if tag_file.genres_updated:
                logger.success(f"- Genres: {tag_file.local_genres} ➔ {tag_file.genres}")
            else:
                logger.log(f"- Genres: {tag_file.local_genres} ➔ not updated")

            if tag_file.year_updated:
                logger.success(f"- Year: {tag_file.local_year} ➔ {tag_file.year}")
            else:
                logger.log(f"- Year: {tag_file.local_year} ➔ not updated")

            if tag_file.cover_updated:
                logger.success("- Cover: ➔ updated\n")
            else:
                logger.log("- Cover: ➔ not updated\n")

            progress.advance(task)

    logger.log(f"Total files: {total}")
    logger.success(f"With Discogs info found: {found}")
    logger.error(f"With Discogs info not found: {not_found}")
    logger.warning(f"Renamed: {renamed}\n")
    input("Press Enter to exit...")


if __name__ == "__main__":
    import argparse

    from cli_helpers import activate_argcomplete, add_media_path_argument

    parser = argparse.ArgumentParser(
        description="Update ID3 tags from Discogs for files under a directory.",
    )
    add_media_path_argument(parser, required=True)
    activate_argcomplete(parser)
    ns = parser.parse_args()
    media_path = ns.path.expanduser().resolve()

    config_path = Path("config.toml")
    if not config_path.is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    discogs_config = DiscogsConfig()
    ds = dc.Client("discogs_tag/0.5", user_token=discogs_config.token)
    update_tags_from_discogs(media_path, discogs_config, ds)
