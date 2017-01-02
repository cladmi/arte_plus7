=========
ArtePlus7
=========

ArtePlus7 is a python script aimed at downloading the mp4 videos from
ArtePlus7 using their url.

It's based on BeautifulSoup4.

Usage
-----

The following commands will return the videos urls found

::

    # The page dedicated to the video

    ./arte_plus_7.py -u http://www.arte.tv/guide/fr/034049-007/karambolage

    # Direct access to some pre-stored programs

    ./arte_plus_7.py -p tracks

To actually download the video, add a ``--qualiy <QUAL>`` for the one
you want from the list

::

    # Download 'tracks' with selected quality

    ./arte_plus_7.py -p tracks --quality <MQ|HQ|EQ|SQ>
