#!/usr/bin/env python3

import argparse
import configparser
import gazelle
import html
import os
import re
import subprocess
import string
import sys
import tempfile

# WARNING untested
cross_seeding = False

dry_run = False

##
##
##


def find_all(dir):
    return [f for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]


def find_flac_torrents(torrents_dir):
    o = []
    for folder in find_all(torrents_dir):
        if folder.lower().find('flac') != -1:
            o.append(folder)
    return o

##
##
##


def sanitize_tag(tag):
    tag = ' '.join(tag.split())  # fold whitespace
    tag = re.sub(r'\(.*?\)', '', tag)  # remove (parentheticals)
    tag = re.sub(r'\[.*?\]', '', tag)  # remove [brace comments]
    return tag


def get_metaflac_tag(path, tag):
    key = subprocess.check_output(['metaflac', '--show-tag='+tag, path])
    key = key.decode('utf-8')
    pos = key.find('=')
    if pos != -1:
        key = key[pos+1:]
    return sanitize_tag(key)


def build_search_queries(path):
    queries = []
    query_strs = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith('.flac'):
                path = os.path.join(root, name)
                album = get_metaflac_tag(path, 'ALBUM')
                artist = get_metaflac_tag(path, 'ARTIST')
                if album and artist:
                    query = {'searchstr': album, 'artistname': artist}
                    query_str = str(query)
                    if query_str not in query_strs:
                        queries.append(query)
                        query_strs.append(query_str)
            elif name.endswith('.mp3'):
                # TODO:
                pass

    return queries

##
##
##


def file_size_is_close(n1, n2):
    diff = abs(n1-n2)
    if not n1 or not n2:
        return n1 == n2
    percent_diff = diff / min(n1, n2)
    print('n1==%s, n2==%s' % (n1, n2))
    return percent_diff < 0.05


def get_prefix_and_suffix(s):
    suffix = None
    pos = s.rfind('.')
    if pos != -1:
        suffix = s[pos+1:].lower()
    prefix = None
    pos = 0
    while s[pos].isdigit():
        pos += 1
    prefix = s[0:pos].lower()
    return prefix, suffix


def find_matching_file(path, fname, fsize):

    # look for an easy match first
    candidate = os.path.join(path, fname)
    if os.path.isfile(candidate):
        s = os.path.getsize(candidate)
        if s == fsize:
            print('perfect match: ' + fname)
            return fname

        # maybe someone tweaked the metainfo.
        # see if the torrent size is close
        # if file_size_is_close(s, fsize):
        #    print('near match: ' + fname)
        #    return fname

    candidates = []
    for root, dirs, files in os.walk(path):
        for name in files:
            prefix, suffix = get_prefix_and_suffix(name)
            full = os.path.join(root, name)
            size = os.path.getsize(full)
            rel = os.path.relpath(full, path)
            candidates.append([prefix, suffix, rel, size])

    # next look & see if someone renamed the file
    for candidate in candidates:
        if fsize == candidate[3]:
            print('filesize match: ' + candidate[2])
            return candidate[2]

    # maybe they renamed it /and/ edited the metainfo.
    # look for a file that begins with the same number
    # ends with the same suffix
    # differs by <5%
    # prefix, suffix = get_prefix_and_suffix(fname)
    # for candidate in candidates:
    #     print("prefix==%s suffix==%s fname==%s candidate==[%s] fsize==%s"
    #           % (prefix, suffix, fname, candidate, fsize))
    #     if prefix==candidate[0] and suffix==candidate[1]:
    #         if file_size_is_close(candidate[3], fsize):
    #             print('prefix, suffix match: ' + candidate[2])
    #             return candidate[2]

    # print('seeking %s (%s)' % (fname, fsize))
    # for candidate in candidates:
    #     print(candidate)
    # print('no match.')
    return None


def is_match(torrent_path, filepath, filelist):
    filemap = {}
    for fname in filelist:
        fsize = filelist[fname]
        match = find_matching_file(torrent_path, fname, fsize)
        if match:
            filemap[fname] = match
        elif not fname.endswith('.flac') and not fname.endswith('.mp3'):
            pass  # missing supporting files are ok
        else:
            print('discarding candidate "%s" because we have no match for "%s"'
                  % (filepath, fname))
            return False, {}
    return True, filemap

##
##
##


def mv(src, tgt):
    print('$ mv "%s" "%s"' % (src, tgt))
    if not dry_run:
        dirname = os.path.dirname(tgt)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        os.rename(src, tgt)


def move_torrent(src, tgt, filemap):
    # move the torrent folder over
    mv(src, tgt)
    # if the user's renamed any files, update them too
    for key in filemap:
        if key != filemap[key]:
            fin = os.path.join(tgt, filemap[key])
            fout = os.path.join(tgt, key)
            mv(fin, fout)


def link(src, tgt):
    print('$ ln -s "%s" "%s"' % (src, tgt))
    if not dry_run:
        dirname = os.path.dirname(tgt)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        os.symlink(src, tgt)


def link_torrent(src, tgt, filemap):

    no_changes = True
    for key in filemap:
        if key != filemap[key]:
            no_changes = False
            break

    if no_changes:
        # everything's the same, one symlink is enough
        link(src, tgt)
    else:
        # symlink each file into a new folder
        os.makedirs(tgt)
        for key in filemap:
            fin = os.path.join(src, filemap[key])
            fout = os.path.join(tgt, key)
            link(fin, fout)


def add_torrent_from_id(id, api, add_cmd):
    torrent_file = api.snatch_torrent(id)
    fd, fname = tempfile.mkstemp()
    os.write(fd, torrent_file)
    os.close(fd)
    cmd = add_cmd.format(torrent=fname)
    print('$ ' + cmd)
    if not dry_run:
        os.system(cmd)
    os.remove(fname)

##
##
##


# returns a map of filename -> filesize
def parse_filelist(str):
    filelist = {}
    for f in str.split('|||'):
        pos = f.rfind('{{{')
        fname = f[0:pos]
        fname = html.unescape(fname)
        f = f[pos+3:]
        pos = f.rfind('}}}')
        fsize = int(f[:pos])
        filelist[fname] = fsize
    return filelist


def find_match(torrent_path, api):

    print(torrent_path)

    for query in build_search_queries(torrent_path):
        print(query)
        reply = api.request('browse', **query)
        for result in reply.get('results', {}):
            # FIXME: sort candidates by size closeness
            for candidate in result.get('torrents', []):
                torrent = api.request('torrent', id=candidate['torrentId'])
                if torrent:
                    t = torrent['torrent']
                    filepath = html.unescape(t['filePath'])
                    files = parse_filelist(t['fileList'])
                    match, filemap = is_match(torrent_path,
                                              filepath, files)
                    if match:
                        torrentid = t['id']
                        return match, torrentid, filepath, filemap

    return False, '', '', {}


def process_torrent(torrent_path, api, tracker_root, action_func, add_cmd):
    match, torrentid, filepath, filemap = find_match(torrent_path, api)
    if match:
        src = torrent_path
        tgt = os.path.join(tracker_root, filepath)
        action_func(src, tgt, filemap)
        add_torrent_from_id(torrentid, api, add_cmd)


##
##
##


def build_default_config(config, filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    section = 'source'
    config.add_section(section)
    config.set(section, 'path', '/path/to/old/torrents')

    section = 'target'
    config.add_section(section)
    config.set(section, 'path', '/where/to/put/new/torrents')
    config.set(section, 'url', 'https://passtheheadphones.me/')
    config.set(section, 'username', '')
    config.set(section, 'password', '')

    section = 'user-agent'
    config.add_section(section)
    config.set(section, 'add', 'transmission-remote --add "$torrent" --start-paused --download-dir "$dir"')

    config.write(open(filename, 'w'))
    print('Please edit the configuration file "%s"' % filename)


def main():

    # command-line parsing
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='reseed')
    parser.add_argument(
        '--config',
        help='the location of the configuration file',
        default=os.path.expanduser('~/.reseed/config'))
    args = parser.parse_args()

    # read the config file
    config = configparser.SafeConfigParser()
    try:
        config.readfp(open(args.config))
        section = 'source'
        torrent_root = config.get(section, 'path')

        section = 'target'
        tracker_root = config.get(section, 'path')
        username = config.get(section, 'username')
        password = config.get(section, 'password')
        url = config.get(section, 'url')

        section = 'user-agent'
        add_cmd = config.get(section, 'add')
        add_cmd = string.Template(add_cmd).safe_substitute({'dir': tracker_root})
    except:
        build_default_config(config, args.config)
        sys.exit(2)

    if cross_seeding:
        action_func = link_torrent
    else:
        action_func = move_torrent

    print('logging in')
    api = gazelle.Gazelle(url, username, password)

    print('looking for torrents in %s' % torrent_root)
    folders = find_flac_torrents(torrent_root)
    for f in folders:
        torrent_path = os.path.join(torrent_root, f)
        process_torrent(torrent_path, api, tracker_root, action_func, add_cmd)

    api.logout()


if __name__ == '__main__':
    main()
