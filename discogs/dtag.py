import json
import re
import time
from pathlib import Path

import niquests as requests
from discogs_client.exceptions import HTTPError
from rapidfuzz import fuzz, process, utils
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, FLACNoHeaderError, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError
from mutagen._util import MutagenError

from local_files.logger import logger
from local_files.music_file import MusicFile

COVER_TIMEOUT_S = 30


class DTag(MusicFile):
    def __init__(self, path: Path, original_filename: str, config, ds) -> None:
        # Initialize parent class
        super().__init__(path)

        # DTag-specific attributes
        self.original_filename: str = original_filename
        self.config = config
        self.ds = ds
        self.cover_embedded = False
        self.local_genres = ""
        self.genres: str = ""
        self.local_year: str = ""
        self.year: str = ""
        self.year_found: bool = False
        self.genres_found: bool = False
        self.year_updated: bool = False
        self.genres_updated: bool = False
        self.cover_updated: bool = False

        # Get additional tags (genres, year, cover info)
        self._get_additional_tags()

        # Cleaned title and artist, only for searching: the original tags
        # are kept for renaming, so "(Remix)" etc. stay in the file name
        self.search_artist: str = clean(string=self.artist)
        self.search_title: str = clean(string=self.title)

    def __repr__(self) -> str:
        return f"File: {self.path}"

    @property
    def tags_log(self) -> str:
        tags = {
            "file": str(self.path),
            "local": {
                "genre": self.local_genres,
                "year": self.local_year,
                "picture": self.cover_embedded,
            },
            "discogs": {
                "genre_found": self.genres_found,
                "genre": self.genres,
                "year_found": self.year_found,
                "year": self.year,
                "image_found": True if hasattr(self, "image") else False,
            },
        }
        return json.dumps(tags)

    def _get_additional_tags(self) -> None:
        """Extract additional tags (genres, year, cover) that are specific to DTag."""
        if self.suffix.lower() == ".flac":
            try:
                audio = FLAC(self.path)
                if audio.get("genre"):
                    self.local_genres = audio["genre"][0]
                if audio.get("date"):
                    self.local_year = audio["date"][0]
                if audio.pictures:
                    self.cover_embedded = True
            except (FLACNoHeaderError, Exception):
                pass

        elif self.suffix.lower() == ".mp3":
            try:
                audio = EasyID3(self.path)
                if audio.get("genre"):
                    self.local_genres = audio["genre"][0]
                if audio.get("date"):
                    self.local_year = audio["date"][0]

                audio = MP3(self.path)
                for k in audio.keys():
                    if "covr" in k or "APIC" in k:
                        self.cover_embedded = True
            except (HeaderNotFoundError, MutagenError, KeyError):
                pass

        elif self.suffix.lower() == ".m4a":
            try:
                audio = MP4(self.path)
                if audio.get("\xa9gen"):
                    self.local_genres = audio["\xa9gen"][0]
                if audio.get("\xa9day"):
                    self.local_year = audio["\xa9day"][0]
                if audio.get("covr"):
                    self.cover_embedded = True
            except (KeyError, MP4StreamInfoError, MutagenError):
                pass

    def save(self) -> None:
        """
        flac and mp3 support the same keys from mutagen,
        .m4a does not
        """
        if self.year_found is False and self.genres_found is False:
            return

        if self.suffix.lower() not in (".flac", ".mp3", ".m4a"):
            logger.warning(f"Writing tags to {self.suffix} files is not supported.")
            return

        if self.suffix.lower() == ".flac":
            self._image_flac()
            audio = FLAC(self.path)
        elif self.suffix.lower() == ".mp3":
            self._image_mp3()
            audio = EasyID3(self.path)
        elif self.suffix.lower() == ".m4a":
            self._save_m4a()
            return

        if self.genres_found and (self.local_genres != self.genres):
            if self.config.overwrite_genre:
                audio["genre"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["genre"] = self.genres
                    self.genres_updated = True

        if self.year_found and (self.local_year != self.year):
            if self.config.overwrite_year:
                audio["date"] = self.year
                self.year_updated = True
            else:
                if self.local_year == "":
                    audio["date"] = self.year
                    self.year_updated = True

        audio.save()

    def _save_m4a(self) -> None:
        """
        code duplication from self.save
        """
        audio = MP4(self.path)
        if self.genres_found and (self.local_genres != self.genres):
            if self.config.overwrite_genre:
                audio["\xa9gen"] = self.genres
                self.genres_updated = True
            else:
                if self.local_genres == "":
                    audio["\xa9gen"] = self.genres
                    self.genres_updated = True

        if self.year_found and (self.local_year != self.year):
            if self.config.overwrite_year:
                audio["\xa9day"] = self.year
                self.year_updated = True
            else:
                if self.local_year == "":
                    audio["\xa9day"] = self.year
                    self.year_updated = True
        # save image
        cover = self._cover_to_embed()
        if cover:
            audio["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]
            self.cover_updated = True
        audio.save()

    def _cover_to_embed(self) -> bytes | None:
        """Download the Discogs cover if it should be embedded, else None."""
        if not hasattr(self, "image") or not self.config.embed_cover:
            return None
        if self.cover_embedded and not self.config.overwrite_cover:
            return None
        try:
            response = requests.get(self.image, timeout=COVER_TIMEOUT_S)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Could not download cover, skipping it: {e}")
            return None
        return response.content

    def _image_flac(self) -> None:
        cover = self._cover_to_embed()
        if cover:
            audio = FLAC(self.path)
            img = Picture()
            img.type = 3
            img.data = cover
            audio.clear_pictures()
            audio.add_picture(img)
            audio.save()
            self.cover_updated = True

    def _image_mp3(self) -> None:
        cover = self._cover_to_embed()
        if cover:
            # del image
            audio_id3 = ID3(self.path)
            audio_id3.delall("APIC")
            audio_id3.save()

            # update
            audio = MP3(self.path, ID3=ID3)
            audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))
            audio.save()
            self.cover_updated = True

    def search(self, retry: int = 3) -> bool:
        """Search Discogs for this track; return True if a match was found."""
        # check if track has required tags for searching
        if self.search_artist == "" or self.search_title == "":
            logger.error("Track does not have the required tags for searching on Discogs.")
            return False

        logger.info(f'Searching for "{self.search_title} {self.search_artist}" on Discogs...')
        results = []
        for attempt in range(1, retry + 1):
            # discogs api limit: 60/1minute
            time.sleep(0.5)
            try:
                res = self.ds.search(
                    type="master", artist=self.search_artist, track=self.search_title
                )
                # Only the first page: iterating res would fetch every page
                results = res.page(1) if res.count > 0 else []
                break
            except HTTPError:
                if attempt == retry:
                    logger.error(f"Too many API calls, skipping {self}")
                    return False
                logger.error(
                    f"Too many API calls. {retry - attempt} retries left, next retry in 5 sec."
                )
                time.sleep(5)

        if not results:
            logger.warning("Not Found on Discogs.")
            return False

        local_string = f"{self.search_title} {self.search_artist}"
        discogs_strings = []
        for track in results:
            d_artist = ""
            if track.data.get("artist"):
                d_artist = track.data["artist"][0]["name"]

            # create string for comparison
            discogs_strings.append(f"{track.title} {d_artist}")

        # get best match from list
        _, _, best_index = process.extractOne(
            local_string, discogs_strings, scorer=fuzz.WRatio, processor=utils.default_process
        )
        best = results[best_index]

        # check if genre is missing
        if best.genres:
            self.genres = ", ".join(sorted(best.genres))
            self.genres_found = True

        if best.data.get("year"):
            self.year = str(best.data["year"])
            self.year_found = True

        if best.images:
            self.image = best.images[0]["uri"]

        return True


def clean(string: str) -> str:
    """Clean and normalize artist/title strings for better Discogs search matching.

    Removes common variations and formatting that can interfere with finding
    the correct release on Discogs.
    """
    # Remove parenthetical content like "(feat. Artist)", "(Radio Edit)", etc.
    string = re.sub(r"\([^)]*\)", "", string).strip()

    # Take only the first part before commas (common in artist names)
    if "," in string:
        string = string.split(",")[0].strip()

    # Take only the first part before ampersands (collaborations)
    if "&" in string:
        string = string.split("&")[0].strip()

    # Remove specific problematic terms that can interfere with search
    blacklist = ["'", "(Deluxe)"]
    for c in blacklist:
        string = string.replace(c, "")

    return string
