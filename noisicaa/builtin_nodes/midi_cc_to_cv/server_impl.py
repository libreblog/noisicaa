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
import typing
from typing import Any, Iterator, MutableSequence

from noisicaa.core.typing_extra import down_cast
from noisicaa import audioproc
from noisicaa.music import graph
from noisicaa.music import pmodel
from noisicaa.music import commands
from noisicaa.builtin_nodes import commands_registry_pb2
from . import commands_pb2
from . import model_pb2
from . import processor_pb2
from . import model

if typing.TYPE_CHECKING:
    from noisicaa import core

logger = logging.getLogger(__name__)


class UpdateMidiCCtoCV(commands.Command):
    proto_type = 'update_midi_cc_to_cv'
    proto_ext = commands_registry_pb2.update_midi_cc_to_cv

    def run(self) -> None:
        pb = down_cast(commands_pb2.UpdateMidiCCtoCV, self.pb)
        down_cast(MidiCCtoCV, self.pool[pb.node_id])


class CreateMidiCCtoCVChannel(commands.Command):
    proto_type = 'create_midi_cc_to_cv_channel'
    proto_ext = commands_registry_pb2.create_midi_cc_to_cv_channel

    def run(self) -> None:
        pb = down_cast(commands_pb2.CreateMidiCCtoCVChannel, self.pb)
        node = down_cast(MidiCCtoCV, self.pool[pb.node_id])

        if pb.HasField('index'):
            index = pb.index
        else:
            index = len(node.channels)

        channel = self.pool.create(
            MidiCCtoCVChannel,
            type=model_pb2.MidiCCtoCVChannel.CONTROLLER)
        node.channels.insert(index, channel)


class UpdateMidiCCtoCVChannel(commands.Command):
    proto_type = 'update_midi_cc_to_cv_channel'
    proto_ext = commands_registry_pb2.update_midi_cc_to_cv_channel

    def run(self) -> None:
        pb = down_cast(commands_pb2.UpdateMidiCCtoCVChannel, self.pb)
        channel = down_cast(MidiCCtoCVChannel, self.pool[pb.channel_id])

        if pb.HasField('set_type'):
            channel.type = pb.set_type

        if pb.HasField('set_midi_channel'):
            channel.midi_channel = pb.set_midi_channel

        if pb.HasField('set_midi_controller'):
            channel.midi_controller = pb.set_midi_controller

        if pb.HasField('set_min_value'):
            channel.min_value = pb.set_min_value

        if pb.HasField('set_max_value'):
            channel.max_value = pb.set_max_value

        if pb.HasField('set_log_scale'):
            channel.log_scale = pb.set_log_scale


class DeleteMidiCCtoCVChannel(commands.Command):
    proto_type = 'delete_midi_cc_to_cv_channel'
    proto_ext = commands_registry_pb2.delete_midi_cc_to_cv_channel

    def run(self) -> None:
        pb = down_cast(commands_pb2.DeleteMidiCCtoCVChannel, self.pb)
        channel = down_cast(MidiCCtoCVChannel, self.pool[pb.channel_id])
        node = down_cast(MidiCCtoCV, channel.parent)

        del node.channels[channel.index]


class MidiCCtoCVChannel(model.MidiCCtoCVChannel, pmodel.ObjectBase):
    def create(
            self, *,
            type: model_pb2.MidiCCtoCVChannel.Type = model_pb2.MidiCCtoCVChannel.CONTROLLER,  # pylint: disable=redefined-builtin
            **kwargs: Any
    ) -> None:
        super().create(**kwargs)

        self.type = type

    def setup(self) -> None:
        super().setup()

        self.type_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.midi_channel_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.midi_controller_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.min_value_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.max_value_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.log_scale_changed.add(lambda _: self.midi_cc_to_cv.update_spec())
        self.log_scale_changed.add(lambda _: self.midi_cc_to_cv.update_spec())

    @property
    def midi_cc_to_cv(self) -> 'MidiCCtoCV':
        return down_cast(MidiCCtoCV, self.parent)

    @property
    def type(self) -> model_pb2.MidiCCtoCVChannel.Type:
        return self.get_property_value('type')

    @type.setter
    def type(self, value: model_pb2.MidiCCtoCVChannel.Type) -> None:
        self.set_property_value('type', value)

    @property
    def midi_channel(self) -> int:
        return self.get_property_value('midi_channel')

    @midi_channel.setter
    def midi_channel(self, value: int) -> None:
        self.set_property_value('midi_channel', value)

    @property
    def midi_controller(self) -> int:
        return self.get_property_value('midi_controller')

    @midi_controller.setter
    def midi_controller(self, value: int) -> None:
        self.set_property_value('midi_controller', value)

    @property
    def min_value(self) -> float:
        return self.get_property_value('min_value')

    @min_value.setter
    def min_value(self, value: float) -> None:
        self.set_property_value('min_value', value)

    @property
    def max_value(self) -> float:
        return self.get_property_value('max_value')

    @max_value.setter
    def max_value(self, value: float) -> None:
        self.set_property_value('max_value', value)

    @property
    def log_scale(self) -> bool:
        return self.get_property_value('log_scale')

    @log_scale.setter
    def log_scale(self, value: bool) -> None:
        self.set_property_value('log_scale', value)


class MidiCCtoCV(model.MidiCCtoCV, graph.BaseNode):
    def create(self, **kwargs: Any) -> None:
        super().create(**kwargs)

        channel = self._pool.create(
            MidiCCtoCVChannel,
            type=model_pb2.MidiCCtoCVChannel.CONTROLLER)
        self.channels.append(channel)

    def setup(self) -> None:
        super().setup()

        self.channels_changed.add(lambda _: self.update_spec())

    def get_initial_parameter_mutations(self) -> Iterator[audioproc.Mutation]:
        yield from super().get_initial_parameter_mutations()
        yield self.__get_spec_mutation()

    def update_spec(self) -> None:
        if self.attached_to_project:
            self.project.handle_pipeline_mutation(
                self.__get_spec_mutation())

    def __get_spec_mutation(self) -> audioproc.Mutation:
        params = audioproc.NodeParameters()
        spec = params.Extensions[processor_pb2.midi_cc_to_cv_spec]
        for channel in self.channels:
            channel_spec = spec.channels.add()
            channel_spec.midi_channel = channel.midi_channel
            channel_spec.midi_controller = channel.midi_controller
            channel_spec.min_value = channel.min_value
            channel_spec.max_value = channel.max_value
            channel_spec.log_scale = channel.log_scale

        return audioproc.Mutation(
            set_node_parameters=audioproc.SetNodeParameters(
                node_id=self.pipeline_node_id,
                parameters=params))

    @property
    def channels(self) -> MutableSequence[MidiCCtoCVChannel]:
        return self.get_property_value('channels')
