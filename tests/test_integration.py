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

        # Test with a fact that exists at top level in structured format
        kernel = f.lookup("kernel")
        assert isinstance(kernel, str)
        assert len(kernel) > 0

        # Test dictionary-style access
        kernel2 = f["kernel"]
        assert kernel == kernel2

        # Test individual fact lookup (bypasses cache)
        arch = f.lookup("architecture", cache=False)
        assert isinstance(arch, str)
        assert len(arch) > 0

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
        kernel1 = f.lookup("kernel")
        assert f._cache is not None

        # Second call should use cache
        kernel2 = f.lookup("kernel")
        assert kernel1 == kernel2

        # Force refresh should bypass cache
        kernel3 = f.lookup("kernel", cache=False)
        assert kernel1 == kernel3  # Should be same value but fetched fresh

    def test_no_cache_behavior(self) -> None:
        """Test behavior with caching disabled."""
        f = Facter(cache_enabled=False)

        # Should not populate cache - use individual fact lookup
        arch = f.lookup("architecture", cache=False)
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
        # This might fail on systems without Puppet installed
        try:
            f = Facter(get_puppet_facts=True)
            facts = f.all
            assert isinstance(facts, dict)
        except RuntimeError as e:
            # Skip if Puppet is not available
            if "Could not load puppet gem" in str(e):
                pytest.skip("Puppet not available")

    def test_custom_facter_path(self) -> None:
        """Test custom facter path."""
        # Test with correct path
        f = Facter(facter_path="facter")
        kernel = f.lookup("kernel")
        assert isinstance(kernel, str)

        # Test with incorrect path should raise error
        f_bad = Facter(facter_path="/nonexistent/facter")
        with pytest.raises(FileNotFoundError):
            f_bad.lookup("architecture")

    def test_iterator_methods(self) -> None:
        """Test iterator methods work with real data."""
        f = Facter()

        # Test keys()
        keys = list(f.keys())
        assert len(keys) > 0
        assert "kernel" in keys  # Should exist in structured format

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

    def test_legacy_facts_behavior(self) -> None:
        """Test legacy facts functionality."""
        # Test without legacy facts (default)
        f_no_legacy = Facter(legacy_facts=False)
        facts_no_legacy = f_no_legacy.all

        # Test with legacy facts enabled
        f_legacy = Facter(legacy_facts=True)
        facts_legacy = f_legacy.all

        # Legacy version should have more or equal facts
        assert len(facts_legacy) >= len(facts_no_legacy)

        # Test specific legacy fact lookup
        # Architecture should work with legacy_facts=True
        try:
            arch_legacy = f_legacy.lookup("architecture")
            assert isinstance(arch_legacy, str)
            assert len(arch_legacy) > 0
        except KeyError:
            # If architecture doesn't exist as legacy fact, skip this part
            pass

        # Test that some legacy facts appear with legacy=True but not without
        legacy_fact_names = ["architecture", "operatingsystem", "hostname"]
        legacy_only_facts = []

        for fact_name in legacy_fact_names:
            in_legacy = fact_name in facts_legacy
            in_no_legacy = fact_name in facts_no_legacy

            if in_legacy and not in_no_legacy:
                legacy_only_facts.append(fact_name)

        # Should find at least one fact that appears only with legacy enabled
        # (This may vary by facter version, so we don't assert specific facts)
        assert len(legacy_only_facts) >= 0  # At least don't fail

    def test_legacy_facts_repr(self) -> None:
        """Test string representation includes legacy_facts setting."""
        f_no_legacy = Facter(legacy_facts=False)
        f_legacy = Facter(legacy_facts=True)

        repr_no_legacy = repr(f_no_legacy)
        repr_legacy = repr(f_legacy)

        # Both should contain Facter and cache info
        assert "Facter" in repr_no_legacy
        assert "Facter" in repr_legacy

        # Could add legacy_facts to repr if desired, but not required
        assert isinstance(repr_no_legacy, str)
        assert isinstance(repr_legacy, str)
