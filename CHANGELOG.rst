=========
Changelog
=========

2.2.1 - 2.2.2 - 2.2.3: Updates for Pypi
---------------------------------------

* 2.2.3: convert ``README`` to reStructuredText
* 2.2.3: add a changelog in ``CHANGELOG.rst``
* 2.2.3: add ``CHANGELOG.rst`` to ``long_description``

* 2.2.2: fixes issues while releasing previous version on pypi
* 2.2.1: changes for pypi


2.2.0: Update to the new search results
-----------------------------------------

* Fix search handling
* Improve 'program' to exclude not matching included search results
* Add a '--version' option
* Remove unused '--keep-artifacts' option
* Pylint/pep8 cleanup
* tox.ini: update to fail on pylint/pep8 errors.


2.1.0: New ArtePlus7 search handling
------------------------------------

* Handle new way of presenting search results
* Fix num-progs for ``-1`` to use all entries
* Nicely handle some errors and add debug logging


2.0.0: New ArtePlus7 site and new options
-----------------------------------------

* Adapt to new ArtePlus7 interface, main JSON has been removed and now a
  search page should be parsed to get search results
* Allow downloading multiple videos
* Add a ``--search`` option to search using arte search engine
* Add also a ``--verbose`` option
