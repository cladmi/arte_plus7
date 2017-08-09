# -*- coding:utf-8 -*-

"""arte_plus7 test module."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import unittest
try:
    from mock import patch, Mock
except ImportError:
    from unittest.mock import patch, Mock

import arte_plus7
from . import open_url, save_url_if_non_present


def urlopen_mock(subdir='.'):
    """Create a mock for urlopen using given subdir for storage."""
    def _urlopen(url):
        """Return file handle for url."""
        save_url_if_non_present(url, subdir=subdir)
        return open_url(url, subdir=subdir, mode='rb')
    return Mock(side_effect=_urlopen)


class TestArtePlus7(unittest.TestCase):
    """Test arte_plus7 module."""

    def test_get_page_from_cache(self):
        """Test getting a page from cache."""
        url = 'http://www.arte.tv/fr/search/?q=Tracks'
        with patch('arte_plus7.urlopen', urlopen_mock('tracks')) as urlopen:
            arte_plus7.page_read(url)
        self.assertTrue(urlopen.called)

    def test_arte_program(self):
        """Test getting arte program urls."""
        with patch('arte_plus7.urlopen', urlopen_mock('tracks')) as urlopen:
            programs = arte_plus7.ArtePlus7.program('tracks')

        print(programs)
        self.fail()
