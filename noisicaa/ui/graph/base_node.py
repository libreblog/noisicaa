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

import functools
import logging
import os.path
from typing import cast, Any, Optional, Dict, List, Iterable

from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtSvg
from PyQt5 import QtWidgets

from noisicaa import constants
from noisicaa import audioproc
from noisicaa import core
from noisicaa import value_types
from noisicaa import music
from noisicaa import node_db
from noisicaa.ui import ui_base
from noisicaa.ui import mute_button

logger = logging.getLogger(__name__)


port_colors = {
    node_db.PortDescription.UNDEFINED: QtGui.QColor(150, 150, 150),
    node_db.PortDescription.AUDIO: QtGui.QColor(100, 255, 100),
    node_db.PortDescription.ARATE_CONTROL: QtGui.QColor(100, 255, 180),
    node_db.PortDescription.KRATE_CONTROL: QtGui.QColor(100, 180, 255),
    node_db.PortDescription.EVENTS: QtGui.QColor(255, 180, 100),
}


class SelectColorAction(QtWidgets.QWidgetAction):
    colorSelected = QtCore.pyqtSignal(value_types.Color)

    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)

        self.setDefaultWidget(SelectColorWidget(parent=parent, action=self))


class ColorBox(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def __init__(self, color: value_types.Color, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.__color = color

        self.setFixedSize(24, 24)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QtGui.QPainter(self)
        try:
            painter.fillRect(self.rect(), Qt.black)
            painter.fillRect(self.rect().adjusted(1, 1, -1, -1), Qt.white)
            painter.fillRect(self.rect().adjusted(2, 2, -2, -2), QtGui.QColor.fromRgbF(
                self.__color.r,
                self.__color.g,
                self.__color.b,
                self.__color.a))

        finally:
            painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class SelectColorWidget(QtWidgets.QWidget):
    colors = [
        value_types.Color(0.7, 0.7, 0.7),
        value_types.Color(0.8, 0.8, 0.8),
        value_types.Color(0.9, 0.9, 0.9),
        value_types.Color(1.0, 1.0, 1.0),

        value_types.Color(1.0, 0.6, 0.6),
        value_types.Color(1.0, 0.7, 0.7),
        value_types.Color(1.0, 0.8, 0.8),
        value_types.Color(1.0, 0.9, 0.9),

        value_types.Color(1.0, 0.6, 0.1),
        value_types.Color(1.0, 0.7, 0.3),
        value_types.Color(1.0, 0.8, 0.6),
        value_types.Color(1.0, 0.9, 0.8),

        value_types.Color(0.6, 1.0, 0.6),
        value_types.Color(0.7, 1.0, 0.7),
        value_types.Color(0.8, 1.0, 0.8),
        value_types.Color(0.9, 1.0, 0.9),

        value_types.Color(0.6, 0.6, 1.0),
        value_types.Color(0.7, 0.7, 1.0),
        value_types.Color(0.8, 0.8, 1.0),
        value_types.Color(0.9, 0.9, 1.0),

        value_types.Color(1.0, 0.6, 1.0),
        value_types.Color(1.0, 0.7, 1.0),
        value_types.Color(1.0, 0.8, 1.0),
        value_types.Color(1.0, 0.9, 1.0),

        value_types.Color(1.0, 1.0, 0.6),
        value_types.Color(1.0, 1.0, 0.7),
        value_types.Color(1.0, 1.0, 0.8),
        value_types.Color(1.0, 1.0, 0.9),

        value_types.Color(0.6, 1.0, 1.0),
        value_types.Color(0.7, 1.0, 1.0),
        value_types.Color(0.8, 1.0, 1.0),
        value_types.Color(0.9, 1.0, 1.0),
    ]

    def __init__(self, *, action: SelectColorAction, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__action = action

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        layout.setSpacing(2)
        self.setLayout(layout)

        for idx, color in enumerate(self.colors):
            w = ColorBox(color, self)
            w.clicked.connect(functools.partial(self.__action.colorSelected.emit, color))
            layout.addWidget(w, idx // 8, idx % 8)


class NodeProps(QtCore.QObject):
    contentRectChanged = QtCore.pyqtSignal(QtCore.QRectF)
    canvasLayoutChanged = QtCore.pyqtSignal()


class Title(QtWidgets.QGraphicsSimpleTextItem):
    def __init__(self, name: str, parent: 'Node') -> None:
        super().__init__(parent)

        self.setText(name)
        self.setFlag(QtWidgets.QGraphicsItem.ItemClipsToShape, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.__width = None  # type: float

    def boundingRect(self) -> QtCore.QRectF:
        bounding_rect = super().boundingRect()
        if self.__width is not None:
            bounding_rect.setWidth(self.__width)
        return bounding_rect

    def shape(self) -> QtGui.QPainterPath:
        shape = QtGui.QPainterPath()
        shape.addRect(self.boundingRect())
        return shape

    def setWidth(self, width: float) -> None:
        self.__width = width


class Box(QtWidgets.QGraphicsPathItem):
    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        # swallow mouse press events (which aren't handled by some other of the
        # node's items) to prevent the canvas from triggering a rubber band
        # selection.
        event.accept()


class NodeIcon(QtWidgets.QGraphicsItem):
    def __init__(self, icon: QtSvg.QSvgRenderer, parent: QtWidgets.QGraphicsItem) -> None:
        super().__init__(parent)

        self.__icon = icon
        self.__size = QtCore.QSizeF()
        self.__pixmap = None  # type: QtGui.QPixmap

    def setRect(self, rect: QtCore.QRectF) -> None:
        self.prepareGeometryChange()
        self.setPos(rect.topLeft())
        self.__size = rect.size()

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(QtCore.QPointF(), self.__size)

    def paint(
            self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem,
            widget: Optional[QtWidgets.QWidget] = None) -> None:
        size = min(self.__size.width(), self.__size.height())
        size = int(size - 0.4 * max(0, size - 50))

        if size < 10:
            return

        pixmap_size = QtCore.QSize(size, size)
        if self.__pixmap is None or self.__pixmap.size() != pixmap_size:
            self.__pixmap = QtGui.QPixmap(pixmap_size)
            self.__pixmap.fill(QtGui.QColor(0, 0, 0, 0))
            pixmap_painter = QtGui.QPainter(self.__pixmap)
            try:
                self.__icon.render(pixmap_painter, QtCore.QRectF(0, 0, size, size))
            finally:
                pixmap_painter.end()

        painter.setOpacity(min(0.8, max(0.2, 0.8 - (size - 30) / 100)))
        painter.drawPixmap(
            int((self.__size.width() - size) / 2),
            int((self.__size.height() - size) / 2),
            self.__pixmap)


class PortLabel(QtWidgets.QGraphicsRectItem):
    def __init__(self, port: 'Port') -> None:
        super().__init__()

        self.setZValue(100000)

        self.__text = QtWidgets.QGraphicsSimpleTextItem(self)
        tooltip = '%s: ' % port.name()

        tooltip += '/'.join(
            {
                node_db.PortDescription.AUDIO: "audio",
                node_db.PortDescription.KRATE_CONTROL: "k-rate control",
                node_db.PortDescription.ARATE_CONTROL: "a-rate control",
                node_db.PortDescription.EVENTS: "event",
            }[port_type]
            for port_type in port.possible_types())

        tooltip += {
            node_db.PortDescription.INPUT: " input",
            node_db.PortDescription.OUTPUT: " output",
        }[port.direction()]

        self.__text.setText(tooltip)
        self.__text.setPos(4, 2)

        text_box = self.__text.boundingRect()

        pen = QtGui.QPen()
        pen.setColor(Qt.black)
        pen.setWidth(1)
        self.setPen(pen)
        self.setBrush(QtGui.QColor(255, 255, 200))
        self.setRect(0, 0, text_box.width() + 8, text_box.height() + 4)


class Port(QtWidgets.QGraphicsPathItem):
    def __init__(self, port_desc: node_db.PortDescription, parent: 'Node') -> None:
        super().__init__(parent)

        self.__desc = port_desc
        self.__node = parent.node()

        self.__listeners = core.ListenerList()

        self.__listeners.add(
            self.__node.connections_changed.add(lambda _: self.__update()))

        self.__target_type = None  # type: node_db.PortDescription.Type
        self.__highlighted = False

        self.__tooltip = None  # type: PortLabel

    def setup(self) -> None:
        self.__tooltip = PortLabel(self)
        self.scene().addItem(self.__tooltip)

        self.__update()

    def cleanup(self) -> None:
        if self.__tooltip is not None:
            self.scene().removeItem(self.__tooltip)
            self.__tooltip = None

        self.__listeners.cleanup()

    def name(self) -> str:
        return self.__desc.name

    def direction(self) -> node_db.PortDescription.Direction:
        return self.__desc.direction

    def current_type(self) -> node_db.PortDescription.Type:
        return self.__node.get_current_port_type(self.__desc.name)

    def possible_types(self) -> List['node_db.PortDescription.Type']:
        return self.__node.get_possible_port_types(self.__desc.name)

    def node(self) -> 'Node':
        return cast(Node, self.parentItem())

    def highlighted(self) -> bool:
        return self.__highlighted

    def setHighlighted(self, highlighted: bool) -> None:
        self.__highlighted = highlighted
        self.__update()

    def setTargetType(self, target_type: node_db.PortDescription.Type) -> None:
        if self.__target_type == target_type:
            return

        self.__target_type = target_type
        self.__update()

    def clearTargetType(self) -> None:
        if self.__target_type is None:
            return

        self.__target_type = None
        self.__update()

    def canConnectTo(self, port: 'Port') -> bool:
        return music.can_connect_ports(
            self.__node, self.__desc.name,
            port.__node, port.__desc.name)

    def preferredConnectionType(self, port: 'Port') -> node_db.PortDescription.Type:
        return music.get_preferred_connection_type(
            self.__node, self.__desc.name,
            port.__node, port.__desc.name)

    def handleScenePos(self) -> QtCore.QPointF:
        if not self.isVisible():
            return self.scenePos()
        elif self.__desc.direction == node_db.PortDescription.INPUT:
            return self.scenePos() + QtCore.QPointF(-10, 0)
        else:
            return self.scenePos() + QtCore.QPointF(10, 0)

    def descriptionChanged(self, port_desc: node_db.PortDescription) -> None:
        self.__desc = port_desc
        self.__update()

    def __update(self) -> None:
        color = port_colors[self.__target_type or self.current_type()]

        if self.__highlighted:
            self.setOpacity(1.0)

            self.__tooltip.setVisible(self.__highlighted)
            ttpos = self.scenePos()
            ttpos += QtCore.QPointF(0, -self.__tooltip.boundingRect().height() / 2)
            if self.__desc.direction == node_db.PortDescription.OUTPUT:
                ttpos += QtCore.QPointF(20, 0)
            else:
                ttpos -= QtCore.QPointF(20 + self.__tooltip.boundingRect().width(), 0)
            self.__tooltip.setPos(ttpos)

        else:
            self.setOpacity(0.7)
            self.__tooltip.setVisible(False)

        if self.__highlighted or self.__target_type is not None:
            pen = QtGui.QPen()
            pen.setColor(Qt.red)
            pen.setWidth(2)
            self.setPen(pen)
            self.setBrush(color)
            rect = QtCore.QRectF(-15, -12, 30, 24)

        else:
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(80, 80, 200))
            pen.setWidth(1)
            self.setPen(pen)
            self.setBrush(color)
            rect = QtCore.QRectF(-10, -8, 20, 16)

        path = QtGui.QPainterPath()
        if self.__desc.direction == node_db.PortDescription.INPUT:
            path.moveTo(0, rect.top())
            path.arcTo(rect, 90, 180)

        else:
            path.moveTo(0, rect.top())
            path.arcTo(rect, 90, -180)

        self.setPath(path)


class Node(ui_base.ProjectMixin, core.AutoCleanupMixin, QtWidgets.QGraphicsItem):
    __next_zvalue = 2.0

    has_window = False

    def __init__(
            self, *,
            node: music.BaseNode,
            icon: Optional[QtSvg.QSvgRenderer] = None,
            **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)

        self.setZValue(1.0)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.props = NodeProps()

        self.__session_prefix = 'node/%016x/' % node.id
        self.__listeners = core.ListenerList()
        self.add_cleanup_function(self.__listeners.cleanup)

        self.__node = node

        self.__window = None  # type: QtWidgets.QWidget

        self.__box = Box(self)

        if icon is not None:
            self.__icon = NodeIcon(icon, self)
        else:
            self.__icon = None

        self.__ports = {}  # type: Dict[str, Port]
        for port_desc in self.__node.description.ports:
            port = Port(port_desc, self)
            self.__ports[port_desc.name] = port

        self.__title = Title(self.__node.name, self)

        self.__title_edit = QtWidgets.QLineEdit()
        self.__title_edit.editingFinished.connect(self.__renameNodeFinished)

        self.__title_edit_proxy = QtWidgets.QGraphicsProxyWidget(self)
        self.__title_edit_proxy.setWidget(self.__title_edit)

        self.__title_widgets_proxy = None
        self.__title_widgets_container = None
        title_widgets = list(self.titleWidgets())
        if title_widgets:
            self.__title_widgets_container = QtWidgets.QWidget()
            self.__title_widgets_container.setAutoFillBackground(False)
            self.__title_widgets_container.setAttribute(Qt.WA_NoSystemBackground, True)

            layout = QtWidgets.QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(1)
            for widget in title_widgets:
                layout.addWidget(widget)
            self.__title_widgets_container.setLayout(layout)

            self.__title_widgets_proxy = QtWidgets.QGraphicsProxyWidget(self)
            self.__title_widgets_proxy.setWidget(self.__title_widgets_container)

        self.__body_proxy = None  # type: QtWidgets.QGraphicsProxyWidget
        self.__body = self.createBodyWidget()
        if self.__body is not None:
            self.__body.setAutoFillBackground(False)
            self.__body.setAttribute(Qt.WA_NoSystemBackground, True)
            self.__body_proxy = QtWidgets.QGraphicsProxyWidget(self)
            self.__body_proxy.setWidget(self.__body)

        self.__transform = QtGui.QTransform()
        self.__canvas_rect = self.__transform.mapRect(self.contentRect())

        self.__selected = False
        self.__hovered = False
        self.__rename_node = False

        self.__drag_rect = QtCore.QRectF()

        self.__listeners.add(
            self.__node.name_changed.add(self.__nameChanged))
        self.__listeners.add(
            self.__node.graph_pos_changed.add(self.__graphRectChanged))
        self.__listeners.add(
            self.__node.graph_size_changed.add(self.__graphRectChanged))
        self.__listeners.add(
            self.__node.graph_color_changed.add(lambda *_: self.__updateState()))
        self.__listeners.add(
            self.__node.port_properties_changed.add(lambda *_: self.__layout()))
        self.__listeners.add(
            self.__node.description_changed.add(lambda *_: self.__descriptionChanged()))

        self.__state = None  # type: audioproc.NodeStateChange.State

        self.__listeners.add(
            self.audioproc_client.node_state_changed.add(
                '%08x' % self.__node.id, self.__stateChanged))

        self.__updateState()

    def __str__(self) -> str:
        return '<node name=%r> ' % self.__node.name

    @property
    def __in_ports(self) -> List[node_db.PortDescription]:
        return [
            port_desc for port_desc in self.__node.description.ports
            if port_desc.direction == node_db.PortDescription.INPUT
        ]

    @property
    def __out_ports(self) -> List[node_db.PortDescription]:
        return [
            port_desc for port_desc in self.__node.description.ports
            if port_desc.direction == node_db.PortDescription.OUTPUT
        ]

    def __nameChanged(self, *args: Any) -> None:
        self.__title.setText(self.__node.name)

    def __graphRectChanged(self, *args: Any) -> None:
        self.__canvas_rect = self.__transform.mapRect(self.contentRect())
        self.__layout()
        self.props.contentRectChanged.emit(self.contentRect())

    def createBodyWidget(self) -> QtWidgets.QWidget:
        return None

    def createWindow(self, **kwargs: Any) -> QtWidgets.QWidget:
        raise RuntimeError("Node %s does not support windows." % type(self).__name__)

    def titleWidgets(self) -> Iterable[QtWidgets.QWidget]:
        if self.__node.description.node_ui.muteable:
            muted_button = mute_button.MuteButton()
            muted_button.toggled.connect(
                lambda muted: self.project_client.set_session_value(
                    self.__session_prefix + 'muted', muted))
            muted_button.setChecked(
                self.project_client.get_session_value(
                    self.__session_prefix + 'muted', False))
            self.project_client.add_session_data_listener(
                self.__session_prefix + 'muted', muted_button.setChecked)
            yield muted_button

        if self.__node.removable:
            remove_button = QtWidgets.QToolButton()
            remove_button.setAutoRaise(True)
            remove_button.setIcon(QtGui.QIcon(
                os.path.join(constants.DATA_DIR, 'icons', 'window-close.svg')))
            remove_button.clicked.connect(self.onRemove)
            yield remove_button

    def setup(self) -> None:
        for port in self.__ports.values():
            port.setup()

    def cleanup(self) -> None:
        for port in self.__ports.values():
            port.cleanup()
        self.__ports.clear()

        if self.__window is not None:
            self.__window.close()
            self.__window = None

        super().cleanup()

    def node(self) -> music.BaseNode:
        return self.__node

    def id(self) -> int:
        return self.__node.id

    def name(self) -> str:
        return self.__node.name

    def graph_pos(self) -> value_types.Pos2F:
        return self.__node.graph_pos

    def graph_size(self) -> value_types.SizeF:
        return self.__node.graph_size

    def ports(self) -> Iterable[Port]:
        for port_desc in self.__node.description.ports:
            yield self.__ports[port_desc.name]

    def upstream_nodes(self) -> List[music.BaseNode]:
        return self.__node.upstream_nodes()

    def selected(self) -> bool:
        return self.__selected

    def setSelected(self, selected: bool) -> None:
        self.__selected = selected
        self.__updateState()

    def port(self, port_name: str) -> Port:
        return self.__ports[port_name]

    def portHandleScenePos(self, port_name: str) -> QtCore.QPointF:
        return self.__ports[port_name].handleScenePos()

    def contentTopLeft(self) -> QtCore.QPointF:
        return QtCore.QPointF(self.__node.graph_pos.x, self.__node.graph_pos.y)

    def contentSize(self) -> QtCore.QSizeF:
        return QtCore.QSizeF(self.__node.graph_size.width, self.__node.graph_size.height)

    def contentRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self.contentTopLeft(), self.contentSize())

    def canvasTopLeft(self) -> QtCore.QPointF:
        return self.__canvas_rect.topLeft()

    def setCanvasTopLeft(self, pos: QtCore.QPointF) -> None:
        self.__canvas_rect.moveTopLeft(pos)
        self.__layout()

    def setCanvasRect(self, rect: QtCore.QRectF) -> None:
        self.__canvas_rect = rect
        self.__layout()

    def canvasRect(self) -> QtCore.QRectF:
        return self.__canvas_rect

    def setCanvasTransform(self, transform: QtGui.QTransform) -> None:
        self.__transform = transform
        self.__canvas_rect = self.__transform.mapRect(self.contentRect())
        self.__layout()

    def resizeSide(self, pos: QtCore.QPointF) -> Optional[str]:
        t = self.__canvas_rect.top()
        b = self.__canvas_rect.bottom()
        l = self.__canvas_rect.left()
        r = self.__canvas_rect.right()
        w = self.__canvas_rect.width()
        h = self.__canvas_rect.height()
        resize_rects = {
            'top':         QtCore.QRectF(l + 4, t, w - 8, 4),
            'bottom':      QtCore.QRectF(l + 10, b - 10, w - 20, 10),
            'left':        QtCore.QRectF(l, t + 4, 4, h - 14),
            'right':       QtCore.QRectF(r - 4, t + 4, 4, h - 14),
            'topleft':     QtCore.QRectF(l, t, 4, 4),
            'topright':    QtCore.QRectF(r - 4, t, 4, 4),
            'bottomleft':  QtCore.QRectF(l, b - 10, 10, 10),
            'bottomright': QtCore.QRectF(r - 10, b - 10, 10, 10),
        }

        for side, rect in resize_rects.items():
            if rect.contains(pos):
                return side

        return None

    def dragRect(self) -> QtCore.QRectF:
        return self.__drag_rect

    def boundingRect(self) -> QtCore.QRectF:
        return self.__box.boundingRect()

    def __descriptionChanged(self) -> None:
        ports = {}
        for port_desc in self.__node.description.ports:
            if port_desc.name not in self.__ports:
                port = Port(port_desc, self)
                port.setup()
            else:
                port = self.__ports[port_desc.name]
                port.descriptionChanged(port_desc)

            ports[port_desc.name] = port

        for port_name, port in self.__ports.items():
            if port_name not in ports:
                port.cleanup()
                port.setParentItem(None)
                self.scene().removeItem(port)

        self.__ports = ports
        self.__layout()

    def __stateChanged(self, state_change: audioproc.NodeStateChange) -> None:
        if state_change.HasField('state'):
            self.__state = state_change.state
            self.__updateState()

    def __updateState(self) -> None:
        if self.__selected or self.__hovered:
            opacity = 1.0
        else:
            opacity = 0.7

        self.__box.setOpacity(opacity)
        for port in self.__ports.values():
            if not port.highlighted():
                port.setOpacity(opacity)

        if self.__state == audioproc.NodeStateChange.BROKEN:
            pen = QtGui.QPen()
            pen.setColor(Qt.black)
            pen.setWidth(2)
            self.__box.setPen(pen)
            self.__box.setBrush(QtGui.QColor(255, 0, 0))

        elif self.__selected:
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(80, 80, 200))
            pen.setWidth(2)
            self.__box.setPen(pen)
            self.__box.setBrush(QtGui.QColor(150, 150, 255))
        else:
            pen = QtGui.QPen()
            pen.setColor(Qt.black)
            pen.setWidth(2)
            self.__box.setPen(pen)
            self.__box.setBrush(QtGui.QColor.fromRgbF(
                self.__node.graph_color.r,
                self.__node.graph_color.g,
                self.__node.graph_color.b,
                self.__node.graph_color.a))

    def __layout(self) -> None:
        self.setPos(self.__canvas_rect.topLeft())

        w, h = self.__canvas_rect.width(), self.__canvas_rect.height()

        path = QtGui.QPainterPath()
        path.addRoundedRect(0, 0, w, h, 5, 5)
        self.__box.setPath(path)

        visible_in_ports = []
        for desc in self.__in_ports:
            port_properties = self.__node.get_port_properties(desc.name)
            if not port_properties.exposed:
                port = self.__ports[desc.name]
                port.setVisible(False)
                continue

            visible_in_ports.append(desc)

        show_ports = (0.5 * h > 10 * max(len(visible_in_ports), len(self.__out_ports)))
        for idx, desc in enumerate(visible_in_ports):
            port = self.__ports[desc.name]
            if len(visible_in_ports) > 1:
                y = h * (0.5 * idx / (len(visible_in_ports) - 1) + 0.25)
            else:
                y = h * 0.5
            port.setPos(0, y)
            port.setVisible(show_ports)

        for idx, desc in enumerate(self.__out_ports):
            port = self.__ports[desc.name]
            if len(self.__out_ports) > 1:
                y = h * (0.5 * idx / (len(self.__out_ports) - 1) + 0.25)
            else:
                y = h * 0.5
            port.setPos(w, y)
            port.setVisible(show_ports)

        if self.__rename_node:
            title_h = self.__title_edit_proxy.minimumHeight() + 4

            self.__title_edit_proxy.setVisible(True)
            self.__title_edit_proxy.setPos(4, 4)
            self.__title_edit_proxy.resize(w - 8, self.__title_edit_proxy.minimumHeight())

        else:
            title_h = 24

            self.__title_edit_proxy.setVisible(False)

        if self.__title_widgets_proxy is not None:
            if (h > self.__title_widgets_container.height() + 2
                    and w > self.__title_widgets_container.width() + 40
                    and not self.__rename_node):
                self.__title_widgets_proxy.setVisible(True)
                self.__title_widgets_proxy.setPos(
                    w - self.__title_widgets_container.width() - 4, 2)

                title_h = self.__title_widgets_container.height() + 4
            else:
                self.__title_widgets_proxy.setVisible(False)

        if h > 20 and not self.__rename_node:
            self.__title.setVisible(True)
            self.__title.setPos(8, (title_h - 2 - self.__title.boundingRect().height()) / 2)

            if self.__title_widgets_proxy is not None and self.__title_widgets_proxy.isVisible():
                self.__title.setWidth(self.__title_widgets_proxy.pos().x() - 8)
            else:
                self.__title.setWidth(w - 16)

        else:
            self.__title.setVisible(False)

        if self.__icon is not None:
            if self.__title.isVisible():
                icon_y = 24
            else:
                icon_y = 3
            self.__icon.setRect(QtCore.QRectF(3, icon_y, w - 6, h - icon_y - 6))

        if self.__body_proxy is not None:
            bsize = self.__body_proxy.minimumSize()
            if h > bsize.height() + (title_h + 4) and w > bsize.width() + 8:
                self.__body_proxy.setVisible(True)
                self.__body_proxy.setPos(4, title_h)
                self.__body_proxy.resize(w - 8, h - (title_h + 4))

            else:
                self.__body_proxy.setVisible(False)

        if self.__title_edit_proxy.isVisible():
            drag_rect_width, drag_rect_height = 0.0, 0.0
        else:
            if self.__body_proxy is not None and self.__body_proxy.isVisible():
                drag_rect_height = title_h
            else:
                drag_rect_height = h

            if self.__title_widgets_proxy is not None and self.__title_widgets_proxy.isVisible():
                drag_rect_width = self.__title_widgets_proxy.pos().x()
            else:
                drag_rect_width = w

        self.__drag_rect = QtCore.QRectF(0, 0, drag_rect_width, drag_rect_height)

        self.props.canvasLayoutChanged.emit()

    def paint(
            self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem,
            widget: Optional[QtWidgets.QWidget] = None) -> None:
        pass

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.setZValue(Node.__next_zvalue)
        Node.__next_zvalue += 1
        event.ignore()
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        self.__hovered = True
        self.__updateState()
        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        self.__hovered = False
        self.__updateState()
        return super().hoverLeaveEvent(event)

    def buildContextMenu(self, menu: QtWidgets.QMenu) -> None:
        if self.has_window:
            show_window = menu.addAction("Open in window")
            show_window.triggered.connect(self.onShowWindow)

        if self.__node.removable:
            remove = menu.addAction("Remove")
            remove.triggered.connect(self.onRemove)

        rename = menu.addAction("Rename")
        rename.triggered.connect(self.renameNode)

        color_menu = menu.addMenu("Set color")
        color_action = SelectColorAction(color_menu)
        color_action.colorSelected.connect(self.onSetColor)
        color_menu.addAction(color_action)

    def onShowWindow(self) -> None:
        if self.__window is None:
            self.__window = self.createWindow(parent=self.project_view)

        self.__window.show()
        self.__window.raise_()
        self.__window.activateWindow()

    def onRemove(self) -> None:
        with self.project.apply_mutations('Remove node %s' % self.__node.name):
            for conn in self.__node.connections:
                self.project.remove_node_connection(conn)
            self.project.remove_node(self.__node)

    def onSetColor(self, color: value_types.Color) -> None:
        if color != self.__node.graph_color:
            with self.project.apply_mutations('%s: Set color' % self.__node.name):
                self.__node.graph_color = color

    def renameNode(self) -> None:
        self.__rename_node = True
        self.__title_edit.setText(self.__node.name)
        self.__title_edit.setFocus()
        self.__title_edit.selectAll()
        self.__layout()

    def __renameNodeFinished(self) -> None:
        new_name = self.__title_edit.text()
        if new_name != self.__node.name:
            self.__title.setText(self.__node.name)
            with self.project.apply_mutations('%s: Rename to "%s"' % (self.__node.name, new_name)):
                self.__node.name = new_name

        self.__rename_node = False
        self.__layout()


class Connection(ui_base.ProjectMixin, QtWidgets.QGraphicsPathItem):
    def __init__(
            self, *,
            connection: music.NodeConnection,
            src_node: Node,
            dest_node: Node,
            **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.__connection = connection
        self.__src_node = src_node
        self.__dest_node = dest_node

        self.__highlighted = False

        self.__src_node_canvas_layout_changed_connection = \
            self.__src_node.props.canvasLayoutChanged.connect(self.__update)
        self.__dest_node_canvas_layout_changed_connection = \
            self.__dest_node.props.canvasLayoutChanged.connect(self.__update)

        self.__update()

    def cleanup(self) -> None:
        if self.__src_node_canvas_layout_changed_connection is not None:
            self.__src_node.props.canvasLayoutChanged.disconnect(
                self.__src_node_canvas_layout_changed_connection)
            self.__src_node_canvas_layout_changed_connection = None

        if self.__dest_node_canvas_layout_changed_connection is not None:
            self.__dest_node.props.canvasLayoutChanged.disconnect(
                self.__dest_node_canvas_layout_changed_connection)
            self.__dest_node_canvas_layout_changed_connection = None

    def connection(self) -> music.NodeConnection:
        return self.__connection

    def id(self) -> int:
        return self.__connection.id

    def src_node(self) -> Node:
        return self.__src_node

    def src_port(self) -> Port:
        return self.__src_node.port(self.__connection.source_port)

    def dest_node(self) -> Node:
        return self.__dest_node

    def dest_port(self) -> Port:
        return self.__dest_node.port(self.__connection.dest_port)

    def setHighlighted(self, highlighted: bool) -> None:
        self.__highlighted = highlighted
        self.__update()

    def __update(self) -> None:
        color = port_colors[self.__connection.type]

        if self.__highlighted:
            pen = QtGui.QPen()
            pen.setColor(color)
            pen.setWidth(4)
            self.setPen(pen)
        else:
            pen = QtGui.QPen()
            pen.setColor(color)
            pen.setWidth(2)
            self.setPen(pen)

        pos1 = self.__src_node.portHandleScenePos(self.__connection.source_port)
        pos2 = self.__dest_node.portHandleScenePos(self.__connection.dest_port)
        cpos = QtCore.QPointF(min(100, abs(pos2.x() - pos1.x()) / 2), 0)

        path = QtGui.QPainterPath()
        path.moveTo(pos1)
        path.cubicTo(pos1 + cpos, pos2 - cpos, pos2)
        self.setPath(path)
