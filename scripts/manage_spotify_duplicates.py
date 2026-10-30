import sys
import time
from bisect import bisect_left
from pathlib import Path
from typing import TypedDict

import spotipy

from spotify import setup_spotify, select_playlist as select_spotify_playlist
from logger import FileLogger

logger = FileLogger(Path("scripts") / "spotify_duplicates.log")


class TrackInstance(TypedDict):
    name: str
    added_at: str
    position: int


def find_duplicates(
    sp: spotipy.Spotify, playlist_id: str
) -> dict[str, list[TrackInstance]]:
    """Find duplicate tracks in a playlist"""
    logger.info("Fetching playlist tracks...")
    logger.info(f"Using playlist ID: {playlist_id}")

    # Special case for Liked Songs
    if playlist_id == "liked":
        logger.info(
            "Note: Liked Songs cannot contain duplicates by design - Spotify automatically prevents this."
        )
        return {}

    # Get all tracks from playlist
    tracks: dict[
        str, list[TrackInstance]
    ] = {}  # key: track_id, value: list of [track_info, added_at]
    try:
        # Regular playlist
        results = sp.playlist_items(
            playlist_id,
            fields="items.track.id,items.track.name,items.track.artists,items.added_at,next",
        )
        logger.info("Successfully connected to Spotify API")
    except Exception as e:
        logger.error(f"Error fetching playlist items: {e}")
        return {}

    total_tracks = 0
    position = 0
    while results:
        try:
            batch_size = len(results["items"])
            total_tracks += batch_size
            logger.info(
                f"Processing batch of {batch_size} tracks (total: {total_tracks})"
            )

            for item in results["items"]:
                item_position = position
                position += 1
                track = item["track"]
                # Skip empty tracks and local files (no Spotify ID to compare)
                if not track or not track["id"]:
                    continue

                track_id = track["id"]
                artist = (
                    track["artists"][0]["name"]
                    if track["artists"]
                    else "Unknown Artist"
                )
                track_name = f"{track['name']} - {artist}"  # Keep for display purposes

                track_instance: TrackInstance = {
                    "name": track_name,
                    "added_at": item["added_at"],
                    "position": item_position,
                }

                if track_id in tracks:
                    tracks[track_id].append(track_instance)
                else:
                    tracks[track_id] = [track_instance]

            if results["next"]:
                logger.info("Fetching next batch of tracks...")
                results = sp.next(results)
            else:
                logger.info("Finished fetching all tracks")
                break
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            break

    # Filter only duplicates
    duplicates = {k: v for k, v in tracks.items() if len(v) > 1}
    logger.info(f"Found {len(duplicates)} tracks with duplicates")
    return duplicates


def remove_duplicates(
    sp: spotipy.Spotify, playlist_id: str, duplicates: dict[str, list[TrackInstance]]
) -> None:
    """Remove duplicate tracks keeping the oldest one"""
    if not duplicates:
        return

    # Spotify ignores "positions" when removing playlist items, so every copy of
    # a duplicated track is removed, then the oldest copy is re-added where it was.
    keep: list[tuple[int, str]] = []  # (position, track_id) of the copy to keep
    dropped_positions: list[int] = []
    for track_id, instances in duplicates.items():
        # Sort by added_at date in ascending order (oldest first, newest last)
        sorted_by_date = sorted(instances, key=lambda x: (x["added_at"], x["position"]))
        keep.append((sorted_by_date[0]["position"], track_id))
        dropped_positions.extend(i["position"] for i in sorted_by_date[1:])
    keep.sort()
    dropped_positions.sort()

    # Once dropped copies are gone, a kept copy moves up by the number of
    # dropped copies before it. Re-adding in ascending order keeps that exact.
    batches: list[tuple[int, list[str]]] = []  # (target position, track_ids)
    for position, track_id in keep:
        target = position - bisect_left(dropped_positions, position)
        last = batches[-1] if batches else None
        if last and last[0] + len(last[1]) == target and len(last[1]) < 100:
            last[1].append(track_id)
        else:
            batches.append((target, [track_id]))

    track_ids = [track_id for _, track_id in keep]
    logger.info(f"Tracks to re-add if anything fails: {', '.join(track_ids)}")

    try:
        # Spotify API can only remove 100 tracks at a time
        for i in range(0, len(track_ids), 100):
            sp.playlist_remove_all_occurrences_of_items(playlist_id, track_ids[i : i + 100])
            time.sleep(1)  # Rate limiting
    except Exception as e:
        logger.error(f"Error removing tracks: {e}")
        return

    readded = 0
    try:
        for target, batch in batches:
            sp.playlist_add_items(playlist_id, batch, position=target)
            readded += len(batch)
            time.sleep(1)  # Rate limiting
    except Exception as e:
        logger.error(f"Error re-adding tracks: {e}")
        logger.error(f"Add these tracks back manually: {', '.join(track_ids[readded:])}")
        return

    logger.success(f"Successfully removed {len(dropped_positions)} duplicate tracks")


def main() -> None:
    sp = setup_spotify()

    # Get playlist ID from user selection
    playlist_id: str = select_spotify_playlist(sp)

    duplicates = find_duplicates(sp, playlist_id)

    if not duplicates:
        logger.success("No duplicates found!")
        return

    logger.info(
        f"\nFound {sum(len(v) - 1 for v in duplicates.values())} duplicate tracks:"
    )
    for track_id, instances in duplicates.items():
        # Get the track name from the first instance (they're all the same track)
        track_name = instances[0]["name"]
        logger.info(f"\n{track_name}")
        for i, track in enumerate(sorted(instances, key=lambda x: x["added_at"]), 1):
            logger.info(f"  {i}. Added on: {track['added_at']}")

    logger.warning(
        "\nSpotify can only remove every copy of a track: the oldest copy is then "
        "re-added at its position, so its 'date added' becomes today."
    )
    if input("Do you want to remove duplicates? (y/N): ").lower() == "y":
        remove_duplicates(sp, playlist_id, duplicates)


if __name__ == "__main__":
    if not Path("config.toml").is_file():
        logger.error("Configuration file not found")
        sys.exit(1)

    main()
