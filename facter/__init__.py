import json
import logging
import os
import subprocess
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

try:
    import yaml
except ImportError:
    logging.warning("PyYAML not available, falling back to plain text parsing")
    yaml = None  # type: ignore[assignment]


def _parse_cli_facter_results(
    facter_results: str,
) -> Generator[Tuple[str, str], None, None]:
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
        res = line.split(" => ", 1)
        if len(res) == 1:
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


class Facter:
    def __init__(
        self,
        facter_path: str = "facter",
        external_dir: Optional[str] = None,
        use_yaml: bool = True,
        cache_enabled: bool = True,
        get_puppet_facts: bool = False,
    ) -> None:
        self.facter_path = facter_path
        self.external_dir = external_dir
        self._use_yaml = use_yaml
        self.cache_enabled = cache_enabled
        self._get_puppet_facts = get_puppet_facts
        self._cache: Optional[Dict[str, Any]] = None

    @property
    def uses_yaml(self) -> bool:
        """Determines if the yaml library is available and selected"""
        return self._use_yaml and bool(yaml)

    def run_facter(self, key: Optional[str] = None) -> Union[Dict[str, Any], Any]:
        """Run the facter executable with an optional specfic
        fact. Output is parsed to yaml if available and
        selected. Puppet facts are always selected. Returns a
        dictionary if no key is given, and the value if a key is
        passed."""
        args = [self.facter_path]
        # getting puppet facts seems to be writing data to the home directory of
        # the run time user even when cache is not selected.
        # The only additional fact that we can get as of now is `puppetversion.`
        # that is available using puppet.version fact.
        if self._get_puppet_facts:
            args.append("--puppet")
        if self.external_dir is not None:
            args.append("--external-dir")
            args.append(self.external_dir)
        if self.uses_yaml:
            args.append("--yaml")
        if key is not None:
            args.append(key)
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"facter command failed: {stderr.decode()}")
        results = stdout.decode()
        if self.uses_yaml:
            parsed_results = yaml.safe_load(results)
            if key is not None:
                return parsed_results[key]
            else:
                return parsed_results
        if key is not None:
            return results.strip()
        else:
            return dict(_parse_cli_facter_results(results))

    def build_cache(self) -> None:
        """run facter and save the results to `_cache`"""
        cache = self.run_facter()
        self._cache = cache if isinstance(cache, dict) else {}

    def clear_cache(self) -> None:
        self._cache = None

    def has_cache(self) -> bool:
        """Intended to be called before any call that might access the
        cache. If the cache is not selected, then returns False,
        otherwise the cache is build if needed and returns True."""
        if not self.cache_enabled:
            return False
        if self._cache is None:
            self.build_cache()
        return True

    def lookup(self, fact: str, cache: bool = True) -> Any:
        """Return the value of a given fact and raise a KeyError if
        it is not available. If `cache` is False, force the lookup of
        the fact."""
        if (not cache) or (not self.has_cache()):
            val = self.run_facter(fact)
            if val is None or val == "":
                raise KeyError(fact)
            return val
        if self._cache is None:
            raise RuntimeError("Cache is None but has_cache returned True")
        return self._cache[fact]

    def get(self, k: str, d: Any = None) -> Any:
        """Dictionary-like `get` method with a default value"""
        try:
            return self.lookup(k)
        except KeyError:
            return d

    @property
    def all(self) -> Dict[str, Any]:
        """Dictionary representation of all facts"""
        if not self.has_cache():
            result = self.run_facter()
            return result if isinstance(result, dict) else {}
        return self._cache or {}

    def keys(self) -> Iterator[str]:
        return iter(self.all.keys())

    def values(self) -> Iterator[Any]:
        return iter(self.all.values())

    def items(self) -> Iterator[Tuple[str, Any]]:
        return iter(self.all.items())

    def __getitem__(self, key: str) -> Any:
        return self.lookup(key)

    def __iter__(self) -> Iterator[str]:
        return self.keys()

    def __repr__(self) -> str:
        return (
            f"<Facter yaml={self.uses_yaml!r} "
            f"cache_enabled={self.cache_enabled!r} "
            f"cache_active={self._cache is not None!r}>"
        )

    def json(self) -> str:
        """Return a json dump of all facts"""
        return json.dumps(self.all)


_FACTER = Facter()


def get_fact(fact: str, default: Any = None) -> Any:
    return _FACTER.get(fact, default)
