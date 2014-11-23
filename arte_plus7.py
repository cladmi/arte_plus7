#! /usr/bin/python
# -*- coding:utf-8 -*-

from __future__ import print_function

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


from datetime import datetime
from bs4 import BeautifulSoup
import re
import json
import sys
import subprocess
import argparse

class ArtePlus7(object):

    def __init__(self, url, quality=None, keep_artifacts=False):
        self.url = url
        self.quality = quality
        self.keep_artifacts = keep_artifacts

        self.video_name = None

        # intermediate values
        self.page_soup = None
        self.videos_dict = None
        self.summary_dict = None

    def videos_url(self):
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
        tags = soup.find_all(self._select_json_entry)
        urls = set([tag['arte_vp_url'] for tag in tags])
        assert len(urls) == 1, "No url founds, may it's not available anymore"
        return urls.pop()

    @staticmethod
    def _select_json_entry(tag):
        ok = True
        ok = ok and tag.has_attr('class')
        ok = ok and tag.has_attr('arte_vp_lang')
        ok = ok and tag.has_attr('arte_vp_config')
        ok = ok and tag.has_attr('arte_vp_url')
        if not ok:
            return False

        try:
            ok = ok and (tag['arte_vp_lang'] == 'fr_FR')

            url = tag['arte_vp_url']
            ok = ok and 'PLUS7-F' in url
        except KeyError:
            return False

        return ok

    @staticmethod
    def _get_page_content(url):
        """ Download the page and return the utf-8 decoded result """
        ret = urlopen(url).read().decode('utf-8')
        return ret

    def download_video(self):
        """ Download the video """
        url = self.summary_dict['urls'][self.quality]
        dl_name = '{name}_{quality}.mp4'.format(
            name=self.video_name, quality=self.quality)
        cmd = ['wget', '--continue', url, '-O', dl_name]
        subprocess.call(cmd)

    def _save_artifacts(self):
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
        parser = argparse.ArgumentParser(description=u'ArtePlus7 videos download')
        parser.add_argument('url',
                            help=u'Arte page to download video from')
        parser.add_argument('-q', '--quality', choices=(u'HQ', u'EQ', u'SQ'),
                            help=u'Video quality to download')
        parser.add_argument('--keep-artifacts', action='store_true', default=False,
                            help=u'Keep intermediate files artifacts')
        return parser


def main():
    opts = ArtePlus7.parser().parse_args()
    arte_plus_7 = ArtePlus7(opts.url, opts.quality, opts.keep_artifacts)

    urls_dict = arte_plus_7.videos_url()

    if opts.quality is not None:
        arte_plus_7.download_video()
    else:
        print(json.dumps(urls_dict, indent=4, sort_keys=True).encode('utf-8'))


if __name__ == '__main__':
    main()
