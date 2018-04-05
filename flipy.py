#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import io
import webbrowser

import workerpool
import flickrapi

from settings import API_KEY, API_SECRET

EXT_UPLOAD = ('jpg', 'jpeg', 'tif', 'tiff', 'raw', 'png', 'gif')
BYTES_IN_MB = 1048576
MAX_SIZE = 20 * BYTES_IN_MB


def auth(flickr):
    print('You need to verify your API tokens. Spawning browser, please pay attention...')
    flickr.get_request_token(oauth_callback='oob')

    authorize_url = flickr.auth_url(perms='write')
    webbrowser.open_new_tab(authorize_url)

    verifier = str(input('Verifier code: '))
    flickr.get_access_token(verifier)


def upload(fpath, is_public=False, tags=''):
    print('[*] uploading %s' % fpath)
    try:
        rsp = flickr.upload(fpath, is_public=int(is_public), tags=tags)
        if rsp.attrib['stat'] == 'ok':
            print(u'[+] %s uploaded' % fpath)
            uploaded.write(u'%s\n' % os.path.basename(fpath))
        else:
            err = rsp.find('err')
            print(u'[!] %(file)s %(code)s: %(msg)s' % dict(err.attrib, **{'file': fpath}))

        return rsp
    except Exception as e:
        print('[!] %s' % e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FliPy a simple Flickr CLI uploader')
    parser.add_argument('-d', '--dir', dest='src_dir', default=os.getcwd(), help='directory to upload')
    parser.add_argument('-t', '--tags', dest='tags', default='', help='tags (comma seperated)')
    parser.add_argument('-p', '--public', action='store_true', default=False, help='upload as public')
    parser.add_argument('-c', '--concurrency', type=int, default=9, help='max simultaneous uploads')
    args = parser.parse_args()

    src_dir = os.path.expandvars(args.src_dir)
    log_file, uploaded_already = os.path.join(src_dir, '.uploaded'), []

    if os.path.exists(log_file):
        with io.open(log_file, 'r') as f:
            uploaded_already = f.read().splitlines()

    with io.open(log_file, 'a+') as uploaded:
        files = []
        for one in sorted(os.listdir(src_dir)):
            fpath = os.path.join(src_dir, one)
            _, ext = os.path.splitext(fpath)
            ext = ext.lower()[1:] if ext else ''
            size = os.path.getsize(fpath)

            if all([one not in uploaded_already, os.path.isfile(fpath), ext in EXT_UPLOAD, size < MAX_SIZE]):
                files.append((fpath, size))

        if not files:
            sys.exit('[!] No suitable files found in "%s".' % src_dir)
        print('[-] Found %d files (%f MB)' % (len(files), sum(one[1] for one in files) / BYTES_IN_MB))

        pool = workerpool.WorkerPool(size=args.concurrency)
        flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
        if not flickr.token_valid(perms='write'):
            auth()

        pool.map(upload, [fpath for fpath, size in files],
                 [args.public]*len(files), [args.tags]*len(files))

        pool.shutdown()
        pool.wait()
