facterpy
========

Python library to provide a cached and dictionary-like interface to [Puppet's facter utility](http://puppetlabs.com/puppet/related-projects/facter).

The library uses JSON output by default (facter 3.0+) with automatic fallback to plain text parsing for maximum compatibility and performance.

Usage
-----

```python
>>> import facter
>>> f = facter.Facter()
>>> f["architecture"]
'x86_64'
>>> f.lookup("uptime_seconds")
195106
>>> f.lookup("uptime_seconds")  # cached result
195106
>>> f.lookup("uptime_seconds", cache=False)  # force refresh
195234
>>> f.get("not_a_fact", "default_value")
'default_value'
>>> f.all  # get all facts as dictionary
{'architecture': 'x86_64', 'uptime_seconds': 195234, ...}
```

### Advanced Usage

```python
# Custom facter path
f = facter.Facter(facter_path="/usr/local/bin/facter")

# External facts directory
f = facter.Facter(external_dir="/etc/puppetlabs/facter/facts.d")

# Include Puppet facts
f = facter.Facter(get_puppet_facts=True)

# Disable caching
f = facter.Facter(cache_enabled=False)

# Enable legacy facts (equivalent to facter --show-legacy)
f = facter.Facter(legacy_facts=True)
f.lookup("architecture")  # Works with legacy facts enabled
f["operatingsystem"]      # Legacy facts appear in f.all
```

Install
-------

```bash
pip install facterpy
```

Requirements
------------

**Required:**
- Python 3.8+
- `facter` command-line utility (install via system packages or Puppet)

**No external Python dependencies** - uses only Python standard library.

Compatibility
-------------

- **Python**: 3.8+ (Python 2 support removed in v0.2.0)
- **Facter**: 3.0+ (JSON output), with fallback support for older versions
- **Platforms**: Linux, macOS, and other POSIX systems

### Legacy Facts

Modern facter (4.x+) uses structured facts, so legacy top-level facts like `architecture` are nested under structured facts like `os.architecture`. To access legacy facts that were available in older facter versions:

```python
# Modern behavior (default) - structured facts only
f = facter.Facter()
f.lookup("architecture")  # Raises KeyError - not in structured output
f.all["os"]["architecture"]  # Works - nested in structured facts

# Legacy behavior - includes legacy facts (like facter --show-legacy)
f = facter.Facter(legacy_facts=True)
f.lookup("architecture")  # Works - legacy fact available
f["architecture"]  # Works - appears in f.all output
```

Migration from v0.1.x
---------------------

The `use_yaml` parameter is deprecated but still supported with a warning:

```python
# Old (deprecated, shows warning)
f = facter.Facter(use_yaml=False)

# New (recommended)
f = facter.Facter()  # Automatically uses JSON with text fallback
```

Project State
-------------

I've done very little to maintain this library since initally writing it (sorry!), but it is very simple and has some apparent usage. It is modernized in v0.2.0+, and I will look to make a v1.0.0 release at some point soon. I haven't used Puppet in quite some time, so I'm not an active user of this library.
