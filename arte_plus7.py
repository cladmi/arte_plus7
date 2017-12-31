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

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *  # pylint:disable=W0401,W0614,W0622
# pylint:disable=missing-super-argument

import re
import os.path
import json
import subprocess
import argparse
import logging
from datetime import datetime

# pylint:disable=locally-disabled,import-error,no-name-in-module
# pylint:disable=ungrouped-imports
try:
    from collections.abc import Mapping
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from collections import Mapping
    from urllib2 import urlopen
    from urllib2 import HTTPError

import bs4
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())

__version__ = '3.0.0.dev0'


def page_read(url):
    """Download the page and return the utf-8 decoded result."""
    LOGGER.debug('Reading %s', url)
    return urlopen(url).read().decode('utf-8')


def page_soup(page):
    """Get the page soup."""
    return bs4.BeautifulSoup(page, 'html.parser')


def download(url, name, directory=None):
    """Download given url to file `name`.

    If `directory` is set, download to given directory.
    """

    directory = directory or ''
    dest = os.path.join(directory, name)

    cmd = ['wget', '--continue', '-O', dest, url]
    LOGGER.info(' '.join(cmd))
    return subprocess.call(cmd)


class VideoUrl(str, object):
    """One video url, behaves like a str."""
    NAME_FORMAT = '{name}_{date}_{lang}_{quality}.mp4'

    def __new__(cls, url, *args, **kwargs):  # pylint:disable=unused-argument
        # explicitly only pass url to the str constructor
        return super().__new__(cls, url)

    def __init__(self, url, program, lang, quality):
        # Should work with both python2 and python3
        str.__init__(url)
        super().__init__()

        self.program = program
        self.lang = lang
        self.quality = quality

    @property
    def full_name(self):
        """Video full name from NAME_FORMAT."""
        return self.NAME_FORMAT.format(
            name=self.program.name, date=self.program.date,
            lang=self.lang, quality=self.quality)

    @classmethod
    def from_json_dict(cls, program, vjson):
        """Create video from result JSON dict."""
        url = vjson['url']
        lang = vjson['versionShortLibelle']
        quality = vjson.get('VQU', vjson.get('quality'))
        return cls(url, program, lang, quality)


class Plus7Program(Mapping, object):
    """Describes an ArtePlus7 video.

    :param video_id: video unique id
    """
    JSON_URL = ('http://arte.tv/papi/tvguide/videos/stream/player/D/'
                '{0}_PLUS7-D/ALL/ALL.json')
    INFOS_VALUES = ('id', 'date', 'name', 'urls')
    DATE_FMT = '%Y-%m-%d'

    def __init__(self, video_id):
        super().__init__()
        self.id = video_id  # pylint:disable=invalid-name

        try:
            page = page_read(self._video_json_url(self.id))
            self._video = self._video_json(page)

            self.name = self.__name()
            self.urls = self.__urls()
            self.timestamp = self.__timestamp()

        except HTTPError:
            raise ValueError('%s: No JSON for video' % (self.id))
        except KeyError as err:
            raise ValueError('%s: Incomplete JSON for id: %s' % (self.id, err))
        except ValueError as err:
            raise ValueError('%s: %s' % (self.id, err))

    @property
    def date(self):
        """Format timestamp to date string."""
        return datetime.fromtimestamp(self.timestamp).strftime(self.DATE_FMT)

    @classmethod
    def _video_json(cls, page):
        """Extract 'video' json informations from page."""
        _json = json.loads(page)
        video = _json['videoJsonPlayer']
        cls.__detect_video_error(video)

        return video

    @staticmethod
    def __detect_video_error(video):
        err_msg = video.get('custom_msg', {}).get('type', None)
        if err_msg == 'error':
            raise ValueError('Video Error: %s' % (err_msg))

    def __timestamp(self):
        """Return video timestamp from dict."""
        return self._video['videoBroadcastTimestamp'] / 1000.0

    def __name(self):
        """Return video name from dict."""
        return self._video['VST']['VNA']

    def __urls(self, media='mp4'):
        """Return video urls from dict."""
        videos = {}
        for vdict in self._video['VSR'].values():
            if vdict['mediaType'] != media:
                continue
            url = VideoUrl.from_json_dict(self, vdict)
            videos.setdefault(url.lang, {})[url.quality] = url

        return videos

    def infos(self, values=()):
        """Return a dict describing the object.

        Default to all values in INFOS_VALUES.
        """
        values = set(values or self.INFOS_VALUES)
        return {v: getattr(self, v) for v in values}

    def download(self, lang, quality, directory=None):
        """Download the video."""
        video = self.urls[lang][quality]
        download(video, video.full_name, directory)

    # Using by giving video URL

    @classmethod
    def _video_json_url(cls, video_id):
        """Url to JSON video description."""
        short_id = cls._short_id(video_id)
        json_url = cls.JSON_URL.format(short_id)
        return json_url

    @staticmethod
    def _short_id(video_id):
        """Return short id used for jon entry.

        >>> print(Plus7Program._short_id('058941-007-A'))
        058941-007
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

        >>> print(Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/de/055969-002-A/tracks?autoplay=1'))
        055969-002-A

        >>> print(Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/fr/055900-002-A/trop-xx?autoplay=1'))
        055900-002-A

        >>> print(Plus7Program._id_from_url(
        ...   'http://www.arte.tv/guide/fr/058941-008/tracks'))
        058941-008
        >>> print(Plus7Program._id_from_url(
        ...   'https://www.arte.tv/fr/videos/053915-002-A/france-allemagne/'))
        053915-002-A
        """
        url = re.sub(r'\?.*', '', url)
        url = re.sub(r'/$', '', url)
        video_id = url.split('/')[-2]
        return video_id

    # Mapping implementation

    def __getitem__(self, vlang):
        return self.urls.__getitem__(vlang)

    def __len__(self):
        return len(self.urls)

    def __iter__(self):
        return iter(self.urls)


class ArtePlus7(object):
    """ArtePlus7 helps using arte website."""
    PROGRAMS_JSON_URL = 'http://www.arte.tv/guide/fr/plus7.json'
    PROGRAMS = {
        'tracks': 'Tracks',
        'karambolage': 'Karambolage',
        'xenius': 'X:enius',
    }
    PROGRAMS_SEARCH = 'http://www.arte.tv/fr/search/?q={0}'

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

    _parser.add_argument('-l', '--lang',
                         help=u'Video lang to download')

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
    if any((opts.quality, opts.lang)) and not all((opts.quality, opts.lang)):
        print("Use --quality and --lang are required together")
        exit(1)

    for program in programs:
        if any((opts.quality, opts.lang)):
            program.download(opts.lang, opts.quality, opts.download_directory)
        else:
            print(json.dumps(program.infos(), indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
