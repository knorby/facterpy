import os
import subprocess
import warnings

import six
try:
    import yaml
except ImportError:
    warnings.warn("no yaml module loaded", ImportWarning)
    yaml = None

def _parse_cli_facter_results(facter_results):
    '''Parse key value pairs printed with "=>" separators.
    YAML is preferred output scheme for facter.

    >>> list(_parse_cli_facter_results("""foo => bar
    ... baz => 1
    ... foo_bar => True"""))
    [('foo', 'bar'), ('baz', '1'), ('foo_bar', 'True')]
    >>> list(_parse_cli_facter_results("""foo => bar
    ... babababababababab
    ... baz => 2"""))
    [('foo', 'bar\nbabababababababab'), ('baz', '2')]
    >>> list(_parse_cli_facter_results("""3434"""))
    Traceback (most recent call last):
        ...
    ValueError: parse error


    Uses a generator interface:
    >>> _parse_cli_facter_results("foo => bar").next()
    ('foo', 'bar')
    '''
    last_key, last_value = None, []
    for line in filter(None, facter_results.splitlines()):
        res = line.split(six.u(" => "), 1)
        if len(res)==1:
            if not last_key:
                raise ValueError("parse error")
            else:
                last_value.append(res[0])
        else:
            if last_key:
                yield last_key, os.linesep.join(last_value)
            last_key, last_value = res[0], [res[1]]
    else:
        if last_key:
            yield last_key, os.linesep.join(last_value)


class Facter(object):

    def __init__(self, facter_path="facter",
                 use_yaml=True, cache_enabled=True):
        self.facter_path = facter_path
        self._use_yaml = use_yaml
        self.cache_enabled = cache_enabled
        self._cache = None
        
    @property
    def uses_yaml(self):
        """Determines if the yaml library is available and selected"""
        return self._use_yaml and bool(yaml)
        
    def run_facter(self, key=None):
        """Run the facter executable with an optional specfic
        fact. Output is parsed to yaml if available and
        selected. Puppet facts are always selected. Returns a
        dictionary if no key is given, and the value if a key is
        passed."""
        args = [self.facter_path]
        #this seems to not cause problems, but leaving it separate
        args.append("--puppet")
        if self.uses_yaml:
            args.append("--yaml")
        if key is not None:
            args.append(key)
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        results = proc.stdout.read()
        if self.uses_yaml:
            parsed_results = yaml.load(results)
            if key is not None:
                return parsed_results[key]
            else:
                return parsed_results
        results = results.decode()
        if key is not None:
            return results.strip()
        else:
            return dict(_parse_cli_facter_results(results))

    def build_cache(self):
        """run facter and save the results to `_cache`"""
        cache = self.run_facter()
        self._cache = cache

    def clear_cache(self):
        self._cache = None

    def has_cache(self):
        """Intended to be called before any call that might access the
        cache. If the cache is not selected, then returns False,
        otherwise the cache is build if needed and returns True."""
        if not self.cache_enabled:
            return False
        if self._cache is None:
            self.build_cache()
        return True

    def lookup(self, fact, cache=True):
        """Return the value of a given fact and raise a KeyError if
        it is not available. If `cache` is False, force the lookup of
        the fact."""
        if (not cache) or (not self.has_cache()):
            val =  self.run_facter(fact)
            if val is None or val == '':
                raise KeyError(fact)
            return val
        return self._cache[fact]
    
    def get(self, k, d=None):
        """Dictionary-like `get` method with a default value"""
        try:
            return self.lookup(k)
        except KeyError:
            return d

    @property
    def all(self):
        """Dictionary representation of all facts"""
        if not self.has_cache():
            return self.run_facter()
        return self._cache

    def iterkeys(self):
        return six.iterkeys(self.all)

    def keys(self):
        return self.all.keys()

    def iterkeys(self):
        return six.iterkeys(self.all)
    
    def values(self):
        return self.all.values()

    def iteritems(self):
        return six.iteritems(self.all)

    def items(self):
        return self.all.items()

    def __getitem__(self, key):
        return self.lookup(key)

    def __iter__(self):
        return iter(self.keys())

    def __repr__(self):
        return ('<Facter yaml=%r cache_enabled=%r cache_active=%r>'
                % (self.uses_yaml, self.cache_enabled,
                   (self._cache is not None)))
    
    def json(self):
        """Return a json dump of all facts"""
        import json
        return json.dumps(self.all)
        
            
    
