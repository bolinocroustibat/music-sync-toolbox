from ytmusicapi import YTMusic
import sys
from ytmusic.logger import logger


def get_playlist_track_details(ytm: YTMusic, ytmusic_playlist_id: str) -> list[dict]:
    """
    Get track details (name, artist) from a YouTube Music playlist or Liked Music.

    Args:
        ytm: Authenticated YTMusic client instance.
        ytmusic_playlist_id: Playlist ID or "LM" for Liked Music.

    Returns:
        list[dict]: List of tracks, each with "name" and "artist" keys.

    Raises:
        SystemExit: If fetching fails or no tracks are found.

    Notes:
        - Exits if no tracks are found or an error occurs.
        - Handles both regular playlists and Liked Music.
    """
    logger.info(f'Fetching tracks from YouTube Music playlist "{ytmusic_playlist_id}"...')
    tracks: list[dict] = []
    try:
        if ytmusic_playlist_id == "LM":
            # Special case for Liked Music
            results = ytm.get_liked_songs(limit=None)
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
        else:
            # Regular playlist
            results = ytm.get_playlist(ytmusic_playlist_id, limit=None)
            for track in results["tracks"]:
                if not track.get("title") or not track.get("artists"):
                    continue
                tracks.append(
                    {
                        "name": track["title"],
                        "artist": track["artists"][0]["name"],
                    }
                )
    except Exception as e:
        logger.error(f"Error fetching YouTube Music playlist: {e}")
        sys.exit(1)

    if not tracks:
        logger.warning("No tracks found in YouTube Music playlist")
        sys.exit(1)

    logger.info(f"Found {len(tracks)} tracks in YouTube Music playlist")
    return tracks
