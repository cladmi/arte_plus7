#! /usr/bin/python
# -*- coding:utf-8 -*-
""" arte_plus_7 is a script to help download arte videos

It's only configured for French at the moment.

Usage:

The following commands will return the videos urls found

    # The generic program page
    ./arte_plus_7.py -u http://www.arte.tv/guide/fr/emissions/TRA/tracks
    # The page dedicated to the video
    ./arte_plus_7.py -u http://www.arte.tv/guide/fr/034049-007/karambolage

    # Direct access to some pre-stored programs
    ./arte_plus_7.py -p tracks

To actually download the video, add a '--qualiy <QUAL>' for the one you want
from the list

    # Direct access to some pre-stored programs
    ./arte_plus_7.py -p tracks --quality <MQ|HQ|EQ|SQ'>


Debug:

    # Use the option --keep-artifacts to save intermediate files to help adding
    # features
    ./arte_plus_7.py -u URL --keep-artifacts

"""

from __future__ import print_function

# pylint:disable=locally-disabled,import-error,no-name-in-module
try:
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import HTTPError

import re
import sys
import os.path
from datetime import datetime
import bs4
import json
import subprocess
import argparse
import logging
logging.basicConfig(level=logging.DEBUG)

__version__ = '1.0.1'


def page_read(url):
    """Download the page and return the utf-8 decoded result."""
    logging.debug('Reading %s', url)
    return urlopen(url).read().decode('utf-8')

def page_soup(page):
    """Get the page soup."""
    return bs4.BeautifulSoup(page, 'html.parser')


class Plus7Program(object):
    JSON_URL = ('http://arte.tv/papi/tvguide/videos/stream/player/D/'
                '{0}_PLUS7-D/ALL/ALL.json')

    def __init__(self, video_id):
        json_url = self.JSON_URL.format(self._short_id(video_id))
        try:
            page = page_read(json_url)
        except HTTPError:
            raise ValueError('No JSON for id: %s:%s' % (video_id, json_url))
        _json = json.loads(page)

        player = _json['videoJsonPlayer']

        # Read infos
        self.timestamp = player['videoBroadcastTimestamp'] / 1000.0
        self.date = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d')
        self.name = player['VST']['VNA']
        self.full_name = '{self.name}_{self.date}'.format(self=self)
        self.urls = self._extract_videos(player['VSR'])

    def infos(self, values=('date', 'name', 'full_name', 'urls')):
        values = set(values)
        ret = {p: v for p, v in self.__dict__.items() if p in values}
        return ret

    def download(self, quality, directory=None):
        """Download the video."""

        url = self.urls[quality]
        directory = directory or '.'

        dl_name = '{name}_{quality}.mp4'
        dl_name = dl_name.format(name=self.full_name, quality=quality)
        dl_name = os.path.join(directory, dl_name)

        cmd = ['wget', '--continue', '-O', dl_name, url]
        logging.info(' '.join(cmd))
        subprocess.call(cmd)

    @staticmethod
    def _extract_videos(vsr, media='mp4', lang='FR'):
        videos = {}
        for video in vsr.values():
            if video['mediaType'] != media:
                continue
            if video['versionShortLibelle'] != lang:
                continue
            videos[video['VQU']] = video['url']
        return videos

    @staticmethod
    def _short_id(video_id):
        """Return short id used for jon entry.

        >>> Plus7Program._short_id('058941-007-A')
        '058941-007'
        """
        return '-'.join(video_id.split('-')[0:2])

    @classmethod
    def by_url(cls, url):
        video_id = cls._id_from_url(url)
        return Plus7Program(video_id)

    @staticmethod
    def _id_from_url(url):
        """Extract video id from url.

        >>> Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/de/055969-002-A/tracks?autoplay=1')
        '055969-002-A'

        >>> Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/fr/055900-002-A/trop-xx?autoplay=1')
        '055900-002-A'

        >>> Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/fr/058941-008/tracks')
        '058941-008'
        """
        url = re.sub('\?.*', '', url)
        video_id = url.split('/')[-2]
        return video_id


class ArtePlus7(object):
    """ ArtePlus7 helps getting arte videos link and download them """
    PROGRAMS_JSON_URL = 'http://www.arte.tv/guide/fr/plus7.json'
    PROGRAMS = {
        'tracks': 'Tracks',
        'karambolage': 'Karambolage',
        'xenius': 'X:enius',
    }
    PROGRAMS_SEARCH = 'http://www.arte.tv/guide/fr/search?scope=plus7&q={0}'


    def __init__(self):
        pass

    @classmethod
    def search(cls, search_str):
        logging.info('Searching %s', search_str)
        url = cls.PROGRAMS_SEARCH.format(search_str)
        soup = page_soup(page_read(url))
        tag = soup.find(cls._search_results)

        program_dict = cls._extract_program_dict(tag.text)
        programs = []
        for program in program_dict['programs']:
            try:
                prog = Plus7Program(program['id'])
            except ValueError:
                pass  # Ignore 'previews'
            else:
                programs.append(prog)

        programs.sort(key=lambda p:p.timestamp, reverse=True)

        return programs

    @staticmethod
    def _search_results(tag):
        """ Tells in this tag is the requested json url file """
        # Script matching
        script_re = re.compile(r"require\('js/page/search'\)\(")

        keep = True
        keep = keep and tag.get('type', None) == 'text/javascript'
        keep = keep and bool(script_re.match(tag.text.strip()))

        return keep

    @staticmethod
    def _extract_program_dict(text):
        for line in text.splitlines():
            if re.search('results:', line):
                break
        else:
            raise ValueError("'results:' not in text:\n%s" % text)

        line = re.sub(r'^\s*results: ', '', line)
        line = re.sub(r',$', '', line)

        program_dict = json.loads(line)
        return json.loads(line)


    @staticmethod
    def parser():
        """ arte_plus_7 parser """
        parser = argparse.ArgumentParser(
            description=u'ArtePlus7 videos download')
        vid_parser = parser.add_mutually_exclusive_group(required=True)
        vid_parser.add_argument('-u', '--url',
                                help=u'Arte page to download video from')
        vid_parser.add_argument('-p', '--program',
                                choices=ArtePlus7.PROGRAMS.keys(),
                                help=u'Download given program')

        parser.add_argument('-q', '--quality',
                            choices=(u'MQ', u'HQ', u'EQ', u'SQ'),
                            help=u'Video quality to download')
        parser.add_argument('--keep-artifacts', action='store_true',
                            default=False,
                            help=u'Keep intermediate files artifacts')

        parser.add_argument('-d', '--download-directory', default='.',
                            help=u'Directory where to save file')
        return parser


def main():
    """ arte_plus_7 main function """
    opts = ArtePlus7.parser().parse_args()

    if opts.url:
        program = Plus7Program.by_url(opts.url)
    elif opts.program:

        programs = ArtePlus7.search(ArtePlus7.PROGRAMS[opts.program])
        if not programs:
            logging.error('No videos found for program: %s', search_str)
            exit(1)
        elif len(programs) > 1:
            logging.info('Found multiple videos, using the last one')

    for program in (programs[0],):
    # for program in programs:
        if opts.quality is not None:
            program.download(opts.quality, opts.download_directory)
        else:
            print(json.dumps(program.infos(), indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
