import sys

import spotipy

from spotify.logger import logger


def get_playlist_track_details(
    sp: spotipy.Spotify, spotify_playlist_id: str, allow_empty: bool = False
) -> list[dict]:
    """Extract track details (name and artist) from a Spotify playlist.

    Fetches all tracks from a Spotify playlist and extracts their basic metadata
    (track name and primary artist) for use in search operations. Handles both
    regular playlists and the special "liked" playlist (user's Liked Songs).

    Args:
        sp: Authenticated Spotify client instance
        spotify_playlist_id: Spotify playlist ID or "liked" for Liked Songs
        allow_empty: Return an empty list instead of exiting when the playlist has no tracks

    Returns:
        List of dictionaries, each containing:
            - id: Spotify track ID (None for local files)
            - name: Track title
            - artist: Primary artist name

    Raises:
        SystemExit: If there's an error fetching the playlist or if no tracks
                   are found in the playlist and allow_empty is False

    Note:
        - Handles pagination automatically for large playlists
        - Skips tracks with missing metadata (name or artist)
        - For multi-artist tracks, only the first artist is included
        - Exits the program if the playlist is empty or inaccessible
    """
    logger.info(f'Fetching tracks from Spotify playlist "{spotify_playlist_id}"...')
    tracks: list[dict] = []
    try:
        if spotify_playlist_id == "liked":
            # Special case for Liked Songs
            results = sp.current_user_saved_tracks()
            while results:
                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    track = item["track"]
                    if not track.get("name") or not track.get("artists"):
                        continue
                    tracks.append(
                        {
                            "id": track.get("id"),
                            "name": track["name"],
                            "artist": track["artists"][0]["name"],
                        }
                    )
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
                    if not track.get("name") or not track.get("artists"):
                        continue
                    tracks.append(
                        {
                            "id": track.get("id"),
                            "name": track["name"],
                            "artist": track["artists"][0]["name"],
                        }
                    )
                if results["next"]:
                    results = sp.next(results)
                else:
                    break
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist: {e}")
        sys.exit(1)

    if not tracks and not allow_empty:
        logger.warning("No tracks found in Spotify playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in Spotify playlist")
    return tracks
