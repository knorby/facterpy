import os
import subprocess
import warnings

try:
    import yaml
except ImportError:
    warnings.warn("no yaml module loaded", ImportWarning)
    yaml = None

def _parse_cli_facter_results(facter_results):
    """parse key value pairs printed with "=>" separators.
    YAML is preferred output scheme for facter."""
    last_key, last_value = None, []
    for line in filter(None, facter_results.splitlines()):
        res = line.split(" => ", 1)
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
        return self._use_yaml and bool(yaml)
        
    def run_facter(self, key=None):
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
        if key is not None:
            return results.strip()
        else:
            return dict(_parse_cli_facter_results(results))

    def build_cache(self):
        cache = self.run_facter()
        self._cache = cache

    def clear_cache(self):
        self._cache = None

    def has_cache(self):
        if not self.cache_enabled:
            return False
        if self._cache is None:
            self.build_cache()
        return True

    def lookup(self, fact, skip_cache=False):
        if skip_cache or not self.has_cache():
            return self.run_facter(fact)
        return self._cache[fact]
    
    def get(self, k, d=None):
        try:
            return self.lookup(k)
        except KeyError:
            return d

    @property
    def all(self):
        if not self.has_cache():
            return self.run_facter()
        return self._cache

    def keys(self):
        return self.all.keys()

    def values(self):
        return self.all.values()

    def iteritems(self):
        return self.all.iteritems()

    def __getitem__(self, key):
        return self.lookup(key)

    def __iter__(self):
        return iter(self.keys())

    def __repr__(self):
        return ('<Facter yaml=%r cache_enabled=%r cache_active=%r>'
                % (self.uses_yaml, self.cache_enabled,
                   (self._cache is not None)))
    
    def json(self):
        import json
        return json.dumps(self.all)
        
            
    
