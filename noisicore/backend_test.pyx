from libcpp.memory cimport unique_ptr

from .buffers cimport *
from .status cimport *
from .backend cimport *

import unittest


class TestPortAudioBackend(unittest.TestCase):
    def test_foo(self):
        cdef Status status
        cdef float samples[128]

        cdef unique_ptr[Backend] beptr
        beptr.reset(Backend.create(b"portaudio"))

        cdef Backend* be = beptr.get()
        status = be.setup()
        try:
            self.assertFalse(status.is_error(), status.message())

            for _ in range(100):
                status = be.begin_frame()
                self.assertFalse(status.is_error(), status.message())

                for i in range(128):
                    samples[i] = i / 128.0
                status = be.output(b"left", <BufferPtr>samples)
                self.assertFalse(status.is_error(), status.message())
                status = be.output(b"right", <BufferPtr>samples)
                self.assertFalse(status.is_error(), status.message())

                status = be.end_frame()
                self.assertFalse(status.is_error(), status.message())

        finally:
            status = be.cleanup()
            self.assertFalse(status.is_error(), status.message())