# Copyright (c) 2024, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

"""
Module for technical utilities.
"""
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
Supplier = Callable[[], T]


def require_not_none(obj: Any, msg: Optional[str] = None) -> None:
    """
    Raises a ValueError if obj is None.
    """
    if obj is None:
        error_msg = msg if msg else "Object must not be None"
        raise ValueError(error_msg)


def get_or_add(dictionary: Dict[K, V], key: K, default_factory: Supplier[V]) -> V:
    """
    Gets value from dictionary, or inserts it if it does not exist.

    Factory is only called if value is absent.
    """
    value = dictionary.get(key)
    if not value:
        value = default_factory()
        dictionary[key] = value
    return value
