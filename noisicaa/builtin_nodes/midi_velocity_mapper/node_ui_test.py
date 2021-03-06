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

from noisidev import uitest
from . import node_ui


class MidiVelocityMapperNodeTest(uitest.ProjectMixin, uitest.UITestCase):
    async def setup_testcase(self):
        with self.project.apply_mutations('test'):
            self.node = self.project.create_node('builtin://midi-velocity-mapper')

    async def test_init(self):
        widget = node_ui.MidiVelocityMapperNode(node=self.node, context=self.context)
        widget.cleanup()


class MidiVelocityMapperNodeWidgetTest(uitest.ProjectMixin, uitest.UITestCase):
    async def setup_testcase(self):
        with self.project.apply_mutations('test'):
            self.node = self.project.create_node('builtin://midi-velocity-mapper')

    async def test_init(self):
        widget = node_ui.MidiVelocityMapperNodeWidget(
            node=self.node, session_prefix='test', context=self.context)
        widget.cleanup()
