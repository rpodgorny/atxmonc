import sys
from cx_Freeze import setup, Executable

from atxmon.version import __version__


base = 'Win32GUI'

executables = [
	Executable(
		script='atxmonc',
		#appendScriptToExe=True,
		#appendScriptToLibrary=False,
		#compress=True,
	),
	#Executable(
	#	script='faddnsc_gui',
	#	appendScriptToExe=True,
	#	appendScriptToLibrary=False,
	#	compress=True,
	#	base=base
	#),
]

setup(
	name = 'atxmonc',
	version = __version__,
	options = {
		'build_exe': {
			#'includes': ['re', ],
			#'create_shared_zip': False,
			#'compressed': True,
			'include_msvcr': True,
			'packages': ['asyncio', ],
		},
	},
	executables = executables,
)
