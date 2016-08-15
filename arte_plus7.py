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

import re
import os.path

# pylint:disable=locally-disabled,import-error,no-name-in-module
try:
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import HTTPError

import unicodedata
from datetime import datetime
import bs4
import json
import subprocess
import argparse
import logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())

__version__ = '2.3.0'


def page_read(url):
    """Download the page and return the utf-8 decoded result."""
    LOGGER.debug('Reading %s', url)
    return urlopen(url).read().decode('utf-8')


def page_soup(page):
    """Get the page soup."""
    return bs4.BeautifulSoup(page, 'html.parser')


def _json_dumps(obj):
    """Dumps object to JSON"""
    print(json.dumps(obj, indent=4, sort_keys=True))


class Plus7Program(object):
    """Describes an ArtePlus7 video.

    :param video_id: video unique id
    """
    JSON_URL = ('http://arte.tv/papi/tvguide/videos/stream/player/F/'
                '{0}_PLUS7-F/ALL/ALL.json')
    LANGS = {'FR': {'FR', 'VF', 'VOF', 'VOSTF'}}
    # 'DE': {'DE': {'VA'}}  missing stuff maybe

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
            self.date = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d')
            self.name = player['VST']['VNA']
            self.full_name = '{self.name}_{self.date}'.format(self=self)
            self.title = self._sanitize_title(self._title(player))
            self.urls = self._extract_videos(player['VSR'])
        except KeyError as err:
            raise ValueError('Incomplete JSON for id: %s: %s' % (err, debug_id))

    @staticmethod
    def _title(player):
        return player.get('VSU', '') or player.get('VTI', '')

    @staticmethod
    def _sanitize_title(title):
        """Remove special characters

        http://sametmax.com/transformer-des-caracteres-speciaux-en-ascii/

        >>> Plus7Program._sanitize_title('La bière, cette créature méconnue')
        'La_biere,_cette_creature_meconnue'
        >>> Plus7Program._sanitize_title('Les Chiens de Navarre / '
        ...                              'Chelsea Wolfe / OG Maco')
        'Les_Chiens_de_Navarre_-_Chelsea_Wolfe_-_OG_Maco'

        """
        title = unicodedata.normalize('NFKD', title)
        title = title.encode('ascii', 'ignore').decode('ascii')
        title = title.replace(' ', '_')
        title = title.replace('/', '-')
        title = title.replace(':', '-')
        return str(title)

    def infos(self, values=('date', 'name', 'full_name', 'urls', 'title')):
        """Return a dict describing the object."""
        values = set(values)
        ret = {p: v for p, v in self.__dict__.items() if p in values}
        return ret

    def download(self, quality, directory=None, version=None):
        """Download the video."""
        versions = self.urls.keys()

        if version is not None:
            _version = version
        else:
            # Select version automatically
            if len(self.urls) == 1:
                _version = versions[0]
            else:
                raise ValueError('Multiple versions, should select one: %s' %
                                 list(versions))

        url = self.urls[_version][quality]
        directory = directory or '.'

        if version:
            dl_name = '{name}_{quality}_{version}.mp4'
        else:
            dl_name = '{name}_{quality}.mp4'
        dl_name = dl_name.format(name=self.full_name, quality=quality,
                                 version=version)
        dl_name = os.path.join(directory, dl_name)

        cmd = ['wget', '--continue', '-O', dl_name, url]
        LOGGER.info(' '.join(cmd))
        subprocess.call(cmd)

    @classmethod
    def _extract_videos(cls, vsr, media='mp4', lang='FR'):
        langs = cls.LANGS[lang]
        all_videos = {}
        for video in vsr.values():
            if video['mediaType'] != media:
                continue
            video_lang = video['versionShortLibelle']
            if video_lang not in langs:
                continue
            videos = all_videos.setdefault(video_lang, {})
            videos[video['VQU']] = video['url']
        return all_videos

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
        soup = page_soup(page_read(url))
        tag = soup.find(cls.search_results)

        program_dict = cls.extract_program_dict(tag.text)
        programs = []
        for program in program_dict['programs']:
            try:
                prog = Plus7Program(program['id'])
            except ValueError as err:
                # Ignore 'previews' or 'outdated'
                LOGGER.debug('Error while reading program: %r' % err)
            else:
                programs.append(prog)

        programs.sort(key=lambda p: p.timestamp, reverse=True)

        return programs

    @staticmethod
    def search_results(tag):
        """ Tells in this tag is the requested json url file """
        # Script matching
        script_re = re.compile(r'var element = React.createElement\(Search, {')

        keep = True
        keep = keep and tag.get('type', None) == 'text/javascript'
        keep = keep and bool(script_re.search(tag.text.strip()))

        return keep

    @staticmethod
    def extract_program_dict(text):
        """Extract program dict from script tag."""
        entry = 'initialResults: '
        tail = '.programs,'

        line = ''
        for line in text.splitlines():
            if re.search(entry, line):
                break
        else:
            raise ValueError("'%s' not in text:\n%s" % (entry, text))

        line = re.sub(r'^\s*%s' % entry, '', line)
        line = re.sub(r'%s$' % tail, '', line)

        return json.loads(line)


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
    _parser.add_argument('-lv', '--lang-version',
                         help=u'Select between different version in a lang')
    _parser.add_argument('--keep-artifacts', action='store_true',
                         default=False,
                         help=u'Keep intermediate files artifacts')

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
        programs = ArtePlus7.search(ArtePlus7.PROGRAMS[opts.program])
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
            try:
                program.download(opts.quality,
                                 directory=opts.download_directory,
                                 version=opts.lang_version)
            except ValueError as err:
                LOGGER.error(err)
                exit(1)
        else:
            print(json.dumps(program.infos(), indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
