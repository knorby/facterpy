facterpy
========

Python library to provide a cached and dictionary-like interface to [Puppet's facter utility](http://puppetlabs.com/puppet/related-projects/facter). 

The facter script is run to gather facts, and YAML output is used if pyYAML is installed.

The library is compatibile with Python 2 and Python 3 and *nix and OS X, although testing hasn't been extensive. 

Usage
------

```
>>> import facter
>>> f = facter.Facter()
>>> f["architecture"]
'x86_64'
>>> f.lookup("uptime_seconds")
195106
>>> f.lookup("uptime_seconds")
195106
>>> f.lookup("uptime_seconds", cache=False)
195234
>>> f = facter.Facter(use_yaml=False)
>>> f.lookup("uptime_seconds")
'195301'
>>> f.get("not a fact", "mere opinion")
'mere opinion'
```

More methods exist. Documentation to come.

Install
---------

```
pip install facter
```

or 

```
pip install facter[yaml]
```

to include pyYAML

Requirements
-------------

Required:

- facter - must be installed through system packages or Ruby Gems
- [six](https://pypi.python.org/pypi/six/) - Python 2 and 3 compatibility (marked in setup.py)

Optional:

- [pyYAML](http://pyyaml.org/wiki/PyYAML) - For YAML parsing of results


Project State
--------------

This is an alpha/early version and it hasn't been tested much. Please report any issues observed.

