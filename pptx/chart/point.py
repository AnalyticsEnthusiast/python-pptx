# encoding: utf-8

"""
Data point-related objects.
"""

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from collections import Sequence


class _BasePoints(Sequence):
    """
    Sequence providing access to the individual data points in a series.
    """
    def __init__(self, ser):
        super(_BasePoints, self).__init__()
        self._element = ser
        self._ser = ser

    def __getitem__(self, idx):
        raise NotImplementedError


class BubblePoints(_BasePoints):
    """
    Sequence providing access to the individual data points in a series.
    """
    def __len__(self):
        return min(
            self._ser.xVal_ptCount_val,
            self._ser.yVal_ptCount_val,
            self._ser.bubbleSize_ptCount_val
        )


class XyPoints(_BasePoints):
    """
    Sequence providing access to the individual data points in a series.
    """
    def __len__(self):
        return min(self._ser.xVal_ptCount_val, self._ser.yVal_ptCount_val)
