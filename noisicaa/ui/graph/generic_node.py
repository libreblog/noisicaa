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

import logging
from typing import Any, Optional, List

from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets

from noisicaa import core
from noisicaa import value_types
from noisicaa import music
from noisicaa import node_db
from noisicaa.ui import ui_base
from noisicaa.ui import slots
from noisicaa.ui import control_value_dial
from noisicaa.ui import control_value_connector

from . import base_node

logger = logging.getLogger(__name__)


class ControlValueEnum(slots.SlotContainer, QtWidgets.QComboBox):
    value, setValue, valueChanged = slots.slot(float, 'value', default=0.0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.valueChanged.connect(lambda _: self.__valueChanged())
        self.currentIndexChanged.connect(lambda _: self.__currentIndexChanged())

    def __valueChanged(self) -> None:
        closest_idx = None  # type: int
        closest_dist = None  # type: float
        for idx in range(self.count()):
            value = self.itemData(idx)
            dist = abs(value - self.value())
            if closest_idx is None or dist < closest_dist:
                closest_idx = idx
                closest_dist = dist

        if closest_idx is not None:
            self.setCurrentIndex(closest_idx)

    def __currentIndexChanged(self) -> None:
        self.setValue(self.currentData())


class ControlValueWidget(control_value_connector.ControlValueConnector):
    def __init__(
            self, *,
            node: music.BaseNode, port: node_db.PortDescription,
            parent: Optional[QtWidgets.QWidget],
            **kwargs: Any) -> None:
        super().__init__(node=node, name=port.name, **kwargs)

        self.__node = node
        self.__port = port

        listener = self.__node.port_properties_changed.add(
            self.__portPropertiesChanged)
        self.add_cleanup_function(listener.remove)

        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        port_properties = self.__node.get_port_properties(self.__port.name)

        if self.__port.WhichOneof('value') == 'float_value':
            self.__dial = control_value_dial.ControlValueDial(parent)
            self.__dial.setDisabled(port_properties.exposed)
            self.__dial.setRange(self.__port.float_value.min, self.__port.float_value.max)
            self.__dial.setDefault(self.__port.float_value.default)
            if self.__port.float_value.scale == node_db.FloatValueDescription.LOG:
                self.__dial.setLogScale(True)
            self.connect(self.__dial.valueChanged, self.__dial.setValue)

            self.__exposed = QtWidgets.QCheckBox(parent)
            self.__exposed.setChecked(port_properties.exposed)
            self.__exposed.toggled.connect(self.__exposedEdited)

            layout.addWidget(self.__exposed)
            layout.addWidget(self.__dial)

        elif self.__port.WhichOneof('value') == 'enum_value':
            self.__enum = ControlValueEnum(parent=parent)
            for item in self.__port.enum_value.items:
                self.__enum.addItem(item.name, item.value)
            self.connect(self.__enum.valueChanged, self.__enum.setValue)

            layout.addWidget(self.__enum)

        layout.addStretch(1)

        self.__widget = QtWidgets.QWidget(parent)
        self.__widget.setLayout(layout)

    def label(self) -> str:
        return self.__port.display_name + ":"

    def widget(self) -> QtWidgets.QWidget:
        return self.__widget

    def __exposedEdited(self, exposed: bool) -> None:
        port_properties = self.__node.get_port_properties(self.__port.name)
        if port_properties.exposed == exposed:
            return

        if not exposed:
            with self.project.apply_mutations(
                    '%s: Unexpose port "%s"' % (self.__node.name, self.__port.name)):
                self.__node.set_port_properties(value_types.NodePortProperties(
                    name=self.__port.name,
                    exposed=False))

        else:
            with self.project.apply_mutations(
                    '%s: Expose port "%s"' % (self.__node.name, self.__port.name)):
                for conn in self.__node.connections:
                    if conn.dest_port == self.__port.name or conn.source_port == self.__port.name:
                        self.project.remove_node_connection(conn)

                self.__node.set_port_properties(value_types.NodePortProperties(
                    name=self.__port.name,
                    exposed=True))

        self.__dial.setDisabled(exposed)

    def __portPropertiesChanged(self, change: music.PropertyListChange) -> None:
        if self.__port.WhichOneof('value') == 'float_value':
            port_properties = self.__node.get_port_properties(self.__port.name)
            self.__exposed.setChecked(port_properties.exposed)
            self.__dial.setDisabled(port_properties.exposed)


class GenericNodeWidget(ui_base.ProjectMixin, core.AutoCleanupMixin, QtWidgets.QWidget):
    def __init__(self, node: music.BaseNode, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__node = node
        self.__node.control_value_map.init()

        self.__control_value_widgets = []  # type: List[ControlValueWidget]
        self.__control_value_form = None  # type: QtWidgets.QWidget

        self.__main_layout = QtWidgets.QVBoxLayout()
        self.__main_layout.setSpacing(0)
        self.__main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__main_layout)

        self.__setupControlValueForm()
        listener = self.__node.description_changed.add(
            lambda *_: self.__setupControlValueForm())
        self.add_cleanup_function(listener.remove)

        self.add_cleanup_function(self.__cleanupControlValueForm)

    def __cleanupControlValueForm(self) -> None:
        if self.__control_value_form is not None:
            self.__main_layout.removeWidget(self.__control_value_form)
            self.__control_value_form.setParent(None)
            self.__control_value_form = None

        for widget in self.__control_value_widgets:
            widget.cleanup()
        self.__control_value_widgets.clear()

    def __setupControlValueForm(self) -> None:
        self.__cleanupControlValueForm()

        form = QtWidgets.QWidget()
        form.setAutoFillBackground(False)
        form.setAttribute(Qt.WA_NoSystemBackground, True)

        layout = QtWidgets.QFormLayout()
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setVerticalSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        form.setLayout(layout)

        for port in self.__node.description.ports:
            if (port.direction == node_db.PortDescription.INPUT
                    and set(port.types) & {
                        node_db.PortDescription.KRATE_CONTROL,
                        node_db.PortDescription.ARATE_CONTROL}):
                widget = ControlValueWidget(
                    node=self.__node,
                    port=port,
                    parent=form,
                    context=self.context)
                self.__control_value_widgets.append(widget)
                layout.addRow(widget.label(), widget.widget())

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(form)

        self.__control_value_form = scroll
        self.__main_layout.addWidget(self.__control_value_form)



class GenericNode(base_node.Node):
    def __init__(self, *, node: music.BaseNode, **kwargs: Any) -> None:
        super().__init__(node=node, **kwargs)

    def createBodyWidget(self) -> QtWidgets.QWidget:
        widget = GenericNodeWidget(node=self.node(), context=self.context)
        self.add_cleanup_function(widget.cleanup)
        return widget
