"""Integration tests using real facter executable."""

import subprocess

import pytest

from facter import Facter


def facter_available() -> bool:
    """Check if facter is available on the system."""
    try:
        result = subprocess.run(["facter", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def facter_supports_json() -> bool:
    """Check if facter supports JSON output."""
    try:
        result = subprocess.run(
            ["facter", "--json", "architecture"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not facter_available(), reason="facter not available")
class TestFacterIntegration:
    """Integration tests that require real facter."""

    def test_get_all_facts(self) -> None:
        """Test getting all facts from facter."""
        f = Facter()
        facts = f.all

        # Basic sanity checks
        assert isinstance(facts, dict)
        assert len(facts) > 0

        # These facts should exist on most systems
        common_facts = ["architecture", "kernel", "os"]
        for fact in common_facts:
            if fact in facts:
                assert isinstance(facts[fact], (str, dict, list, int, float, bool))

    def test_get_specific_fact(self) -> None:
        """Test getting a specific fact."""
        f = Facter()

        # Architecture should exist on all systems
        arch = f.lookup("architecture")
        assert isinstance(arch, str)
        assert len(arch) > 0

        # Test dictionary-style access
        arch2 = f["architecture"]
        assert arch == arch2

    def test_get_nonexistent_fact(self) -> None:
        """Test getting a fact that doesn't exist."""
        f = Facter()

        # Should raise KeyError for non-existent fact
        with pytest.raises(KeyError):
            f.lookup("nonexistent_fact_12345")

        # Should return default with get()
        result = f.get("nonexistent_fact_12345", "default")
        assert result == "default"

    def test_cache_behavior(self) -> None:
        """Test that caching works correctly."""
        f = Facter(cache_enabled=True)

        # First call should populate cache
        arch1 = f.lookup("architecture")
        assert f._cache is not None

        # Second call should use cache
        arch2 = f.lookup("architecture")
        assert arch1 == arch2

        # Force refresh should bypass cache
        arch3 = f.lookup("architecture", cache=False)
        assert arch1 == arch3  # Should be same value but fetched fresh

    def test_no_cache_behavior(self) -> None:
        """Test behavior with caching disabled."""
        f = Facter(cache_enabled=False)

        # Should not populate cache
        arch = f.lookup("architecture")
        assert f._cache is None
        assert isinstance(arch, str)

    @pytest.mark.skipif(not facter_supports_json(), reason="facter JSON not supported")
    def test_json_output_preference(self) -> None:
        """Test that JSON output is preferred when available."""
        f = Facter()
        facts = f.all

        # JSON output should provide properly typed values
        assert isinstance(facts, dict)

        # Look for facts that should be specific types in JSON
        if "uptime_seconds" in facts:
            assert isinstance(facts["uptime_seconds"], int)

        if "load_averages" in facts:
            assert isinstance(facts["load_averages"], dict)

    def test_external_facts_directory(self) -> None:
        """Test external facts directory functionality."""
        # Most systems won't have external facts, but the parameter should work
        f = Facter(external_dir="/nonexistent/path")

        # Should still work (facter handles non-existent external dirs gracefully)
        facts = f.all
        assert isinstance(facts, dict)

    def test_puppet_facts_option(self) -> None:
        """Test puppet facts option."""
        # This might not add facts on systems without Puppet, but should work
        f = Facter(get_puppet_facts=True)
        facts = f.all
        assert isinstance(facts, dict)

    def test_custom_facter_path(self) -> None:
        """Test custom facter path."""
        # Test with correct path
        f = Facter(facter_path="facter")
        arch = f.lookup("architecture")
        assert isinstance(arch, str)

        # Test with incorrect path should raise error
        f_bad = Facter(facter_path="/nonexistent/facter")
        with pytest.raises(RuntimeError):
            f_bad.lookup("architecture")

    def test_iterator_methods(self) -> None:
        """Test iterator methods work with real data."""
        f = Facter()

        # Test keys()
        keys = list(f.keys())
        assert len(keys) > 0
        assert "architecture" in keys or "kernel" in keys  # At least one should exist

        # Test values()
        values = list(f.values())
        assert len(values) == len(keys)

        # Test items()
        items = list(f.items())
        assert len(items) == len(keys)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in items)

    def test_json_method(self) -> None:
        """Test JSON serialization of facts."""
        import json

        f = Facter()
        json_str = f.json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert len(parsed) > 0
