from setuptools import setup

setup(
    name='ptb',
    version='0.1.0',
    packages=['ptb'],
    entry_points={
        'console_scripts': ['ptb=ptb.ptb:main']
    }
)
