#!/usr/bin/python

import functools
import math
import time
import uuid

from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from noisicaa.core import stats

from . import ui_base

class StatGraph(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def __init__(self, *, parent):
        super().__init__(parent)

        self.setMinimumHeight(200)
        self.setMaximumHeight(200)

        self.__selected = False
        self.__expression = None
        self.__compiled_expression = None
        self.__id = uuid.uuid4().hex
        self.__timeseries_set = None

    def id(self):
        return self.__id

    def selected(self):
        return self.__selected

    def setSelected(self, selected):
        self.__selected = bool(selected)
        self.update()

    def expression(self):
        return self.__expression

    def compiled_expression(self):
        return self.__compiled_expression

    def setExpression(self, expr, compiled):
        self.__expression = expr
        self.__compiled_expression = compiled

    def is_valid(self):
        return self.__compiled_expression is not None

    def setTimeseriesSet(self, ts_set):
        self.__timeseries_set = ts_set
        self.update()

    def mousePressEvent(self, evt):
        self.clicked.emit()

    def paintEvent(self, evt):
        super().paintEvent(evt)

        painter = QtGui.QPainter(self)

        if self.__selected:
            painter.fillRect(0, 0, self.width(), self.height(), QtGui.QColor(60, 0, 0))
        else:
            painter.fillRect(0, 0, self.width(), self.height(), Qt.black)

        painter.setPen(Qt.white)
        if self.__expression is not None:
            painter.drawText(200, 16, self.__expression)

        if self.__timeseries_set is not None:
            vmin = self.__timeseries_set.min()
            vmax = self.__timeseries_set.max()

            if vmax == vmin:
                vmin = vmin - 1
                vmax = vmax + 1

            painter.drawText(5, 16, str(vmax))
            painter.drawText(5, self.height() - 10, str(vmin))

            for name, ts in self.__timeseries_set.items():
                px, py = None, None
                for idx, value in enumerate(ts):
                    x = self.width() - idx - 1
                    y = int((self.height() - 1) * (vmax - value.value) / (vmax - vmin))
                    if px is not None:
                        painter.drawLine(px, py, x, y)
                    px, py = x, y

        painter.end()


class QTextEdit(QtWidgets.QTextEdit):
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)

        self.setAcceptRichText(False)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        self.__initial_text = None

    def keyPressEvent(self, evt):
        if (evt.modifiers() == Qt.ControlModifier and evt.key() == Qt.Key_Return):
            self.editingFinished.emit()
            self.__initial_text = self.toPlainText()
            evt.accept()
            return
        super().keyPressEvent(evt)

    def focusInEvent(self, evt):
        super().focusInEvent(evt)
        self.__initial_text = self.toPlainText()

    def focusOutEvent(self, evt):
        super().focusOutEvent(evt)
        new_text = self.toPlainText()
        if new_text != self.__initial_text:
            self.editingFinished.emit()
        self.__initial_text = None


class StatMonitor(ui_base.CommonMixin, QtWidgets.QMainWindow):
    visibilityChanged = QtCore.pyqtSignal(bool)

    def __init__(self, app):
        super().__init__(app=app)

        self.__update_timer = QtCore.QTimer(self)
        self.__update_timer.setInterval(1000)
        self.__update_timer.timeout.connect(self.onUpdate)

        self.__realtime = True
        self.__time_scale = 4096

        self.setWindowTitle("noisicaä - Stat Monitor")
        self.resize(600, 300)

        self.__pause_action = QtWidgets.QAction(
            QtGui.QIcon.fromTheme('media-playback-pause'),
            "Play",
            self, triggered=self.onToggleRealtime)
        self.__zoom_in_action = QtWidgets.QAction(
            QtGui.QIcon.fromTheme('zoom-in'),
            "Zoom In",
            self, triggered=self.onZoomIn)
        self.__zoom_out_action = QtWidgets.QAction(
            QtGui.QIcon.fromTheme('zoom-out'),
            "Zoom Out",
            self, triggered=self.onZoomOut)
        self.__add_stat_action = QtWidgets.QAction(
            QtGui.QIcon.fromTheme('list-add'),
            "Add stat",
            self, triggered=self.onAddStat)

        self.__toolbar = QtWidgets.QToolBar()
        self.__toolbar.addAction(self.__pause_action)
        self.__toolbar.addAction(self.__zoom_in_action)
        self.__toolbar.addAction(self.__zoom_out_action)
        self.__toolbar.addAction(self.__add_stat_action)
        self.addToolBar(Qt.TopToolBarArea, self.__toolbar)

        self.__stat_graphs = []
        self.__selected_graph = None

        self.__stat_list_layout = QtWidgets.QVBoxLayout()
        self.__stat_list_layout.setSpacing(4)

        self.__stat_list = QtWidgets.QWidget(self)
        self.__stat_list.setLayout(self.__stat_list_layout)

        self.__scroll_area = QtWidgets.QScrollArea(self)
        self.__scroll_area.setWidget(self.__stat_list)
        self.__scroll_area.setWidgetResizable(True)
        self.__scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.__expression_input = QTextEdit(self)
        self.__expression_input.setMaximumHeight(100)
        self.__expression_input.editingFinished.connect(
            self.onExpressionInputEdited)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.__scroll_area)
        main_layout.addWidget(self.__expression_input)

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

        self.setVisible(
            int(self.app.settings.value(
                'dialog/stat_monitor/visible', False)))
        self.restoreGeometry(
            self.app.settings.value(
                'dialog/stat_monitor/geometry', b''))

    def storeState(self):
        s = self.app.settings
        s.beginGroup('dialog/stat_monitor')
        s.setValue('visible', int(self.isVisible()))
        s.setValue('geometry', self.saveGeometry())
        s.endGroup()

    def showEvent(self, event):
        self.visibilityChanged.emit(True)
        self.__update_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.__update_timer.stop()
        self.visibilityChanged.emit(False)
        super().hideEvent(event)

    def setSelectedGraph(self, graph):
        if self.__selected_graph is not None:
            self.__selected_graph.setSelected(False)
            self.__selected_graph = None

        if graph is not None:
            graph.setSelected(True)
            self.__selected_graph = graph
            self.__expression_input.setPlainText(graph.expression())
        else:
            self.__expression_input.setPlainText('')

    def onToggleRealtime(self):
        if self.__realtime:
            self.__realtime = False
            self.__pause_action.setIcon(
                QtGui.QIcon.fromTheme('media-playback-start'))
        else:
            self.__realtime = True
            self.__pause_action.setIcon(
                QtGui.QIcon.fromTheme('media-playback-pause'))

    def onZoomIn(self):
        self.__time_scale *= 2

    def onZoomOut(self):
        if self.time_scale > 1:
            self.__time_scale //= 2

    def onUpdate(self):
        expressions = {
            graph.id(): graph.compiled_expression()
            for graph in self.__stat_graphs
            if graph.is_valid()}
        self.call_async(
            self.app.process.manager.call('STATS_FETCH', expressions),
            callback=self.onStatsFetched)

    def onStatsFetched(self, result):
        for graph in self.__stat_graphs:
            graph.setTimeseriesSet(result.get(graph.id(), None))

    def onAddStat(self):
        graph = StatGraph(parent=self.__stat_list)
        graph.clicked.connect(functools.partial(self.setSelectedGraph, graph))
        self.setSelectedGraph(graph)
        self.__stat_graphs.append(graph)
        self.__stat_list_layout.addWidget(graph)

    def onExpressionInputEdited(self):
        if self.__selected_graph is None:
            return

        expr = self.__expression_input.toPlainText()
        try:
            compiled = stats.compile_expression(expr)
        except stats.InvalidExpressionError:
            return
        self.__selected_graph.setExpression(expr, compiled)