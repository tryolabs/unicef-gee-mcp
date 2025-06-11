"""
Test script to check that the following work, for developers of this template:
- the python interpreter is selected
- imports are sorted
- absolute imports of the current project work
- types are checked
- linter warnings are shown
- formatting works and is applied on save

Remove this file when you start a new project from this template.
"""
import os
import pathlib
from datetime import datetime

from project_base.src import a

a()


def func(a: int) -> float:
    return datetime.now()


print(func("str"))
