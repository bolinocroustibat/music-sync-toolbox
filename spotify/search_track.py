import spotipy

from spotify.logger import logger

MAX_MATCHES_TO_DISPLAY = 4  # Maximum number of matches to show for each track


def search_track(
    sp: spotipy.Spotify, track_name: str, artist_name: str, file_name: str | None = None
) -> list[dict] | None:
    """Search for a track on Spotify using track name and artist.

    Performs a Spotify search using the track name and artist name to find
    potential matches. The search uses Spotify's search API with specific
    track and artist filters for better accuracy.

    Args:
        sp: Authenticated Spotify client instance
        track_name: Name of the track to search for
        artist_name: Name of the artist to search for
        file_name: Optional name of the local file being processed (for logging)

    Returns:
        list[dict] | None: List of potential matches, each containing:
            - id: Spotify track ID
            - name: Track name
            - artist: Artist name
            Returns None if no matches found or search fails.

    Note:
        - Maximum of 4 matches are returned (MAX_MATCHES_TO_DISPLAY)
        - Search query format: "track:{track_name} artist:{artist_name}"
        - Only tracks with valid name and artist fields are included in results
        - If track_name or artist_name is empty, returns None immediately
    """
    if not track_name or not artist_name:
        if file_name:
            logger.error(f"Missing tags for local file {file_name}")
        return None

    query = f"track:{track_name} artist:{artist_name}"
    if file_name:
        logger.info(f'\nLocal file: "{file_name}"')
    logger.info(f'\nSearching Spotify for "{artist_name} - {track_name}"')

    try:
        results = sp.search(query, type="track", limit=5)
        if not results or not results.get("tracks") or not results["tracks"].get("items"):
            logger.error("No matches found on Spotify")
            return None

        # Format matches
        matches: list[dict] = []
        for track in results["tracks"]["items"]:
            if not track.get("name") or not track.get("artists"):
                continue

            matches.append(
                {
                    "id": track["id"],
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                }
            )

        if not matches:
            logger.error("No valid matches found on Spotify")
            return None

        # Only return first N matches
        return matches[:MAX_MATCHES_TO_DISPLAY]

    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        logger.error(f"Query was: {query}")
        return None
