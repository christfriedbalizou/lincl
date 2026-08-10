"""
File: test_imports.py
Author: Christfried Balizou
Email: christfriedbalizou@gmail.com
Github: https://github.com/ChristfriedBalizou
Description: Test dynamic imports
"""

import pytest


def test_script_not_found():
    # Try importing a command which does not exist
    # should raise and ImportError
    with pytest.raises(ImportError, match="Script for foobar not found."):
        from lincl import foobar  # noqa: F401


def test_script_found():
    # Check import of an existing script works
    from lincl import ls

    assert callable(ls)


def test_script_found_with_alias():
    # Try to use alias "as"
    from lincl import cp as copy

    assert callable(copy)
