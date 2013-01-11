# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-youtube',
    version='0.2',
    author=u'Suleyman Melikoglu',
    author_email='suleyman@melikoglu.info',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/laplacesdemon/django-youtube',
    license='BSD licence, see LICENCE.txt',
    description='Youtube API wrapper app for Django.' + \
                ' It helps to upload, display, delete, update videos from Youtube',
    long_description=open('README.md').read(),
    zip_safe=False,
)
