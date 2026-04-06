import re
import inquirer
from inquirer_prompt import prompt

from local_files.logger import logger
from local_files.music_file import MusicFile


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename.

    Replaces characters that are not allowed in file names with underscores.
    This ensures the filename is compatible with the file system.

    Invalid characters include: < > : " / \\ | ? *
    """
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, "_", filename)


def rename_file(music_file: MusicFile, confirm: bool = True) -> tuple[bool, bool]:
    """Rename file to 'artist - title.ext' format

    Args:
        music_file: MusicFile object (or subclass like DTag) containing path, artist, and title information
        confirm: Whether to ask for user confirmation before renaming (default: True)

    Returns:
        tuple[bool, bool]: (was_renamed, was_skipped)
    """
    try:
        # Sanitize artist and title
        artist = sanitize_filename(music_file.artist)
        title = sanitize_filename(music_file.title)

        # Create new filename
        new_name = f"{artist} - {title}{music_file.suffix}"
        new_path = music_file.path.parent / new_name

        # Skip if filename is already correct
        if music_file.path.name == new_name:
            logger.info(f"File already correctly named: {music_file.path}")
            return False, False

        # Check if target file already exists
        if new_path.exists():
            logger.warning(f"Target file already exists: {new_path}")
            return False, True

        # Ask for confirmation if requested
        if confirm:
            questions = [
                inquirer.Confirm(
                    "confirm",
                    message=f"\nRename '{music_file.path.name}' to '{new_name}'?",
                    default=False,
                ),
            ]
            answers = prompt(questions)
            if not answers or not answers["confirm"]:
                logger.info(f"Skipping rename of: {music_file.path}")
                return False, True

        # Rename file
        music_file.path.rename(new_path)
        logger.success(f"Renamed: {music_file.path.name} -> {new_name}")
        return True, False

    except Exception as e:
        logger.error(f"Error renaming {music_file.path}: {e}")
        return False, True
