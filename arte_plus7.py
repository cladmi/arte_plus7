#! /usr/bin/python

from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import json
import sys
import subprocess

def get_page_content(arte_url):
    ret = urlopen(arte_url).read().decode('utf-8')
    return ret


def select_json_entry(tag):
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


def get_json_url(soup):
    tags = soup.find_all(select_json_entry)
    urls = set([tag['arte_vp_url'] for tag in tags])
    assert len(urls) == 1, "No url founds, may it's not available anymore"

    return urls.pop()

def get_videos_urls_dict(page_content):
    vids_json = json.loads(page_content)
    name = vids_json["videoJsonPlayer"]["VST"]["VNA"]
    all_vids_dict = vids_json["videoJsonPlayer"]["VSR"]


    vids_dict = {}
    ret_dict = {'name': name, 'urls': vids_dict}
    for value in all_vids_dict.values():
        if value['mediaType'] != 'mp4':
            continue
        if value['versionShortLibelle'] not in ('VF', 'VOF', 'VOSTF'):
            continue
        vids_dict[value['VQU']] = value['url']


    return ret_dict


def videos_url(arte_url):
    page_content = get_page_content(arte_url)
    soup = BeautifulSoup(page_content)
    # print(soup.prettify())
    json_url = get_json_url(soup)

    page_content = get_page_content(json_url)

    ret = get_videos_urls_dict(page_content)
    return ret

def download_video(videos_dict, quality):
    url = videos_dict['urls'][quality]
    name = videos_dict['name']
    dl_name = '{name}_{quality}.mp4'.format(name=name, quality=quality)
    print((dl_name, url))
    cmd = ['wget', '--continue', url, '-O', dl_name]
    subprocess.call(cmd)



def main(arte_url, quality=None):
    urls_dict = videos_url(arte_url)
    if quality is not None:
        assert quality in ('HQ', 'SQ', 'EQ')
        download_video(urls_dict, quality)
        pass
    else:
        print(json.dumps(urls_dict, indent=4, sort_keys=True))


if __name__ == '__main__':
    try:
        arte_url = sys.argv[1]
        quality = sys.argv[2] if len(sys.argv) == 3 else None
        main(arte_url, quality)
    except IndexError:
        print('Usage: {0} <arte_page_url>'.format(sys.argv[0]),
              file=sys.stderr)
        exit(1)
