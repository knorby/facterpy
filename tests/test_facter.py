"""Basic tests to ensure the modernized code works."""

import subprocess
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

import pytest

from facter import Facter, _parse_cli_facter_results


def _completed(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> CompletedProcess[str]:
    """Build a CompletedProcess as subprocess.run would return."""
    return CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


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
    assert f.timeout == 30.0
    assert f._cache is None


def test_facter_init_custom_timeout() -> None:
    """Test Facter accepts a custom timeout."""
    f = Facter(timeout=5.0)
    assert f.timeout == 5.0


def test_facter_uses_yaml_deprecated() -> None:
    """Test deprecated yaml property and parameter."""
    # Test deprecated use_yaml parameter
    with patch("facter.log.warning") as mock_warning:
        Facter(use_yaml=True)
        mock_warning.assert_called_once()
        assert "deprecated" in mock_warning.call_args[0][0]

    # Test deprecated uses_yaml property
    with patch("facter.log.warning") as mock_warning:
        f = Facter()
        result = f.uses_yaml
        assert result is False
        mock_warning.assert_called_once()
        assert "deprecated" in mock_warning.call_args[0][0]


@patch("subprocess.run")
def test_run_facter_legacy_facts(mock_run: Mock) -> None:
    """Test that legacy_facts=True adds --show-legacy to command."""
    mock_run.return_value = _completed(stdout='{"architecture": "x86_64"}')

    # Test with legacy_facts=True
    f = Facter(legacy_facts=True)
    f.run_facter()

    # Check that --show-legacy was added to args
    args = mock_run.call_args[0][0]
    assert "--show-legacy" in args
    assert "--json" in args

    # Test with legacy_facts=False (default)
    mock_run.reset_mock()
    mock_run.return_value = _completed(stdout='{"architecture": "x86_64"}')
    f_no_legacy = Facter(legacy_facts=False)
    f_no_legacy.run_facter()

    # Check that --show-legacy was NOT added
    args = mock_run.call_args[0][0]
    assert "--show-legacy" not in args
    assert "--json" in args


@patch("subprocess.run")
def test_run_facter_json_success(mock_run: Mock) -> None:
    """Test successful JSON parsing."""
    mock_run.return_value = _completed(stdout='{"architecture": "x86_64"}')

    f = Facter()
    result = f.run_facter()
    assert result == {"architecture": "x86_64"}

    # Check that --json was added to args
    args = mock_run.call_args[0][0]
    assert "--json" in args


@patch("subprocess.run")
def test_run_facter_json_specific_fact(mock_run: Mock) -> None:
    """Test JSON parsing when a specific fact is requested."""
    mock_run.return_value = _completed(
        stdout='{"architecture": "x86_64", "kernel": "darwin"}'
    )

    f = Facter()
    result = f.run_facter("kernel")
    assert result == "darwin"
    assert "kernel" in mock_run.call_args[0][0]


@patch("subprocess.run")
def test_run_facter_fallback_to_text(mock_run: Mock) -> None:
    """Test fallback to text parsing when JSON fails."""
    # First call (JSON) fails, second call (text) succeeds
    mock_run.side_effect = [
        _completed(stderr="json not supported", returncode=1),
        _completed(stdout="architecture => x86_64\n"),
    ]

    f = Facter()
    result = f.run_facter()
    assert result == {"architecture": "x86_64"}


@patch("subprocess.run")
def test_run_facter_complete_failure(mock_run: Mock) -> None:
    """Test complete failure when both JSON and text fail."""
    mock_run.return_value = _completed(stderr="error message", returncode=1)

    f = Facter()
    with pytest.raises(RuntimeError, match="facter command failed"):
        f.run_facter()


@patch("subprocess.run")
def test_run_facter_timeout(mock_run: Mock) -> None:
    """Test that a facter timeout propagates instead of falling back."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="facter", timeout=30)

    f = Facter()
    with pytest.raises(subprocess.TimeoutExpired):
        f.run_facter()

    # Only the JSON attempt should have been made - no text fallback
    assert mock_run.call_count == 1


@patch("subprocess.run")
def test_run_facter_passes_timeout(mock_run: Mock) -> None:
    """Test that the configured timeout is passed to subprocess.run."""
    mock_run.return_value = _completed(stdout="{}")

    f = Facter(timeout=7.5)
    f.run_facter()
    assert mock_run.call_args.kwargs["timeout"] == 7.5


def test_facter_repr() -> None:
    """Test string representation."""
    f = Facter()
    repr_str = repr(f)
    assert "Facter" in repr_str
    assert "cache_enabled=" in repr_str
    assert "cache_active=" in repr_str
    # Should not contain yaml reference anymore
    assert "yaml=" not in repr_str
