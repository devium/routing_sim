#!/usr/bin/env python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('requirements.txt') as requirements:
    reqs = requirements.read().split()

config = {
    'description': 'raidensim',
    'version': '1.0.0-SNAPSHOT',
    'packages': ['raidensim', 'raidensim.network'],
    'scripts': [],
    'name': 'raidensim',
    'install_requires': reqs
}

setup(**config)
