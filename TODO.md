The code is a quick hack, still lots that can be done.

 * no way to switch from 'migrate' to 'cross-seed' mode
 * currently only handles flacs -- need to handle mp3s in reseed.py build_search_queries()
 * sort candidates based on how close candidate size is to local torrent size
 * VA torrents generate way too many search queries
 * need code cleanup / better comments
 * code is completely untestable right now
 * in migrate mode, maybe mv torrents with no match into an 'unmatched' folder so they're not retested in the next run
