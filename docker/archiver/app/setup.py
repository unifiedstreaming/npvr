# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='archiver',
    version='0.1.0',
    description='Archiver',
    long_description='Remix nPVR Archiver proof of concept',
    author='Mark Ogle',
    author_email='mark@unified-streaming.com',
    packages=find_packages(exclude=('tests', 'docs'))
)
