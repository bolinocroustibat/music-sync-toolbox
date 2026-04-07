import spotipy
import inquirer
from spotify.list_user_playlists import list_user_playlists
from spotify.logger import logger


def select_playlist(sp: spotipy.Spotify, playlist_id: str | None = None) -> str:
    """Select a Spotify playlist for operations.

    Either uses a pre-configured playlist ID or prompts the user to select
    from their owned playlists. Supports special handling for "Liked Songs".

    Args:
        sp: Authenticated Spotify client instance
        playlist_id: Optional pre-configured playlist ID to use directly.
            If "liked", uses the user's Liked Songs playlist.

    Returns:
        str: The selected playlist ID

    Raises:
        Exception: If no playlists are found for the user
        KeyboardInterrupt: If user cancels the selection process
        Exception: If the specified playlist_id is invalid or inaccessible

    Note:
        If playlist_id is provided but invalid, the function falls back
        to interactive playlist selection. The "liked" playlist_id is
        a special case that refers to the user's Liked Songs.
    """
    if playlist_id:
        try:
            if playlist_id == "liked":
                # Special case for Liked Songs
                try:
                    sp.current_user_saved_tracks(
                        limit=1
                    )  # Just check if we can access liked tracks
                    logger.success('Using Spotify playlist "Liked Songs"')
                    return playlist_id
                except Exception as e:
                    logger.error(f"Error accessing liked songs: {e}")
                    # Fall through to manual selection
            else:
                playlist = sp.playlist(playlist_id)
                logger.success(f'Using Spotify playlist "{playlist["name"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(sp)

    if not playlists:
        raise Exception("No playlists found for user")

    # Create choices list for inquirer with formatted display
    choices = [
        (f"{playlist['name']} ({playlist['track_count']} tracks)", playlist["id"])
        for playlist in playlists
    ]

    questions = [
        inquirer.List(
            "playlist_id",
            message="Select a Spotify playlist",
            choices=choices,
            carousel=True,  # Show all options without scrolling
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using Spotify playlist "{selected_name}"')
    return selected_id
