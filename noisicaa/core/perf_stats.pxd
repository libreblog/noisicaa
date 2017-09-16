from libc.stdint cimport uint64_t
from libcpp.memory cimport unique_ptr
from libcpp.string cimport string

cdef extern from "noisicaa/core/perf_stats.h" namespace "noisicaa" nogil:
    cppclass PerfStats:
        struct Span:
            uint64_t id
            string name
            uint64_t parent_id
            uint64_t start_time_nsec
            uint64_t end_time_nsec

        ctypedef uint64_t (*clock_func_t)(void*)

        PerfStats()
        PerfStats(clock_func_t clock, void* clock_data)

        void start_span(const string& name, uint64_t parent_id)
        void start_span(const string& name)
        void end_span()
        void append_span(const Span& span)
        uint64_t current_span_id() const
        int num_spans() const
        Span span(int idx) const


cdef class PyPerfStats(object):
    cdef unique_ptr[PerfStats] __stats
    cdef object __clock

    cdef PerfStats* get(self)
    @staticmethod
    cdef uint64_t __clock_cb(void* data)
