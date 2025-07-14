"""Basic tests to ensure the modernized code works."""

import warnings
from unittest.mock import Mock, patch

import pytest

from facter import Facter, _parse_cli_facter_results


def test_parse_cli_facter_results() -> None:
    """Test the CLI parser function."""
    test_input = """foo => bar
baz => 1
foo_bar => True"""

    results = list(_parse_cli_facter_results(test_input))
    expected = [("foo", "bar"), ("baz", "1"), ("foo_bar", "True")]
    assert results == expected


def test_facter_init() -> None:
    """Test Facter initialization."""
    f = Facter()
    assert f.facter_path == "facter"
    assert f.cache_enabled is True
    assert f._cache is None


def test_facter_uses_yaml_deprecated() -> None:
    """Test deprecated yaml property and parameter."""
    # Test deprecated use_yaml parameter
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        f = Facter(use_yaml=True)
        assert len(w) == 1
        assert "deprecated" in str(w[0].message)

    # Test deprecated uses_yaml property
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        f = Facter()
        result = f.uses_yaml
        assert result is False
        assert len(w) == 1
        assert "deprecated" in str(w[0].message)


@patch("subprocess.Popen")
def test_run_facter_json_success(mock_popen: Mock) -> None:
    """Test successful JSON parsing."""
    mock_process = Mock()
    mock_process.communicate.return_value = (b'{"architecture": "x86_64"}', b"")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    f = Facter()
    result = f.run_facter()
    assert result == {"architecture": "x86_64"}

    # Check that --json was added to args
    args = mock_popen.call_args[0][0]
    assert "--json" in args


@patch("subprocess.Popen")
def test_run_facter_fallback_to_text(mock_popen: Mock) -> None:
    """Test fallback to text parsing when JSON fails."""
    # First call (JSON) fails, second call (text) succeeds
    mock_process_json = Mock()
    mock_process_json.communicate.return_value = (b"", b"json not supported")
    mock_process_json.returncode = 1

    mock_process_text = Mock()
    mock_process_text.communicate.return_value = (b"architecture => x86_64\n", b"")
    mock_process_text.returncode = 0

    mock_popen.side_effect = [mock_process_json, mock_process_text]

    f = Facter()
    result = f.run_facter()
    assert result == {"architecture": "x86_64"}


@patch("subprocess.Popen")
def test_run_facter_complete_failure(mock_popen: Mock) -> None:
    """Test complete failure when both JSON and text fail."""
    mock_process = Mock()
    mock_process.communicate.return_value = (b"", b"error message")
    mock_process.returncode = 1
    mock_popen.return_value = mock_process

    f = Facter()
    with pytest.raises(RuntimeError, match="facter command failed"):
        f.run_facter()


def test_facter_repr() -> None:
    """Test string representation."""
    f = Facter()
    repr_str = repr(f)
    assert "Facter" in repr_str
    assert "cache_enabled=" in repr_str
    assert "cache_active=" in repr_str
    # Should not contain yaml reference anymore
    assert "yaml=" not in repr_str
