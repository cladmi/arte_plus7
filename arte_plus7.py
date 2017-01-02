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

"""

from __future__ import print_function

import re
import os.path
import json
import subprocess
import argparse
import logging
from datetime import datetime

# pylint:disable=locally-disabled,import-error,no-name-in-module
try:
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import HTTPError

import bs4
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())

__version__ = '2.2.3'


def page_read(url):
    """Download the page and return the utf-8 decoded result."""
    LOGGER.debug('Reading %s', url)
    return urlopen(url).read().decode('utf-8')


def page_soup(page):
    """Get the page soup."""
    return bs4.BeautifulSoup(page, 'html.parser')


class Plus7Program(object):
    """Describes an ArtePlus7 video.

    :param video_id: video unique id
    """
    JSON_URL = ('http://arte.tv/papi/tvguide/videos/stream/player/D/'
                '{0}_PLUS7-D/ALL/ALL.json')

    def __init__(self, video_id):
        json_url = self.JSON_URL.format(self._short_id(video_id))
        debug_id = '%s:%s' % (video_id, json_url)
        try:
            page = page_read(json_url)
        except HTTPError:
            raise ValueError('No JSON for id: %s' % debug_id)
        _json = json.loads(page)

        player = _json['videoJsonPlayer']

        if player.get('custom_msg', {}).get('type', None) == 'error':
            raise ValueError("Error: '%s': %s" % (player['custom_msg']['msg'],
                                                  debug_id))

        # Read infos
        try:
            self.timestamp = player['videoBroadcastTimestamp'] / 1000.0
            self.date = self._date_from_timestamp(self.timestamp)
            self.name = player['VST']['VNA']
            self.full_name = '{self.name}_{self.date}'.format(self=self)
            self.urls = self._extract_videos(player['VSR'])
        except KeyError as err:
            raise ValueError('Incomplete JSON for id: %s: %s' %
                             (err, debug_id))

    @staticmethod
    def _date_from_timestamp(timestamp, fmt='%Y-%m-%d'):
        """Format timestamp to date string."""
        return datetime.fromtimestamp(timestamp).strftime(fmt)

    def infos(self, values=('date', 'name', 'full_name', 'urls')):
        """Return a dict describing the object."""
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
        LOGGER.info(' '.join(cmd))
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
        """Return Plus7Program for given `url`."""
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
        url = re.sub(r'\?.*', '', url)
        video_id = url.split('/')[-2]
        return video_id


class ArtePlus7(object):
    """ArtePlus7 helps using arte website."""
    PROGRAMS_JSON_URL = 'http://www.arte.tv/guide/fr/plus7.json'
    PROGRAMS = {
        'tracks': 'Tracks',
        'karambolage': 'Karambolage',
        'xenius': 'X:enius',
    }
    PROGRAMS_SEARCH = 'http://www.arte.tv/guide/fr/search?scope=plus7&q={0}'

    @classmethod
    def search(cls, search_str):
        """Search program with given `search_str`.

        It will be passed directly as a search query string
        """
        LOGGER.info('Searching %s', search_str)
        url = cls.PROGRAMS_SEARCH.format(search_str)
        page = page_read(url)

        program_dict = cls._programs_dict_from_page(page)

        programs = []
        for program in program_dict['programs']:
            try:
                prog = Plus7Program(program['id'])
            except ValueError as err:
                # Ignore 'previews' or 'outdated'
                LOGGER.debug('Error while reading program: %r', err)
            else:
                programs.append(prog)

        programs.sort(key=lambda p: p.timestamp, reverse=True)

        return programs

    @classmethod
    def program(cls, program):
        """Search program and select only results that are named 'program'."""
        search_str = ArtePlus7.PROGRAMS[program]
        all_programs = cls.search(search_str)
        programs = [p for p in all_programs if p.name == program]
        return programs

    @staticmethod
    def _programs_dict_from_page(page):
        """Return programs dict from page.

        Programs dict is stored as a JSON in attribute 'data-results'
        from id='search-container' div.

            <div
            id="search-container"
            data-results="{...PROGRAMS_DICT_JSON...}"

        """
        soup = page_soup(page)
        tag = soup.find(id='search-container')
        programs = json.loads(tag.attrs['data-results'])

        return programs


def parser():
    """ arte_plus_7 parser """
    _parser = argparse.ArgumentParser(
        description=u'ArtePlus7 videos download')
    _parser.add_argument('-v', '--verbose', action='store_true', default=False)
    _parser.add_argument('--version', action='version',
                         version='%(prog)s {0}'.format(__version__))

    vid_parser = _parser.add_mutually_exclusive_group(required=True)
    vid_parser.add_argument('-u', '--url',
                            help=u'Arte page to download video from')
    vid_parser.add_argument('-p', '--program',
                            choices=ArtePlus7.PROGRAMS.keys(),
                            help=u'Download given program')
    vid_parser.add_argument('-s', '--search', help=u'Search programs')

    _parser.add_argument(
        '-n', '--num-programs', type=int, default=1,
        help=u'Specify number of programs to download (-1 for all).')

    _parser.add_argument('-q', '--quality',
                         choices=(u'MQ', u'HQ', u'EQ', u'SQ'),
                         help=u'Video quality to download')

    _parser.add_argument('-d', '--download-directory', default='.',
                         help=u'Directory where to save file')
    return _parser


def main():
    """ arte_plus_7 main function """
    opts = parser().parse_args()
    if opts.verbose:
        LOGGER.setLevel(logging.DEBUG)

    # Get programs
    if opts.url:
        programs = [Plus7Program.by_url(opts.url)]
    elif opts.program:
        programs = ArtePlus7.program(opts.program)
    elif opts.search:
        programs = ArtePlus7.search(opts.search)
    else:
        raise ValueError('Invalid option, should be url, program or search')

    # Nothing found
    if not programs:
        LOGGER.error('Error: No videos found')
        exit(1)

    num_progs = len(programs) if opts.num_programs == -1 else opts.num_programs

    LOGGER.info('Found %d videos, using %d', len(programs), num_progs)
    programs = programs[0:num_progs]

    # Iterate over programs selection
    for program in programs:
        if opts.quality is not None:
            program.download(opts.quality, opts.download_directory)
        else:
            print(json.dumps(program.infos(), indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
