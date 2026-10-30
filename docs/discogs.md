# Discogs tag updater

Writes the genres and the original release year from the Discogs master release to your MP3, FLAC and M4A files, in batch.
It also embeds the cover art. Tracks need their artist and title tags set to be searched.

## Why?

Genres on downloaded tracks are often far too broad: a track tagged "Electronic" or "Dance" is actually Dubstep.

The year is often wrong too. A track taken from a "Best Of The 90's" compilation released in 2018 shows 2018, although it was made in the 90's.

## Why Discogs genres?

They are curated by contributors who discuss and agree on the right genres and styles for each release. See the Discogs guidelines:

- [Database Guidelines 9: Genres / Styles](https://support.discogs.com/hc/en-us/articles/360005055213-Database-Guidelines-9-Genres-Styles)
- [Quick Start Guide for New Contributors](https://support.discogs.com/hc/en-us/articles/360004051893-Quick-Start-Guide-For-New-Contributors)

## Why the original year?

It comes from the master release, i.e. when the track officially appeared for the very first time.
Your collection then shows a consistent timeline of tracks with their 70's, 80's, 90's or 00's "vibe".

## Limitations

- The Discogs API allows at most 60 calls per minute.
- Discogs serves images up to 600x600px ([details](https://support.discogs.com/hc/en-us/articles/360005006874-Database-Guidelines-13-Images#Size_And_Quality)).

## Results comparison

Before and after running the Discogs tag updater: [Google spreadsheet](https://docs.google.com/spreadsheets/d/1Y76JXhYQpOmZuy36jalYsfad_uidKWCUCktGb_ymxJs/edit?usp=sharing).
