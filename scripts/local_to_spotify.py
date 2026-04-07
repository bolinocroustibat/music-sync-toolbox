import sys
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from spotify import (
    Config as SpotifyConfig,
    setup_spotify,
    select_playlist as select_spotify_playlist,
    search_track as search_spotify_track,
    select_match as select_spotify_match,
    add_track as add_track_to_spotify,
)
from logger import FileLogger
from local_files import get_music_files, MusicFile

config = SpotifyConfig()
logger = FileLogger(Path("scripts") / "local_to_spotify.log")


def main(media_path: Path) -> None:
    # Initialize Spotify client
    sp = setup_spotify()

    # Get playlist ID from config or user selection
    playlist_id = select_spotify_playlist(sp, config.playlist_id)

    if not media_path.is_dir():
        logger.error(f"Media directory not found: {media_path}")
        sys.exit(1)

    music_files: list[MusicFile] = get_music_files(media_path)

    logger.info(f"Found {len(music_files)} music files in {media_path}")

    if not music_files:
        logger.warning("No local .mp3, .flac, or .m4a files found in directory")
        sys.exit(1)

    tracks_added = 0
    tracks_skipped = 0

    # Get existing tracks in playlist
    logger.info("Fetching existing tracks from playlist...")
    existing_tracks: set[str] = set()
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            if item["track"] and item["track"]["id"]:
                existing_tracks.add(item["track"]["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break

    # Process each music file
    logger.info("\nProcessing files...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(music_files))
        for music_file in music_files:
            matches = search_spotify_track(
                sp, music_file.title, music_file.artist, music_file.path.name
            )
            if matches:
                track_id = select_spotify_match(sp, matches)
                if track_id:
                    if track_id in existing_tracks:
                        logger.warning(
                            "Track already exists in Spotify playlist - skipping"
                        )
                        tracks_skipped += 1
                        progress.advance(task)
                        continue

                    success, _ = add_track_to_spotify(sp, track_id, playlist_id, 1)
                    if success:
                        tracks_added += 1
                    else:
                        tracks_skipped += 1
                else:
                    tracks_skipped += 1
            else:
                tracks_skipped += 1
            progress.advance(task)

    # Print summary
    logger.info("\nSummary:")
    logger.success(f"Tracks added to Spotify: {tracks_added}")
    logger.warning(f"Tracks skipped: {tracks_skipped}")


if __name__ == "__main__":
    import argparse

    from cli_helpers import activate_argcomplete, add_media_path_argument

    parser = argparse.ArgumentParser(
        description="Add local music files to a Spotify playlist.",
    )
    add_media_path_argument(parser, required=True)
    activate_argcomplete(parser)
    ns = parser.parse_args()
    main(ns.path.expanduser().resolve())
