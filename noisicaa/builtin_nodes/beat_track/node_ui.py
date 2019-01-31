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

from typing import Any, Dict
import logging
import os.path

from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from PyQt5 import QtSvg

from noisicaa.constants import DATA_DIR
from noisicaa import core
from noisicaa import model
from noisicaa import music
from noisicaa.ui.graph import track_node
from noisicaa.ui import ui_base
from . import commands
from . import client_impl

logger = logging.getLogger(__name__)


class BeatTrackWidget(ui_base.ProjectMixin, QtWidgets.QScrollArea):
    def __init__(self, track: client_impl.BeatTrack, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__track = track

        self.__listeners = {}  # type: Dict[str, core.Listener]

        body = QtWidgets.QWidget(self)
        body.setAutoFillBackground(False)
        body.setAttribute(Qt.WA_NoSystemBackground, True)

        self.__pitch = QtWidgets.QLineEdit(body)
        self.__pitch.editingFinished.connect(self.__pitchEdited)
        self.__pitch.setText(str(self.__track.pitch))
        self.__listeners['track:pitch'] = (
            self.__track.pitch_changed.add(self.__pitchChanged))

        layout = QtWidgets.QFormLayout()
        layout.setVerticalSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow("Pitch:", self.__pitch)
        body.setLayout(layout)

        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setWidget(body)

    def cleanup(self) -> None:
        for listener in self.__listeners.values():
            listener.remove()
        self.__listeners.clear()

    def __pitchChanged(self, change: model.PropertyValueChange[str]) -> None:
        self.__pitch.setText(str(change.new_value))

    def __pitchEdited(self) -> None:
        try:
            pitch = model.Pitch(self.__pitch.text())
        except ValueError:
            self.__pitch.setText(str(self.__track.pitch))
        else:
            if pitch != self.__track.pitch:
                self.send_command_async(commands.update(
                    self.__track,
                    set_pitch=pitch))


class BeatTrackNode(track_node.TrackNode):
    def __init__(self, node: music.BaseNode, **kwargs: Any) -> None:
        assert isinstance(node, client_impl.BeatTrack)
        self.__widget = None  # type: BeatTrackWidget
        self.__track = node  # type: client_impl.BeatTrack

        super().__init__(
            node=node,
            icon=QtSvg.QSvgRenderer(os.path.join(DATA_DIR, 'icons', 'track-type-beat.svg')),
            **kwargs)

    def cleanup(self) -> None:
        if self.__widget is not None:
            self.__widget.cleanup()
        super().cleanup()

    def createBodyWidget(self) -> QtWidgets.QWidget:
        assert self.__widget is None
        self.__widget = BeatTrackWidget(track=self.__track, context=self.context)
        return self.__widget