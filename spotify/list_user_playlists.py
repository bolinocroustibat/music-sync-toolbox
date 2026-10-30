from spotify.types import SpotifyPlaylistInfo
import spotipy
from spotify.logger import logger


def list_user_playlists(sp: spotipy.Spotify) -> list[SpotifyPlaylistInfo]:
    """Retrieve all playlists owned by the authenticated user.

    Fetches all playlists that the authenticated user owns from Spotify.
    This includes both public and private playlists, but excludes playlists
    owned by other users that the user follows.

    Args:
        sp: Authenticated Spotify client instance

    Returns:
        list[SpotifyPlaylistInfo]: List of playlist information dictionaries,
            each containing name, id, and track_count. Returns empty list
            if an error occurs.

    Note:
        This function only returns playlists owned by the authenticated user.
        Playlists followed from other users are not included in the results.
    """
    logger.info("Fetching your Spotify playlists...")

    try:
        # Get user playlists
        results = sp.current_user_playlists()
        user_playlists: list[SpotifyPlaylistInfo] = []

        while results:
            for playlist in results["items"]:
                playlist_info: SpotifyPlaylistInfo = {
                    "name": playlist["name"],
                    "id": playlist["id"],
                    "track_count": playlist["tracks"]["total"],
                }
                user_playlists.append(playlist_info)
            results = sp.next(results) if results["next"] else None

        # Sort playlists alphabetically by name (case-insensitive)
        user_playlists.sort(key=lambda x: x["name"].lower())

        return user_playlists

    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return []
