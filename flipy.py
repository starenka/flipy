#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pip install flickrapi requests gevent

from __future__ import division
import logging, os, sys
from optparse import OptionParser
import xml.etree.ElementTree as ElementTree

import flickrapi
from requests import async

API_KEY = 'get yours' #http://www.flickr.com/services/apps/create/apply
API_SECRET = 'please'
EXT_UPLOAD = ('jpg', 'jpeg', 'tif', 'tiff', 'raw', 'png', 'gif')
BYTES_IN_MB = 1048576
MAX_SIZE = 20 * BYTES_IN_MB

logger = logging.getLogger('flipy')
logger.setLevel(logging.INFO)

def pre_req(request):
    logger.info(u'[-] uploading %s' % request.files['photo'].name)


def resp(response):
    global uploaded
    if response.error:
        logger.error(
            u'[!] %(file)s %(error)s' % {'error': response.error, 'file': response.request.files['photo'].name})
    else:
        rsp = ElementTree.fromstring(response.text)
        if rsp.attrib['stat'] == 'ok':
            file = response.request.files['photo'].name
            logger.info(u'[+] %s uploaded' % file)
            uploaded.write(u'%s\n' % file)
        else:
            err = rsp.find('err')
            logger.error(u'[!] %(code)s: %(msg)s' % err.attrib)
    return response

usage = '%s --help' % __file__
parser = OptionParser(usage)
parser.add_option('-d', '--dir', action='store', dest='dir', default=os.getcwd(), help='src directory')
parser.add_option('-t', '--tags', action='store', dest='tags', default='', help='tags')
parser.add_option('-p', '--public', action='store_true', dest='public', default=False, help='as public')
parser.add_option('-o', '--timeout', action='store', dest='timeout', default=120, help='timeout for file upload')
parser.add_option('-c', '--concurrency', action='store', dest='concurrency', default=15,
    help='max simultaneous uploads')
(options, args) = parser.parse_args()

dir = os.path.expandvars(options.dir)
log_file = os.path.join(dir, '.uploaded')
if not os.path.exists(log_file):
    open(log_file, 'w').close()
with open(log_file, 'r') as f:
    uploaded_already =  [one.strip() for one in f.readlines()]
uploaded = open(log_file, 'a+')

files = []
for one in sorted(os.listdir(dir)):
    full = os.path.join(dir, one)
    ext, size = one.split('.')[-1].lower(), os.path.getsize(full)
    if all([full not in uploaded_already, os.path.isfile(full), ext in EXT_UPLOAD, size < MAX_SIZE]):
        files.append((full.decode('utf8'), size))
    else:
        logging.warning('[@] Skipping file: %s' % full)

if not files:
    sys.exit('[!] No suitable files found in "%s".' % dir)
logger.info('[-] Uploading %d files (%f MB)' % (len(files), sum(one[1] for one in files) / BYTES_IN_MB))

flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
(token, frob) = flickr.get_token_part_one(perms='write')
if not token:
    raw_input("Wait for browser to be spawned, accept permissions and hit ENTER to continue\n")
flickr.get_token_part_two((token, frob))

data = {'auth_token': flickr.token_cache.token, 'api_key': flickr.api_key, 'tags': options.tags,
        'is_public': str(int(options.public))}
data['api_sig'] = flickr.sign(data)

hooks = dict(response=resp, pre_request=pre_req)
requests = [async.post('http://api.flickr.com/%s' % flickr.flickr_upload_form, data=data,
    files={'photo': open(one[0], 'rb')}, timeout=int(options.timeout), hooks=hooks)
            for one in files]

async.map(requests, size=int(options.concurrency))
uploaded.close()