#!/usr/bin/python3

import unittest

from noisicaa.audioproc import data
from noisicaa.bindings import lv2
from . cimport fluidsynth
from ..vm cimport buffers


class FluidSynthSourceTest(unittest.TestCase):
    def test_basic(self):
        cdef:
            fluidsynth.FluidSynthSource node
            buffers.Buffer buf_in
            buffers.Buffer buf_out_l
            buffers.Buffer buf_out_r

        node = fluidsynth.FluidSynthSource(
            id='test',
            soundfont_path='/usr/share/sounds/sf2/TimGM6mb.sf2', bank=0, preset=0)
        node.setup()
        try:
            buf_in = buffers.Buffer(buffers.AtomData(10240))
            buf_out_l = buffers.Buffer(buffers.FloatArray(256))
            buf_out_r = buffers.Buffer(buffers.FloatArray(256))
            node.connect_port('in', buf_in)
            node.connect_port('out:left', buf_out_l)
            node.connect_port('out:right', buf_out_r)

            forge = lv2.AtomForge(lv2.static_mapper)
            forge.set_buffer(buf_in.data, 10240)
            with forge.sequence():
                forge.write_midi_event(0, bytes([0x90, 60, 100]), 3)
                forge.write_midi_event(128, bytes([0x80, 60, 0]), 3)

            ctxt = data.FrameContext()
            ctxt.sample_pos = 0
            ctxt.duration = 256
            node.run(ctxt)

        finally:
            node.cleanup()


if __name__ == '__main__':
    unittest.main()