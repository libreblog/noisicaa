from libcpp.memory cimport unique_ptr
from libcpp.string cimport string


class Error(Exception):
    pass


class ConnectionClosed(Exception):
    pass


cdef class AudioStream(object):
    cdef unique_ptr[AudioStreamBase] stream

    def __init__(self):
        raise TypeError("Instances must be created with create_server/create_client.")

    @classmethod
    def create_server(self, const string& address):
        cdef AudioStream obj = AudioStream.__new__(AudioStream)
        obj.stream.reset(new AudioStreamServer(address))
        return obj

    @classmethod
    def create_client(self, const string& address):
        cdef AudioStream obj = AudioStream.__new__(AudioStream)
        obj.stream.reset(new AudioStreamClient(address))
        return obj

    cdef _check(self, const Status& status):
        if status.is_connection_closed():
            raise ConnectionClosed()

        if status.is_error():
            raise Error(status.message())

    def setup(self):
        cdef AudioStreamBase* stream = self.stream.get()

        cdef Status status
        with nogil:
            status = stream.setup()
        self._check(status)

    def cleanup(self):
        cdef AudioStreamBase* stream = self.stream.get()
        with nogil:
            stream.cleanup()

    def close(self):
        cdef AudioStreamBase* stream = self.stream.get()
        with nogil:
            stream.close()

    def receive_bytes(self):
        cdef AudioStreamBase* stream = self.stream.get()

        cdef StatusOr[string] status_or_bytes
        with nogil:
            status_or_bytes = stream.receive_bytes();
        self._check(status_or_bytes)

        return bytes(status_or_bytes.result())

    def send_bytes(self, const string& block_bytes):
        cdef AudioStreamBase* stream = self.stream.get()

        cdef Status status
        with nogil:
            status = stream.send_bytes(block_bytes);
        self._check(status)