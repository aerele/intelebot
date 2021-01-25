# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in intelebot/__init__.py
from intelebot import __version__ as version

setup(
	name='intelebot',
	version=version,
	description='Integration of telegram bots to frappe and ERPNext',
	author='Aerele Technologies Private Limited',
	author_email='hello@aerele.in',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
