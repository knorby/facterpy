import os

from setuptools import setup, find_packages

VERSION = "0.1"

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "facterpy",
    version = VERSION,
    packages = find_packages(),
    author = "Kali Norby",
    author_email = "karl.norby@gmail.com",
    license = "BSD",
    keywords = "facter puppet ruby",
    url="https://github.com/knorby/facterpy",
    install_requires = "six",
    extras_require = {
        'yaml': ['pyYAML'],
        },
    zip_safe = True,
    classifiers = [
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Topic :: System :: Systems Administration",
        "Intended Audience :: System Administrators",
        "Programming Language :: Ruby",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        ],
    )    
