from pathlib import Path
import os
import pytest

from tools import list_directory


def test_list_directory_normal():
    res = list_directory('.')
    assert res['ok'] is True
    assert 'items' in res and isinstance(res['items'], list)


@pytest.mark.parametrize("bad_path", [
    "..",
    "../",
    "../..",
    "../../",
    "..\\",  # Windows style
    "docs/../../../",
])
def test_list_directory_blocks_traversal_relative(bad_path):
    res = list_directory(bad_path)
    assert res['ok'] is False
    assert 'outside' in res.get('error', '').lower()


def test_list_directory_blocks_traversal_absolute():
    # Absolute root path (platform agnostic)
    abs_root = os.path.abspath(os.sep)
    res = list_directory(abs_root)
    assert res['ok'] is False
    assert 'outside' in res.get('error', '').lower()


def test_list_directory_non_directory():
    # Known file in backend directory
    res = list_directory('llm.py')
    assert res['ok'] is False
    assert 'not found' in res.get('error', '').lower()
