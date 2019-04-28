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

from typing import Sequence

from noisicaa.music import project_client_model
from . import model


class MidiCCtoCVChannel(
        project_client_model.ProjectChild,
        model.MidiCCtoCVChannel,
        project_client_model.ObjectBase):
    pass


class MidiCCtoCV(
        project_client_model.BaseNode,
        model.MidiCCtoCV,
        project_client_model.ObjectBase):
    @property
    def channels(self) -> Sequence[MidiCCtoCVChannel]:
        return self.get_property_value('channels')