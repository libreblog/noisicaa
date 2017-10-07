#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2017, Benjamin Niemann <pink@odahoda.de>
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
import inspect
import logging
import os.path
from unittest import mock

import asynctest
from PyQt5.QtCore import Qt
from PyQt5 import QtGui

from noisicaa import core
from noisicaa import instrument_db
from noisicaa import node_db
from noisicaa.core import ipc
from noisicaa.runtime_settings import RuntimeSettings
from .editor_app import BaseEditorApp
from . import model


UNSET = object()

class TestMixin(object):
    def __init__(
            self, __no_positional_args=UNSET, testcase=None, **kwargs):
        assert __no_positional_args is UNSET
        assert testcase is not None
        self.__testcase = testcase
        super().__init__(**kwargs)

    @property
    def context(self):
        return {'testcase': self.__testcase}

    @property
    def app(self):
        return self.__testcase.app

    @property
    def window(self):
        return self.__testcase.window

    @property
    def event_loop(self):
        return self.__testcase.loop

    @property
    def project_connection(self):
        return self.__testcase.project_connection

    @property
    def project(self):
        return self.__testcase.project

    @property
    def project_client(self):
        return self.__testcase.project_client

    def call_async(self, coroutine, callback=None):
        task = self.event_loop.create_task(coroutine)
        task.add_done_callback(
            functools.partial(self.__call_async_cb, callback=callback))

    def __call_async_cb(self, task, callback):
        if task.exception() is not None:
            raise task.exception()
        if callback is not None:
            callback(task.result())

    def send_command_async(self, target_id, cmd, **kwargs):
        self.__testcase.commands.append((target_id, cmd, kwargs))


class MockSettings(object):
    def __init__(self):
        self._data = {}

    def value(self, key, default):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value

    def allKeys(self):
        return list(self._data.keys())


class MockSequencer(object):
    def __init__(self):
        self._ports = []

    def add_port(self, port_info):
        self._ports.append(port_info)

    def list_all_ports(self):
        yield from self._ports

    def get_pollin_fds(self):
        return []

    def connect(self, port_info):
        pass

    def disconnect(self, port_info):
        pass

    def close(self):
        pass

    def get_event(self):
        return None


class AsyncSetupBase():
    async def setup(self):
        pass

    async def cleanup(self):
        pass


class TestNodeDBProcess(node_db.NodeDBProcessBase):
    def handle_start_session(self, client_address, flags):
        return '123'

    def handle_end_session(self, session_id):
        return None

    def handle_shutdown(self):
        pass


class TestInstrumentDBProcess(instrument_db.InstrumentDBProcessBase):
    def handle_start_session(self, client_address, flags):
        return '123'

    def handle_end_session(self, session_id):
        return None

    def handle_shutdown(self):
        pass


class MockProcess(core.ProcessBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project = None


class MockApp(BaseEditorApp):
    def __init__(self):
        super().__init__(None, RuntimeSettings(), MockSettings())
        self.process = None

    def createSequencer(self):
        return MockSequencer()


class Bunch(object): pass


class UITest(asynctest.TestCase):
    # There are random crashes if we create and destroy the QApplication for
    # each test. So create a single one and re-use it for all tests. This
    # makes the tests non-hermetic, which could be a problem, but it's better
    # than fighting with the garbage collection in pyqt5.
    app = None

    async def setUp(self):
        self.node_db_process = TestNodeDBProcess(
            name='node_db', event_loop=self.loop, manager=None)
        await self.node_db_process.setup()

        self.instrument_db_process = TestInstrumentDBProcess(
            name='instrument_db', event_loop=self.loop, manager=None)
        await self.instrument_db_process.setup()

        self.manager = mock.Mock()
        async def mock_call(cmd, *args, **kwargs):
            if cmd == 'CREATE_NODE_DB_PROCESS':
                return self.node_db_process.server.address
            elif cmd == 'CREATE_INSTRUMENT_DB_PROCESS':
                return self.instrument_db_process.server.address
            else:
                self.fail(cmd)

        self.manager.call.side_effect = mock_call

        self.process = MockProcess(
            name='ui', event_loop=self.loop, manager=self.manager)
        await self.process.setup()

        if UITest.app is None:
            UITest.app = MockApp()
        UITest.app.process = self.process
        await UITest.app.setup()

        self.window = None
        self.project_connection = Bunch()
        self.project_connection.name = 'test project'
        self.project = model.Project('project')
        self.project_client = None

        self.context = {'testcase': self}
        self.commands = []

    async def tearDown(self):
        await UITest.app.cleanup()
        UITest.app.process = None
        await self.process.cleanup()
        await self.instrument_db_process.cleanup()
        await self.node_db_process.cleanup()

    _snapshot_numbers = {}

    def create_snapshot(self, obj, zoom=1.0, raster=False):
        case_name = self.__class__.__name__

        frames = inspect.getouterframes(inspect.currentframe())
        for frame in frames:
            if frame[3].startswith('test_'):
                test_name = frame[3]
                break
        else:
            raise RuntimeError("Can't find test name")

        num = self._snapshot_numbers.setdefault((case_name, test_name), 0)
        self._snapshot_numbers[(case_name, test_name)] += 1

        img_name = '%s.%s.%d.png' % (case_name, test_name, num)

        image = QtGui.QImage(
            int(zoom * obj.width()) + 20,
            int(zoom * obj.height()) + 20,
            QtGui.QImage.Format_ARGB32)
        painter = QtGui.QPainter(image)

        painter.save()
        painter.fillRect(
            0, 0, int(zoom * obj.width()) + 20, int(zoom * obj.height()) + 20,
            QtGui.QColor(255, 0, 0))
        painter.fillRect(
            10, 10, int(zoom * obj.width()), int(zoom * obj.height()),
            Qt.white)
        painter.restore()

        if raster:
            painter.save()
            painter.setPen(QtGui.QColor(200, 200, 200))

            for x in range(10, int(zoom * obj.width()) + 10, 10):
                painter.drawLine(x, 10, x, int(zoom * obj.height()) + 9)
            for y in range(10, int(zoom * obj.height()) + 10, 10):
                painter.drawLine(10, y, int(zoom * obj.width()) + 9, y)
            painter.restore()

        painter.setViewport(10, 10, zoom * obj.width(), zoom * obj.height())
        obj.render(painter)
        painter.end()
        logging.info("Saving snapshot %s...", test_name)
        image.save(os.path.join('/tmp', img_name))
