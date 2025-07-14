import json
import logging
import os
import subprocess
from typing import Any, Dict, Generator, Iterator, Optional, Tuple, Union

log = logging.getLogger("facter")


def _parse_cli_facter_results(
    facter_results: str,
) -> Generator[Tuple[str, str], None, None]:
    '''Parse key value pairs printed with "=>" separators.
    Used as fallback when JSON output is not available.

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
            # Continue multiline value
            last_value.append(res[0])  # type: ignore[unreachable] # mypy 3.8 compat
        else:
            if last_key:
                yield last_key, os.linesep.join(last_value)  # type: ignore[unreachable] # mypy 3.8 compat
            last_key, last_value = res[0], [res[1]]

    # Yield final key-value pair if exists
    if last_key:
        yield last_key, os.linesep.join(last_value)


class Facter:
    def __init__(
        self,
        facter_path: str = "facter",
        external_dir: Optional[str] = None,
        cache_enabled: bool = True,
        puppet_facts: bool = False,
        legacy_facts: bool = False,
        # Deprecated - kept for backward compatibility
        use_yaml: Optional[bool] = None,
    ) -> None:
        self.facter_path = facter_path
        self.external_dir = external_dir
        self.cache_enabled = cache_enabled
        self.puppet_facts = puppet_facts
        self.legacy_facts = legacy_facts
        self._cache: Optional[Dict[str, Any]] = None

        # Handle deprecated use_yaml parameter
        if use_yaml is not None:
            log.warning(
                "The 'use_yaml' parameter is deprecated. "
                "facterpy now uses JSON by default with text fallback."
            )

    @property
    def uses_yaml(self) -> bool:
        """Deprecated property. facterpy now uses JSON by default."""
        log.warning(
            "The 'uses_yaml' property is deprecated. "
            "facterpy now uses JSON by default with text fallback."
        )
        return False

    def run_facter(self, key: Optional[str] = None) -> Union[Dict[str, Any], Any]:
        """Run the facter executable with an optional specific fact.

        Uses JSON output by default (facter 3.0+) with fallback to plain text parsing.
        Returns a dictionary if no key is given, and the value if a key is passed.

        If legacy_facts=True, includes legacy facts (like facter --show-legacy).
        This is required for lookup() to find legacy facts like 'architecture' that
        don't appear in modern structured fact output but work with individual
        facter commands (e.g., 'facter architecture').
        """
        base_args = [self.facter_path]

        # Add common arguments
        if self.puppet_facts:
            base_args.append("--puppet")
        if self.external_dir is not None:
            base_args.extend(["--external-dir", self.external_dir])
        if self.legacy_facts:
            base_args.append("--show-legacy")
        if key is not None:
            base_args.append(key)

        # Try JSON first (preferred)
        json_args = base_args + ["--json"]
        try:
            proc = subprocess.Popen(
                json_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate()
            if proc.returncode == 0:
                results = stdout.decode()
                parsed_results = json.loads(results)
                if key is not None:
                    return parsed_results.get(key)
                return parsed_results
        except (json.JSONDecodeError, FileNotFoundError, subprocess.SubprocessError):
            # Fall back to text parsing
            pass

        # Fallback to plain text output
        try:
            proc = subprocess.Popen(
                base_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"facter command failed: {stderr.decode()}")
            results = stdout.decode()
            if key is not None:
                return results.strip()
            return dict(_parse_cli_facter_results(results))
        except (FileNotFoundError, subprocess.SubprocessError):
            log.exception("Facter execution failed")
            raise

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
            f"<Facter cache_enabled={self.cache_enabled!r} "
            f"cache_active={self._cache is not None!r}>"
        )

    def json(self) -> str:
        """Return a json dump of all facts"""
        return json.dumps(self.all)


_FACTER = Facter()


def get_fact(fact: str, default: Any = None) -> Any:
    return _FACTER.get(fact, default)
