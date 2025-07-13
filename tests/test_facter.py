"""Basic tests to ensure the modernized code works."""
import pytest
from unittest.mock import Mock, patch
from facter import Facter, _parse_cli_facter_results


def test_parse_cli_facter_results():
    """Test the CLI parser function."""
    test_input = """foo => bar
baz => 1
foo_bar => True"""
    
    results = list(_parse_cli_facter_results(test_input))
    expected = [('foo', 'bar'), ('baz', '1'), ('foo_bar', 'True')]
    assert results == expected


def test_facter_init():
    """Test Facter initialization."""
    f = Facter()
    assert f.facter_path == "facter"
    assert f.cache_enabled is True
    assert f._cache is None


def test_facter_uses_yaml():
    """Test yaml detection."""
    f = Facter(use_yaml=True)
    # Should return True/False based on yaml availability
    assert isinstance(f.uses_yaml, bool)


@patch('subprocess.Popen')
def test_run_facter_error_handling(mock_popen):
    """Test error handling in run_facter."""
    mock_process = Mock()
    mock_process.communicate.return_value = (b'', b'error message')
    mock_process.returncode = 1
    mock_popen.return_value = mock_process
    
    f = Facter()
    with pytest.raises(RuntimeError, match="facter command failed"):
        f.run_facter()


def test_facter_repr():
    """Test string representation."""
    f = Facter()
    repr_str = repr(f)
    assert "Facter" in repr_str
    assert "yaml=" in repr_str
    assert "cache_enabled=" in repr_str