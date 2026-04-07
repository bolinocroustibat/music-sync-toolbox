from ytmusicapi import YTMusic
import inquirer
from ytmusic.list_user_playlists import list_user_playlists
from ytmusic.logger import logger


def select_playlist(ytm: YTMusic, playlist_id: str | None = None) -> str:
    """
    Select a YouTube Music playlist for operations.

    Either uses a pre-configured playlist ID or prompts the user to select
    from their owned playlists. Supports special handling for "Liked Music".

    Args:
        ytm: Authenticated YTMusic client instance.
        playlist_id: Optional pre-configured playlist ID to use directly.
            If "LM", uses the user's Liked Music playlist.

    Returns:
        str: The selected playlist ID.

    Raises:
        Exception: If no playlists are found for the user.
        KeyboardInterrupt: If user cancels the selection process.
        Exception: If the specified playlist_id is invalid or inaccessible.

    Notes:
        If playlist_id is provided but invalid, the function falls back
        to interactive playlist selection. The "LM" playlist_id is
        a special case that refers to the user's Liked Music.
    """
    if playlist_id:
        try:
            if playlist_id == "LM":
                # Special case for Liked Music
                try:
                    ytm.get_liked_songs(
                        limit=1
                    )  # Just check if we can access liked songs
                    logger.success('Using YouTube Music playlist "Liked Music"')
                    return playlist_id
                except Exception as e:
                    logger.error(f"Error accessing liked music: {e}")
                    # Fall through to manual selection
            else:
                playlist = ytm.get_playlist(playlist_id)
                logger.success(f'Using YouTube Music playlist "{playlist["title"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(ytm)

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
            message="Select a YouTube Music playlist",
            choices=choices,
            carousel=True,  # Show all options without scrolling
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using YouTube Music playlist "{selected_name}"')
    return selected_id
