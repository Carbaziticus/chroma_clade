"""
Usage:
    python setup.py py2app
"""

from setuptools import setup

_VERSION="1.0"

APP = ['src/gui.py']
DATA_FILES = [] # may want to use this for py2exe
PY2APP_OPTIONS = {'resources': 
                    'src/default_colour.csv,src/title.gif,src/tree.gif,src/col.tree.gif',
                    'iconfile': 'src/tree.icns'
                    }
PY2EXE_OPTIONS = {"packages": ["biopython"]}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': PY2APP_OPTIONS},
    setup_requires=['py2app'], # will this mess up py2exe?

    windows=['gui.py'],
    console=['chroma_clade.py'],

    description = "A GUI and CLI app for producing phylogenetic tree files coloured by observed molecular sequence states",
    author = 'Christopher Monit', 
    author_email = 'c.monit.12@ucl.ac.uk', 
    url = 'https://github.com/chrismonit/chroma_clade',
    install_requires=['biopython'],
    long_description=open("README.txt").read(),

)
