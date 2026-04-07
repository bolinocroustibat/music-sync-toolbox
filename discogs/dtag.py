import json
import re
import time
from pathlib import Path

import niquests as requests
from discogs_client.exceptions import HTTPError
from fuzzywuzzy import process
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, FLACNoHeaderError, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError
from mutagen._util import MutagenError

from local_files.logger import logger
from local_files.music_file import MusicFile


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

        # Clean title and artist tags
        self.artist: str = clean(string=self.artist)
        self.title: str = clean(string=self.title)

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
        if self.suffix == ".flac":
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

        elif self.suffix == ".mp3":
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

        elif self.suffix == ".m4a":
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

        if self.suffix == ".flac":
            self._image_flac()
            audio = FLAC(self.path)
        elif self.suffix == ".mp3":
            self._image_mp3()
            audio = EasyID3(self.path)
        elif self.suffix == ".m4a":
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
        if hasattr(self, "image") and self.config.embed_cover:
            if self.config.overwrite_cover:
                audio["covr"] = [
                    MP4Cover(
                        requests.get(self.image).content,
                        imageformat=MP4Cover.FORMAT_JPEG,
                    )
                ]
                self.cover_updated = True
        audio.save()

    def _image_flac(self) -> None:
        if hasattr(self, "image") and self.config.embed_cover:
            audio = FLAC(self.path)
            img = Picture()
            img.type = 3
            img.data = requests.get(self.image).content
            if self.config.overwrite_cover:
                audio.clear_pictures()
                audio.add_picture(img)
                self.cover_updated = True
            else:
                if self.cover_embedded is False:
                    audio.clear_pictures()
                    audio.add_picture(img)
                    self.cover_updated = True
            audio.save()

    def _image_mp3(self) -> None:
        def _update_image(path: Path, data: bytes) -> None:
            # del image
            audio_id3 = ID3(path)
            audio_id3.delall("APIC")
            audio_id3.save()

            # update
            audio = MP3(self.path, ID3=ID3)
            audio.tags.add(
                APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=data)
            )
            audio.save()

        # check if image was found
        if hasattr(self, "image") and self.config.embed_cover:
            if self.config.overwrite_cover:
                _update_image(self.path, requests.get(self.image).content)
                self.cover_updated = True
            else:
                if self.cover_embedded is False:
                    _update_image(self.path, requests.get(self.image).content)
                    self.cover_updated = True

    def search(self, retry: int = 3) -> bool | None:
        retry -= 1
        # check if track has required tags for searching
        if self.artist == "" and self.title == "":
            logger.error(
                "Track does not have the required tags for searching on Discogs."
            )
            return False

        logger.info(f'Searching for "{self.title} {self.artist}" on Discogs...')
        # discogs api limit: 60/1minute
        # retry option added
        time.sleep(0.5)
        try:
            # Use original code without timeout modification
            res = self.ds.search(type="master", artist=self.artist, track=self.title)

            local_string = f"{self.title} {self.artist}"
            discogs_list = []
            if res.count > 0:
                for i, track in enumerate(res):
                    d_artist = ""
                    if track.data.get("artist"):
                        d_artist = d_artist["artist"][0]["name"]
                    d_title = track.title

                    # create string for comparison
                    discogs_string = f"{d_title} {d_artist}"

                    # append to list
                    discogs_list.append({"index": i, "str": discogs_string})

                # get best match from list
                best_one = process.extractBests(local_string, discogs_list, limit=1)[0][
                    0
                ]["index"]

                # check if genre is missing
                if res[best_one].genres:
                    genres = ", ".join(sorted([x for x in res[best_one].genres]))
                    self.genres = genres
                    self.genres_found = True

                if res[best_one].data["year"]:
                    year = res[best_one].data["year"]
                    self.year = str(year)
                    self.year_found = True

                if res[best_one].images:
                    self.image = res[best_one].images[0]["uri"]
            else:
                logger.warning("Not Found on Discogs.")
                return False
        except HTTPError:
            if retry == 0:
                logger.error(f"Too many API calls, skipping {self}")
                return False
            logger.error(
                f"Too many API calls. {retry} retries left, next retry in 5 sec."
            )
            time.sleep(5)
            self.search(retry=retry)


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
