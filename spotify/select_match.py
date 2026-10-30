from spotify.logger import logger


def select_match(matches: list[dict]) -> str | None:
    """Let user select a match from the list of potential matches

    Args:
        matches: List of potential matches with id, name, and artist

    Returns:
        str | None: Selected track ID or None if skipped/invalid
    """
    # Show all potential matches
    logger.info("\nPotential matches from Spotify:")
    for i, track in enumerate(matches, 1):
        logger.info(f"{i}. Track: {track['name']}")
        logger.info(f"   Artist: {track['artist']}")

    # Let user choose with 1 as default
    choice = input("\nSelect match number (1 is default, 's' to skip): ").strip().lower()
    if choice == "s":
        logger.warning("Track skipped")
        return None

    if choice == "" or choice == "1":
        choice = "1"

    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        match = matches[int(choice) - 1]
        logger.success(f'Selected from Spotify: "{match["name"]} - {match["artist"]}"')
        return match["id"]

    logger.warning("Invalid choice - track skipped")
    return None
