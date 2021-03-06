#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2019, Benjamin Niemann <pink@odahoda.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# @end:license

import fractions
import functools
import logging
import operator
import typing
from typing import Any, Dict, Tuple, Type, Callable, TypeVar

from PyQt5 import QtCore

from . import ui_base

logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    QObjectMixin = QtCore.QObject
else:
    QObjectMixin = object


class SlotContainer(QObjectMixin):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self._slots = {}  # type: Dict[str, Any]


_type = type

T = TypeVar('T')
def slot(
        type: Type[T],  # pylint: disable=redefined-builtin
        name: str,
        *,
        default: T = None,
        equality: Callable = None,
        allow_none: bool = False
) -> Tuple[Callable[[SlotContainer], T], Callable[[SlotContainer, T], None], QtCore.pyqtSignal]:
    assert isinstance(type, _type), type
    if equality is None:
        if type in (int, float, bool, str, fractions.Fraction):
            equality = operator.eq
        else:
            equality = operator.is_

    # Create the signal with generic 'object' type, to bypass Qt's typechecking, which is too
    # restrictive for my taste. E.g. it doesn't accept None otherwise. Instead we're doing our own
    # typechecking in the setter method.
    signal = QtCore.pyqtSignal(object)

    def getter(self: SlotContainer) -> T:
        return self._slots.get(name, default)

    def setter(self: SlotContainer, value: T) -> None:
        if value is None and allow_none:
            pass
        elif not isinstance(value, type):
            raise TypeError("Expected %s, got %s" % (type.__name__, _type(value).__name__))

        current_value = self._slots.get(name, default)
        if not equality(value, current_value):
            logger.debug("Slot %s on %s set to %s", name, self, value)
            self._slots[name] = value
            sig_inst = signal.__get__(self)
            sig_inst.emit(value)

    return getter, setter, signal


class SlotConnectionManager(ui_base.ProjectMixin, object):
    def __init__(self, *, session_prefix: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__session_prefix = session_prefix
        self.__connections = {}  # type: Dict[str, Tuple[QtCore.pyqtBoundSignal, QtCore.pyqtConnection]]

    def cleanup(self) -> None:
        while self.__connections:
            _, (signal, connection) = self.__connections.popitem()
            signal.disconnect(connection)

    def connect(
            self,
            name: str,
            setter: Callable[[T], None],
            signal: QtCore.pyqtBoundSignal,
            default: T = None,
    ) -> None:
        value = self.get_session_value(self.__session_prefix + ':' + name, default)
        if value is not None:
            setter(value)
        connection = signal.connect(functools.partial(self.__valueChanged, name))
        self.__connections[name] = (signal, connection)

    def disconnect(self, name: str) -> None:
        signal, connection = self.__connections.pop(name)
        signal.disconnect(connection)

    def __valueChanged(self, name: str, value: T) -> None:
        self.set_session_value(self.__session_prefix + ':' + name, value)
