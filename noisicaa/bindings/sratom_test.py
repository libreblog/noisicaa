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

from noisidev import unittest
from noisicaa import lv2
from . import sratom


class SratomTest(unittest.TestCase):
    def test_atom_to_turle(self):
        buf = bytearray(1024)

        mapper = lv2.DynamicURIDMapper()

        forge = lv2.AtomForge(mapper)
        forge.set_buffer(buf, 1024)
        with forge.sequence():
            forge.write_midi_event(123, b'abc', 3)
            forge.write_midi_event(124, b'def', 3)

        turtle = sratom.atom_to_turtle(mapper, buf)
        self.assertIsInstance(turtle, str)
