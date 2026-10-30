import spotipy

from spotify.logger import logger
from spotify.types import SpotifyPlaylistInfo


def list_user_playlists(sp: spotipy.Spotify) -> list[SpotifyPlaylistInfo]:
    """Retrieve the playlists the authenticated user can add tracks to.

    Fetches all playlists that the authenticated user owns or collaborates on,
    public and private, preceded by the user's Liked Songs (id "liked").
    Playlists owned by other users that the user only follows are excluded.

    Args:
        sp: Authenticated Spotify client instance

    Returns:
        list[SpotifyPlaylistInfo]: Liked Songs, then playlists sorted by name,
            each containing name, id, and track_count. Returns empty list
            if an error occurs.
    """
    logger.info("Fetching your Spotify playlists...")

    try:
        user_id = sp.current_user()["id"]

        # Get user playlists
        results = sp.current_user_playlists()
        user_playlists: list[SpotifyPlaylistInfo] = []

        while results:
            for playlist in results["items"]:
                # Tracks can't be added to playlists the user only follows
                if playlist["owner"]["id"] != user_id and not playlist["collaborative"]:
                    continue
                playlist_info: SpotifyPlaylistInfo = {
                    "name": playlist["name"],
                    "id": playlist["id"],
                    "track_count": playlist["tracks"]["total"],
                }
                user_playlists.append(playlist_info)
            results = sp.next(results) if results["next"] else None

        # Sort playlists alphabetically by name (case-insensitive)
        user_playlists.sort(key=lambda x: x["name"].lower())

        liked_songs: SpotifyPlaylistInfo = {
            "name": "Liked Songs",
            "id": "liked",  # Special ID for Liked Songs
            "track_count": sp.current_user_saved_tracks(limit=1)["total"],
        }
        return [liked_songs, *user_playlists]

    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return []
