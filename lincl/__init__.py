"""
File: __init__.py
Author: Christfried Balizou
Email: christfriedbalizou@gmail.com
Github: https://github.com/ChristfriedBalizou
Description:
    This file aim to dynamically wrap linux commands to a pythonic version

    ```python

     from commands import cp as copy

     copy(src, dest, recusive=True, force=True)
     >> cp --recursive --force src dest

     from commands import machinectl

     machinectl("status", "my-container")
     >> machinectl status my-container
    ```

    This shoudl avoid passing complex usage of subprocess.
    Note that we are actually going to use subprocess here.

    This was implemented to solve a difficul experience having to call
    subprocess everywhere. In the aim to reduce that I choosed to implement
    this package

    NOTICE: from package import * # Is not supported
"""

__title__ = "lincl"
__version__ = "1.0.0"
__author__ = "Christfried BALIZOU"

import os
import shutil
import subprocess
from typing import Any, Callable, Dict, List


def __getattr__(name) -> Callable:
    """
    Executed whenever attribute is not found
    This will attempts to dynamically load attribute and return it
    """

    try:
        return command(name)
    except Exception:
        print(f"ERROR while attempting to dynamically load {name}:")
        raise


def __dir__():
    """
    Raise an error to avoid importing univers

    https://www.python.org/dev/peps/pep-0328/#rationale-for-parentheses
    (import * is not an option ;-)

    from package import * #  Is not supported
    """
    raise Exception("Specify the linux command you want to import.")


def command(name) -> Callable:
    """Load a given command name

    This will enforce and load the asked command and bound with controllers
    which will aim to controll the output and check the command executed
    correctly.

    """
    return loader(name)


def controller(func):
    def wrapper(*args: List[str], **kwargs: Dict[str, Any]):
        """Transcribe the command arguments to command line


        This will translate the arguments to Linux base command line

        Note: the presence of "popen" and "communicate", which will be
              forwarded to Popen
        """

        commands = [func()] + transcripte(*args, **kwargs)
        communicate = kwargs.pop("communicate", {})
        popen = kwargs.pop("popen", {})

        popen["stdout"] = subprocess.PIPE
        popen["stderr"] = subprocess.PIPE
        popen["universal_newlines"] = True

        with subprocess.Popen(commands, **popen) as process:
            stdout, stderr = process.communicate(**communicate)

            if process.returncode != 0:
                raise RuntimeError(f"{' '.join(commands)}\n\n{stderr}")

            return stdout, stderr

    return wrapper


def transcripte(*args: List[str], **kwargs: Dict[str, Any]) -> List[str]:
    """Transcribe args and kwargs to linux base schema

    ```
    transcripte("start", uid="foobar", read_only=True)
    >> --uid=foobar --read-only start
    ```

    Arguments:
        args: Interpreted as a Linux command commands or actions
        kwargs: Interpreted as Linux command options

    Return:
        Linux base commands and options representation
    """
    commands: List = []

    for option, value in kwargs.items():

        if len(option) == 1:
            option = f"-{option}"
        else:
            option = f"--{option}"

        option = option.replace("_", "-")
        # change snake_case python name to use minus

        if isinstance(value, bool):
            # We don't need to continue we can stop here
            commands.append(option)
        elif isinstance(value, list):
            # We will use comma separated list. Space separation is not
            # will not be supported
            commands.append("{}={}".format(option, ",".join(value)))
        else:
            commands.append(f"{option}={value}")

    for command in args:
        commands.append(command)

    return commands


def loader(method: str):
    """Load an executable program

    This will load the given Linux command through a subprocess.Popen
    and will return the output.

    Using shutil.which we want to find the executable script and
    make sure the script can be executed using os.X_OK.

    This is equivalent to:

    ```bash
    test -x $program || exit 0
    ```
    """
    script = shutil.which(method, mode=os.X_OK)

    if not script:
        raise ImportError(f"Script for {method} not found.")

    @controller
    def program(*args: List[str], **kwargs: Dict[str, str]):
        """Simply return the program path"""
        return script

    return program
