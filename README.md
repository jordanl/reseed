# reseed

A tool for seeding torrents across gazelle trackers,
such as migrating from What to PTH
or cross-seeding between PTH and APL.

When given a local directory full of torrents and a tracker,
it will try to find a match for each torrent on the tracker.
If a match is found, it downloads corresponding .torrent file
and re-adds it to your torrent client for reseeding.

If the uploader has changed the filenames on the new tracker;
e.g. if your torrent has
`Foo For Bar.flac` but the tracker is looking for
`Foo for Bar.flac`, this tool will handle that.

## Migration

Migration mode is used when moving content over from one tracker to another,
e.g. from What to PTH.

In this mode,
the torrent is moved to the new tracker directory
and its files are renamed to match any spelling changes in the new torrent.

**NB:**  This code is a work in progress and only migration mode is working

## Cross-seeding

Cross-seeding is used when sharing content between trackers,
such as sharing between PTH and APL.

In this mode, the original torrent is left untouched.
Symlinks are added to the new tracker directory.
This way spelling changes can be handled without duplicating files.

## Examples

FIXME
