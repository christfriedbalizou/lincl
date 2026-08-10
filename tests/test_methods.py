"""
File: test_methods.py
Author: Christfried Balizou
Email: christfriedbalizou@gmail.com
Github: https://github.com/ChristfriedBalizou
Description: Test dynamic loaded methods
"""

import os

import pytest

from lincl import cat, echo, touch


def test_return_code_none_zero():
    with pytest.raises(
        RuntimeError, match="foobar: No such file or directory"
    ):
        cat("foobar", show_tabs=True)


def test_return_code_zero():
    here = os.path.dirname(os.path.realpath(__file__))
    touch(os.path.join(here, "test_lincl.txt"), no_create=True)
    assert os.path.exists(os.path.join(here, "test_lincl.txt")) is False


def test_create_file():
    stdout, stderr = echo("Hey this is me")
    assert stdout.splitlines() == ["Hey this is me"]
    assert not stderr
