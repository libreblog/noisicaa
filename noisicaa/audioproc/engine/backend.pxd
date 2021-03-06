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

from libc.stdint cimport uint32_t
from libcpp.memory cimport unique_ptr
from libcpp.string cimport string

from noisicaa.core.status cimport Status, StatusOr
from noisicaa.host_system.host_system cimport HostSystem
from .realm cimport Realm, PyRealm
from .buffers cimport BufferPtr
from .block_context cimport BlockContext


cdef extern from "noisicaa/audioproc/engine/backend.h" namespace "noisicaa" nogil:
    cppclass Backend:
        enum Channel:
            AUDIO_LEFT "noisicaa::Backend::AUDIO_LEFT"
            AUDIO_RIGHT "noisicaa::Backend::AUDIO_RIGHT"
            EVENTS "noisicaa::Backend::EVENTS"

        @staticmethod
        StatusOr[Backend*] create(
            HostSystem* host_system, const string& name, const string& settings,
        void (*callback)(void*, const string&), void* userdata)

        Status setup(Realm* realm)
        void cleanup()
        Status begin_block(BlockContext* ctxt)
        Status end_block(BlockContext* ctxt)
        Status output(BlockContext* ctxt, Channel channel, BufferPtr samples)


cdef class PyBackend(object):
    cdef unique_ptr[Backend] __backend_ptr
    cdef Backend* __backend
    cdef readonly object notifications

    cdef Backend* get(self) nogil
    @staticmethod
    cdef void __notification_callback(void* c_self, const string& notification_serialized) with gil
