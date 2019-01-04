#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
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

import logging
from typing import Any, Dict

from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from noisicaa import core
from noisicaa import model
from noisicaa import music
from noisicaa.ui import ui_base
from noisicaa.ui import instrument_library
from . import base_node

logger = logging.getLogger(__name__)


class InstrumentNodeWidget(ui_base.ProjectMixin, QtWidgets.QScrollArea):
    def __init__(self, node: music.Instrument, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__node = node

        self.__listeners = {}  # type: Dict[str, core.Listener]

        body = QtWidgets.QWidget(self)
        body.setAutoFillBackground(False)
        body.setAttribute(Qt.WA_NoSystemBackground, True)

        select_instrument = QtWidgets.QToolButton(self)
        select_instrument.setIcon(QtGui.QIcon.fromTheme('document-open'))
        select_instrument.setAutoRaise(True)
        select_instrument.clicked.connect(lambda: self.call_async(self.__selectInstrument()))

        self.__instrument = QtWidgets.QLineEdit(self)
        self.__instrument.setReadOnly(True)
        if self.__node.instrument_uri is not None:
            self.__instrument.setText(self.__node.instrument_uri)
        else:
            self.__instrument.setText('---')

        self.__listeners['instrument_uri'] = (
            self.__node.instrument_uri_changed.add(self.__instrumentURIChanged))

        layout = QtWidgets.QFormLayout()
        layout.setVerticalSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        instrument_layout = QtWidgets.QHBoxLayout()
        instrument_layout.addWidget(select_instrument)
        instrument_layout.addWidget(self.__instrument, 1)

        layout.addRow("Instrument:", instrument_layout)
        body.setLayout(layout)

        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setWidget(body)

    def cleanup(self) -> None:
        for listener in self.__listeners.values():
            listener.remove()
        self.__listeners.clear()

    def __instrumentURIChanged(self, change: model.PropertyValueChange[str]) -> None:
        if change.new_value is not None:
            self.__instrument.setText(change.new_value)
        else:
            self.__instrument.setText('---')

    def __instrumentURIEdited(self, instrument_uri: str) -> None:
        if instrument_uri != self.__node.instrument_uri:
            self.send_command_async(music.Command(
                target=self.__node.id,
                update_instrument=music.UpdateInstrument(
                    instrument_uri=instrument_uri)))

    async def __selectInstrument(self) -> None:
        dialog = instrument_library.InstrumentLibraryDialog(
            context=self.context, selectButton=True, parent=self.editor_window)
        dialog.setWindowTitle("Select instrument")
        dialog.setModal(True)
        dialog.finished.connect(lambda _: self.__selectInstrumentClosed(dialog))
        await dialog.setup()
        if self.__node.instrument_uri is not None:
            dialog.selectInstrument(self.__node.instrument_uri)
        dialog.show()

    def __selectInstrumentClosed(
            self, dialog: instrument_library.InstrumentLibraryDialog) -> None:
        if dialog.result() == dialog.Accepted:
            instrument = dialog.instrument()
            if instrument is not None:
                self.__instrumentURIEdited(instrument.uri)
        self.call_async(dialog.cleanup())


class InstrumentNode(base_node.Node):
    def __init__(self, *, node: music.BasePipelineGraphNode, **kwargs: Any) -> None:
        assert isinstance(node, music.Instrument), type(node).__name__
        self.__widget = None  # type: InstrumentNodeWidget
        self.__node = node  # type: music.Instrument

        super().__init__(node=node, **kwargs)

    def cleanup(self) -> None:
        if self.__widget is not None:
            self.__widget.cleanup()
        super().cleanup()

    def createBodyWidget(self) -> QtWidgets.QWidget:
        assert self.__widget is None
        self.__widget = InstrumentNodeWidget(node=self.__node, context=self.context)
        return self.__widget
