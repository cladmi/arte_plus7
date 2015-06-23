#! /usr/bin/env python
# -*- coding:utf-8 -*-

""" Install the `arte_plus7` script """


from setuptools import setup

NAME = 'arte_plus7'


def get_version(module):
    """ Extract package version without importing file
    Importing cause issues with coverage,
    (modules can be removed from sys.modules to prevent this)
    Inspired from pep8 setup.py
    """
    with open('%s.py' % module) as module_fd:
        for line in module_fd:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])  # pylint:disable=eval-used


setup(
    name=NAME,
    version=get_version(NAME),
    description='CLI script to get videos from Arte plus 7 using their URL',
    author='cladmi',
    download_url='https://github.com/cladmi/arte_plus7',
    py_modules=[NAME],
    entry_points={
        'console_scripts': ['{name} = {name}:main'.format(name=NAME)],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',
    ],
    install_requires=['argparse', 'beautifulsoup4'],
)
