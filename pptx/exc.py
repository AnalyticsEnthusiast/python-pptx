# encoding: utf-8

"""
Exceptions used with python-pptx.

The base exception class is PythonPptxError.
"""


class PythonPptxError(Exception):
    """Generic error class."""


class PackageNotFoundError(PythonPptxError):
    """
    Raised when a package cannot be found at the specified path.
    """
