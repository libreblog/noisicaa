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
from typing import Any, MutableSequence, Optional, Iterator, Iterable, Callable

from noisicaa.core.typing_extra import down_cast
from noisicaa import audioproc
from noisicaa import model
from noisicaa.music import commands
from noisicaa.music import pmodel
from noisicaa.music import base_track
from noisicaa.builtin_nodes import commands_registry_pb2
from . import commands_pb2
from . import model as score_track_model

logger = logging.getLogger(__name__)


class UpdateScoreTrack(commands.Command):
    proto_type = 'update_score_track'
    proto_ext = commands_registry_pb2.update_score_track

    def run(self) -> None:
        pb = down_cast(commands_pb2.UpdateScoreTrack, self.pb)
        track = down_cast(ScoreTrack, self.pool[pb.track_id])

        if pb.HasField('set_transpose_octaves'):
            track.transpose_octaves = pb.set_transpose_octaves


class UpdateScoreMeasure(commands.Command):
    proto_type = 'update_score_measure'
    proto_ext = commands_registry_pb2.update_score_measure

    def run(self) -> None:
        pb = down_cast(commands_pb2.UpdateScoreMeasure, self.pb)
        measure = down_cast(ScoreMeasure, self.pool[pb.measure_id])

        if pb.HasField('set_clef'):
            measure.clef = model.Clef.from_proto(pb.set_clef)

        if pb.HasField('set_key_signature'):
            measure.key_signature = model.KeySignature.from_proto(pb.set_key_signature)


class CreateNote(commands.Command):
    proto_type = 'create_note'
    proto_ext = commands_registry_pb2.create_note

    def run(self) -> int:
        pb = down_cast(commands_pb2.CreateNote, self.pb)
        measure = down_cast(ScoreMeasure, self.pool[pb.measure_id])

        assert 0 <= pb.idx <= len(measure.notes)
        note = self.pool.create(
            Note,
            pitches=[model.Pitch.from_proto(pb.pitch)],
            base_duration=audioproc.MusicalDuration.from_proto(pb.duration))
        measure.notes.insert(pb.idx, note)

        return note.id


class UpdateNote(commands.Command):
    proto_type = 'update_note'
    proto_ext = commands_registry_pb2.update_note

    def run(self) -> None:
        pb = down_cast(commands_pb2.UpdateNote, self.pb)
        note = down_cast(Note, self.pool[pb.note_id])

        if pb.HasField('set_pitch'):
            note.pitches[0] = model.Pitch.from_proto(pb.set_pitch)

        if pb.HasField('add_pitch'):
            pitch = model.Pitch.from_proto(pb.add_pitch)
            if pitch not in note.pitches:
                note.pitches.append(pitch)

        if pb.HasField('remove_pitch'):
            assert 0 <= pb.remove_pitch < len(note.pitches)
            del note.pitches[pb.remove_pitch]

        if pb.HasField('set_duration'):
            note.base_duration = audioproc.MusicalDuration.from_proto(pb.set_duration)

        if pb.HasField('set_dots'):
            if pb.set_dots > note.max_allowed_dots:
                raise ValueError("Too many dots on note")
            note.dots = pb.set_dots

        if pb.HasField('set_tuplet'):
            if pb.set_tuplet not in (0, 3, 5):
                raise ValueError("Invalid tuplet type")
            note.tuplet = pb.set_tuplet

        if pb.HasField('set_accidental'):
            assert 0 <= pb.set_accidental.pitch_idx < len(note.pitches)
            note.pitches[pb.set_accidental.pitch_idx] = (
                note.pitches[pb.set_accidental.pitch_idx].add_accidental(
                    pb.set_accidental.accidental))

        if pb.HasField('transpose'):
            for pidx, pitch in enumerate(note.pitches):
                note.pitches[pidx] = pitch.transposed(
                    half_notes=pb.transpose % 12,
                    octaves=pb.transpose // 12)


class DeleteNote(commands.Command):
    proto_type = 'delete_note'
    proto_ext = commands_registry_pb2.delete_note

    def run(self) -> None:
        pb = down_cast(commands_pb2.DeleteNote, self.pb)
        note = down_cast(Note, self.pool[pb.note_id])
        measure = note.measure
        del measure.notes[note.index]


class Note(pmodel.ProjectChild, score_track_model.Note, pmodel.ObjectBase):
    def create(
            self, *,
            pitches: Optional[Iterable[model.Pitch]] = None,
            base_duration: Optional[audioproc.MusicalDuration] = None,
            dots: int = 0, tuplet: int = 0,
            **kwargs: Any) -> None:
        super().create(**kwargs)

        if pitches is not None:
            self.pitches.extend(pitches)
        if base_duration is None:
            base_duration = audioproc.MusicalDuration(1, 4)
        self.base_duration = base_duration
        self.dots = dots
        self.tuplet = tuplet

        assert (self.base_duration.numerator == 1
                and self.base_duration.denominator in (1, 2, 4, 8, 16, 32)), \
            self.base_duration

    def __str__(self) -> str:
        n = ''
        if len(self.pitches) == 1:
            n += str(self.pitches[0])
        else:
            n += '[' + ''.join(str(p) for p in self.pitches) + ']'

        duration = self.duration
        if duration.numerator == 1:
            n += '/%d' % duration.denominator
        elif duration.denominator == 1:
            n += ';%d' % duration.numerator
        else:
            n += ';%d/%d' % (duration.numerator, duration.denominator)

        return n

    @property
    def pitches(self) -> MutableSequence[model.Pitch]:
        return self.get_property_value('pitches')

    @property
    def base_duration(self) -> audioproc.MusicalDuration:
        return self.get_property_value('base_duration')

    @base_duration.setter
    def base_duration(self, value: audioproc.MusicalDuration) -> None:
        self.set_property_value('base_duration', value)

    @property
    def dots(self) -> int:
        return self.get_property_value('dots')

    @dots.setter
    def dots(self, value: int) -> None:
        self.set_property_value('dots', value)

    @property
    def tuplet(self) -> int:
        return self.get_property_value('tuplet')

    @tuplet.setter
    def tuplet(self, value: int) -> None:
        self.set_property_value('tuplet', value)

    @property
    def measure(self) -> 'ScoreMeasure':
        return down_cast(ScoreMeasure, super().measure)


class ScoreMeasure(base_track.Measure, score_track_model.ScoreMeasure, pmodel.ObjectBase):
    @property
    def clef(self) -> model.Clef:
        return self.get_property_value('clef')

    @clef.setter
    def clef(self, value: model.Clef) -> None:
        self.set_property_value('clef', value)

    @property
    def key_signature(self) -> model.KeySignature:
        return self.get_property_value('key_signature')

    @key_signature.setter
    def key_signature(self, value: model.KeySignature) -> None:
        self.set_property_value('key_signature', value)

    @property
    def notes(self) -> MutableSequence[Note]:
        return self.get_property_value('notes')

    @property
    def track(self) -> 'ScoreTrack':
        return down_cast(ScoreTrack, super().track)

    @property
    def empty(self) -> bool:
        return len(self.notes) == 0


class ScoreTrackConnector(base_track.MeasuredTrackConnector):
    _node = None  # type: ScoreTrack

    def _add_track_listeners(self) -> None:
        self._listeners['transpose_octaves'] = self._node.transpose_octaves_changed.add(
            self.__transpose_octaves_changed)

    def _add_measure_listeners(self, mref: pmodel.MeasureReference) -> None:
        measure = down_cast(ScoreMeasure, mref.measure)
        self._listeners['measure:%s:notes' % mref.id] = measure.content_changed.add(
            lambda _=None: self.__measure_notes_changed(mref))  # type: ignore

    def _remove_measure_listeners(self, mref: pmodel.MeasureReference) -> None:
        self._listeners.pop('measure:%s:notes' % mref.id).remove()

    def _create_events(
            self, time: audioproc.MusicalTime, measure: pmodel.Measure
    ) -> Iterator[base_track.PianoRollInterval]:
        measure = down_cast(ScoreMeasure, measure)
        for note in measure.notes:
            if not note.is_rest:
                for pitch in note.pitches:
                    pitch = pitch.transposed(octaves=self._node.transpose_octaves)
                    event = base_track.PianoRollInterval(
                        time, time + note.duration, pitch, 127)
                    yield event

            time += note.duration

    def __transpose_octaves_changed(self, change: model.PropertyChange) -> None:
        self._update_measure_range(0, len(self._node.measure_list))

    def __measure_notes_changed(self, mref: pmodel.MeasureReference) -> None:
        self._update_measure_range(mref.index, mref.index + 1)


class ScoreTrack(base_track.MeasuredTrack, score_track_model.ScoreTrack, pmodel.ObjectBase):
    measure_cls = ScoreMeasure

    def create(self, *, num_measures: int = 1, **kwargs: Any) -> None:
        super().create(**kwargs)

        for _ in range(num_measures):
            self.append_measure()

    @property
    def transpose_octaves(self) -> int:
        return self.get_property_value('transpose_octaves')

    @transpose_octaves.setter
    def transpose_octaves(self, value: int) -> None:
        self.set_property_value('transpose_octaves', value)

    def create_empty_measure(self, ref: Optional[pmodel.Measure]) -> ScoreMeasure:
        measure = down_cast(ScoreMeasure, super().create_empty_measure(ref))

        if ref is not None:
            ref = down_cast(ScoreMeasure, ref)
            measure.key_signature = ref.key_signature
            measure.clef = ref.clef

        return measure

    def create_node_connector(
            self, message_cb: Callable[[audioproc.ProcessorMessage], None]
    ) -> ScoreTrackConnector:
        return ScoreTrackConnector(node=self, message_cb=message_cb)