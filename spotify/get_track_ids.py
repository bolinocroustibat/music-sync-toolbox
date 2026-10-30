import sys

import spotipy

from spotify.logger import logger


def get_playlist_track_ids(sp: spotipy.Spotify, spotify_playlist_id: str) -> set[str]:
    """Extract track IDs from a Spotify playlist for duplicate detection.

    Fetches all track IDs from a Spotify playlist to check for existing tracks
    before adding new ones. This prevents duplicate tracks from being added to
    the playlist. Handles both regular playlists and the special "liked" playlist
    (user's Liked Songs).

    Args:
        sp: Authenticated Spotify client instance
        spotify_playlist_id: Spotify playlist ID or "liked" for Liked Songs

    Returns:
        Set of Spotify track IDs (strings) that are already in the playlist

    Raises:
        SystemExit: If there's an error fetching the playlist

    Note:
        - Handles pagination automatically for large playlists
        - Skips tracks with missing IDs
        - Returns an empty set if the playlist is empty or inaccessible
        - Track IDs are unique identifiers used by Spotify's API
    """
    logger.info("Fetching existing tracks from Spotify playlist...")
    existing_tracks: set[str] = set()
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
        else:
            # Regular playlist
            results = sp.playlist_items(spotify_playlist_id)
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("id"):
                        continue
                    existing_tracks.add(track["id"])
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)
    return existing_tracks
