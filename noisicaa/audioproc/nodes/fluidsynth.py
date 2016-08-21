#!/usr/bin/python3

import logging
import queue
import time

from ..resample import (Resampler,
                        AV_CH_LAYOUT_STEREO,
                        AV_SAMPLE_FMT_S16,
                        AV_SAMPLE_FMT_FLT)
from .. import libfluidsynth
from ..exceptions import SetupError
from ..ports import EventInputPort, AudioOutputPort
from ..node import Node
from ..events import NoteOnEvent, NoteOffEvent, EndOfStreamEvent
from ..node_types import NodeType
from ..frame import Frame

logger = logging.getLogger(__name__)


class FluidSynthSource(Node):
    desc = NodeType()
    desc.name = 'fluidsynth'
    desc.port('in', 'input', 'events')
    desc.port('out', 'output', 'audio')
    desc.parameter('soundfont_path', 'path')
    desc.parameter('bank', 'int')
    desc.parameter('preset', 'int')

    master_synth = libfluidsynth.Synth()
    master_sfonts = {}

    def __init__(self, event_loop, name=None, id=None,
                 soundfont_path=None, bank=None, preset=None):
        super().__init__(event_loop, name, id)

        self._input = EventInputPort('in')
        self.add_input(self._input)

        self._output = AudioOutputPort('out')
        self.add_output(self._output)

        self._soundfont_path = soundfont_path
        self._bank = bank
        self._preset = preset

        self._synth = None
        self._sfont = None
        self._sfid = None
        self._resampler = None

    async def setup(self):
        await super().setup()

        assert self._synth is None

        self._synth = libfluidsynth.Synth(gain=0.5)
        try:
            sfont = self.master_sfonts[self._soundfont_path]
        except KeyError:
            logger.info(
                "Adding new soundfont %s to master synth.",
                self._soundfont_path)
            master_sfid = self.master_synth.sfload(self._soundfont_path)
            if master_sfid == -1:
                raise SetupError(
                    "Failed to load SoundFont %s" % self._soundfont_path)
            sfont = self.master_synth.get_sfont(master_sfid)
            self.master_sfonts[self._soundfont_path] = sfont

        logger.debug("Using soundfont %s", sfont)
        self._sfid = self._synth.add_sfont(sfont)
        logger.debug("Soundfont id=%s", self._sfid)
        if self._sfid == -1:
            raise SetupError(
                "Failed to add SoundFont %s" % self._soundfont_path)
        self._sfont = sfont

        self._synth.system_reset()
        self._synth.program_select(
            0, self._sfid, self._bank, self._preset)

        self._resampler = Resampler(
            AV_CH_LAYOUT_STEREO, AV_SAMPLE_FMT_S16, 44100,
            AV_CH_LAYOUT_STEREO, AV_SAMPLE_FMT_FLT, 44100)

    async def cleanup(self):
        await super().cleanup()

        self._resampler = None
        if self._synth is not None:
            self._synth.system_reset()
            if self._sfont is not None:
                # TODO: This call spits out a ton of "CRITICAL **:
                # fluid_synth_sfont_unref: assertion 'sfont_info != NULL' failed"
                # messages on STDERR
                self._synth.remove_sfont(self._sfont)
                self._sfont = None
            self._synth.delete()
            self._synth = None

    def run(self, ctxt):
        samples = bytes()
        tp = ctxt.sample_pos

        for event in self._input.events:
            if event.sample_pos != -1:
                assert ctxt.sample_pos <= event.sample_pos < ctxt.sample_pos + ctxt.duration, (
                    ctxt.sample_pos, event.sample_pos, ctxt.sample_pos + ctxt.duration)
                esample_pos = event.sample_pos
            else:
                esample_pos = ctxt.sample_pos

            if esample_pos > tp:
                samples += bytes(
                    self._synth.get_samples(esample_pos - tp))
                tp = esample_pos

            logger.info("Consuming event %s", event)

            if isinstance(event, NoteOnEvent):
                self._synth.noteon(
                    0, event.note.midi_note, event.volume)
            elif isinstance(event, NoteOffEvent):
                self._synth.noteoff(
                    0, event.note.midi_note)
            elif isinstance(event, EndOfStreamEvent):
                break
            else:
                raise NotImplementedError(
                    "Event class %s not supported" % type(event).__name__)

        if tp < ctxt.sample_pos + ctxt.duration:
            samples += bytes(
                self._synth.get_samples(
                    ctxt.sample_pos + ctxt.duration - tp))

        samples = self._resampler.convert(
            samples, len(samples) // 4)

        af = self._output.frame.audio_format
        frame = Frame(af, 0, set())
        frame.append_samples(
            samples, len(samples) // (
                # pylint thinks that frame.audio_format is a class object.
                # pylint: disable=E1101
                af.num_channels * af.bytes_per_sample))
        assert len(frame) == ctxt.duration

        self._output.frame.resize(ctxt.duration)
        self._output.frame.copy_from(frame)