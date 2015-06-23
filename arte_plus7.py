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
except ImportError:
    from urllib2 import urlopen

import sys
import os.path
from datetime import datetime
from bs4 import BeautifulSoup
import json
import subprocess
import argparse

__version__ = '1.0.1'


class ArtePlus7(object):
    """ ArtePlus7 helps getting arte videos link and download them """
    PROGRAMS_JSON_URL = 'http://www.arte.tv/guide/fr/plus7.json'
    programs = {
        'tracks': 'Tracks',
        'karambolage': 'Karambolage',
        'xenius': 'X:enius',
    }

    def __init__(self, url, quality=None, keep_artifacts=False):
        self.url = url
        self.quality = quality
        self.keep_artifacts = keep_artifacts

        self.video_name = None

        # intermediate values
        self.page_soup = None
        self.videos_dict = None
        self.summary_dict = None

    @classmethod
    def _programs_dict(cls):
        """ Get the whole programs dict
        Returns it as a dict title:list_of_programs """
        json_content = cls._get_page_content(cls.PROGRAMS_JSON_URL)
        programs = json.loads(json_content)
        # there might be multiple videos with the same title
        # they will be sorted, I think, with newest first
        programs_dict = {}
        for program in programs['videos']:
            programs_dict.setdefault(program['title'], []).append(program)
        return programs_dict

    @classmethod
    def program_url(cls, name):
        """ Return the url for given program """
        programs = cls._programs_dict()
        try:
            progs = programs[name]
            if len(progs) > 1:
                print('Found multiple videos, using the last one',
                      file=sys.stderr)
            return progs[0]['url']
        except KeyError:
            print('No videos found for program: {0}'.format(name))
            exit(1)

    def videos_url(self):
        """ Return the video download urls """
        self._get_page_soup()
        self._get_videos_dict()
        self._get_videos_urls_dict()
        self._save_artifacts()
        return self.summary_dict

    def _get_page_soup(self):
        """ Get the BeautifulSoup decoded page """
        page_raw = self._get_page_content(self.url)
        self.page_soup = BeautifulSoup(page_raw)
        return self.page_soup

    def _get_videos_dict(self):
        """ Extract the the videos description dict """
        json_url = self._get_json_url(self.page_soup)
        json_content = self._get_page_content(json_url)
        self.videos_dict = json.loads(json_content)
        return self.videos_dict

    def _get_videos_urls_dict(self):
        """ Get the videos urls dict """
        aux_d = self.videos_dict["videoJsonPlayer"]

        name = aux_d["VST"]["VNA"]
        timestamp = aux_d['videoBroadcastTimestamp'] / 1000.0
        date = datetime.fromtimestamp(timestamp).strftime(
            '%Y-%m-%d')
        full_name = '{name}_{date}'.format(date=date, name=name)

        # get the mp4/French versions
        vids_dict = {}
        all_vids_dict = aux_d["VSR"]
        for value in all_vids_dict.values():
            if value['mediaType'] != 'mp4':
                continue
            if value['versionShortLibelle'] not in ('VF', 'VOF', 'VOSTF'):
                continue
            vids_dict[value['VQU']] = value['url']

        self.video_name = full_name
        self.summary_dict = {
            'name': name,
            'date': date,
            'full_name': full_name,
            'urls': vids_dict
        }
        return self.summary_dict

    def _get_json_url(self, soup):
        """ Find the json url from the page extract bs4.soup """
        tags = soup.find_all(self._select_json_entry)
        urls = set([tag['arte_vp_url'] for tag in tags])
        assert len(urls) == 1, "No url founds, may it's not available anymore"
        return urls.pop()

    @staticmethod
    def _select_json_entry(tag):
        """ Tells in this tag is the requested json url file """
        keep = True
        keep = keep and tag.has_attr('class')
        keep = keep and tag.has_attr('arte_vp_lang')
        keep = keep and tag.has_attr('arte_vp_config')
        keep = keep and tag.has_attr('arte_vp_url')
        if not keep:
            return False

        try:
            keep = keep and (tag['arte_vp_lang'] == 'fr_FR')
            keep = keep and 'PLUS7-F' in tag['arte_vp_url']
        except KeyError:
            return False

        return keep

    @staticmethod
    def _get_page_content(url):
        """ Download the page and return the utf-8 decoded result """
        ret = urlopen(url).read().decode('utf-8')
        return ret

    def download_video(self, directory=None):
        """ Download the video """
        directory = directory or '.'

        url = self.summary_dict['urls'][self.quality]
        dl_name = '{name}_{quality}.mp4'
        dl_name = dl_name.format(name=self.video_name, quality=self.quality)
        dl_name = os.path.join(directory, dl_name)

        cmd = ['wget', '--continue', '-O', dl_name, url]
        print(' '.join(cmd))
        subprocess.call(cmd)

    def _save_artifacts(self):
        """ Save the script artifacts to help adding features """
        if not self.keep_artifacts:
            return
        name = self.video_name
        with open(name + '_page.html', 'w') as page:
            page.write(self.page_soup.prettify().encode('utf-8'))
        with open(name + '_player_cfg.json', 'w') as json_cfg:
            json_cfg.write(
                json.dumps(
                    self.videos_dict, indent=4, sort_keys=True
                ).encode('utf-8')
            )
        with open(name + '_summary.json', 'w') as summary:
            summary.write(
                json.dumps(
                    self.summary_dict, indent=4, sort_keys=True
                ).encode('utf-8')
            )

    @staticmethod
    def parser():
        """ arte_plus_7 parser """
        parser = argparse.ArgumentParser(
            description=u'ArtePlus7 videos download')
        vid_parser = parser.add_mutually_exclusive_group(required=True)
        vid_parser.add_argument('-u', '--url',
                                help=u'Arte page to download video from')
        vid_parser.add_argument('-p', '--program',
                                choices=ArtePlus7.programs.keys(),
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
    url = opts.url or ArtePlus7.program_url(ArtePlus7.programs[opts.program])

    arte_plus_7 = ArtePlus7(url, opts.quality, opts.keep_artifacts)

    urls_dict = arte_plus_7.videos_url()

    if opts.quality is not None:
        arte_plus_7.download_video(opts.download_directory)
    else:
        print(json.dumps(urls_dict, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
