#! /usr/bin/python
# -*- coding:utf-8 -*-


"""arte_plus7 tests package."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import os
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


PAGES_DIR = os.path.join(os.path.dirname(__file__), 'pages')


def save_url_if_non_present(url, subdir='.'):
    """Download url to pages storage if its not present."""
    path = path_for_url(url, subdir=subdir)
    # Test file exist
    try:
        open(path).close()
        return
    except EnvironmentError:
        pass

    with open(path, 'wb') as stored:
        page = urlopen(url).read()
        stored.write(page)


def open_url(url, subdir='.', *args, **kwargs):
    """Open url from pages storage."""
    path = path_for_url(url, subdir=subdir)
    return open(path, *args, **kwargs)


def path_for_url(url, subdir='.', _dir=PAGES_DIR):
    """Return path for given url.

    >>> path = ('./pages/tracks/'
    ...         'http:||www.arte.tv|guide|fr|emissions|TRA|tracks')
    >>> path_for_url('http://www.arte.tv/guide/fr/emissions/TRA/tracks',
    ...              subdir='tracks', _dir='./pages') == path
    True
    """
    name = _safe_name_for_url(url)
    return os.path.join(_dir, subdir, name)


def _safe_name_for_url(url):
    """Returns a name safe to save url.

    >>> url = 'http://www.arte.tv/guide/fr/emissions/TRA/tracks'
    >>> name = 'http:||www.arte.tv|guide|fr|emissions|TRA|tracks'
    >>> _safe_name_for_url(url) == name
    True
    """
    path = url
    path = path.replace('/', '|')
    return path
