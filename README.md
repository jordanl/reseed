# reseed

A tool for seeding torrents across gazelle trackers, such as
migrating from What to PTH or cross-seeding between PTH and APL.

When given a tracker and a local directory full of torrents,
it will look for a tracker match for each torrent.
If a match is found,
it re-adds it to your torrent client for reseeding on the new tracker.

It handles renamed files and folders,
e.g. if the uploader added edition information to the folder
or renamed "Foo For Bar.flac" as "Foo for Bar.flac".

# Migration

Migration mode is used when moving content over from one tracker to another,
e.g. from What to PTH.

In this mode,
the torrent is moved to the new tracker directory
and its files are renamed to match any spelling changes in the new torrent.

# Cross-seeding

Cross-seeding is used when sharing content between trackers,
such as sharing between PTH and APL.

In this mode, the original torrent is left untouched.
Symlinks are added to the new tracker directory.
This way spelling changes can be handled without duplicating files.

# Examples

FIXME
