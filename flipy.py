#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pip install flickrapi requests gevent

import logging, os
import flickrapi
from requests import async
import xml.etree.ElementTree as ElementTree
from optparse import OptionParser

API_KEY = 'get yours' #http://www.flickr.com/services/apps/create/apply
API_SECRET = 'please'
UPLOADED_EXTS = ['jpg', 'jpeg', 'tif', 'raw', 'png', 'gif']

logger = logging.getLogger('flipy')
logger.setLevel(logging.INFO)

def pre_req(request):
    logger.info(u'Uploading %s' % request.files['photo'].name)


def resp(response):
    if response.error:
        logger.error(response.error)
    else:
        rsp = ElementTree.fromstring(response.text)
        if rsp.attrib['stat'] == 'ok':
            logger.info(u'%s upload OK' % response.request.files['photo'].name)
        else:
            err = rsp.find('err')
            logger.error(u'Error: %(code)s: %(msg)s' % err.attrib)
    return response

usage = '%s --help' % __file__
parser = OptionParser(usage)
parser.add_option('-d', '--dir', action='store', dest='dir', default=os.getcwd(), help='src directory')
parser.add_option('-t', '--tags', action='store', dest='tags', default='', help='tags')
parser.add_option('-p', '--public', action='store_true', dest='public', default=False, help='as public')
parser.add_option('-c', '--concurrency', action='store', dest='concurrency', default=10,
    help='max simultaneous uploads')
(options, args) = parser.parse_args()

flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
(token, frob) = flickr.get_token_part_one(perms='write')
if not token:
    raw_input("Wait for browser to be spawned, accept permissions and hit ENTER to continue\n")
flickr.get_token_part_two((token, frob))

data = {'auth_token': flickr.token_cache.token, 'api_key': flickr.api_key, 'tags': options.tags,
        'is_public': str(int(options.public))}
data['api_sig'] = flickr.sign(data)

dir = os.path.expandvars(options.dir)
files = [one for one in os.listdir(dir) if
         os.path.isfile(os.path.join(dir, one)) and one.split('.')[-1].lower() in UPLOADED_EXTS]

hooks = dict(response=resp, pre_request=pre_req)
requests = [async.post('http://api.flickr.com/%s' % flickr.flickr_upload_form, data=data,
    files={'photo': open(one, 'rb')}, hooks=hooks)
            for one in files]

async.map(requests, size=int(options.concurrency))