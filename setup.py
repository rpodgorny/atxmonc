#!/usr/bin/python3

from setuptools import setup, find_packages

from atxmon.version import __version__

setup(
	name = 'atxmonc',
	version = __version__,
	options = {
		'build_exe': {
			'compressed': True,
			'include_files': ['etc/atxmonc.conf', ]
		},
	},
	scripts = ['atxmonc', ],
	packages = find_packages(),
)
