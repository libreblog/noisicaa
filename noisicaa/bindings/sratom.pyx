from libc.stdint cimport uint8_t
from libc cimport stdlib

from .lv2 cimport (
    URID_Mapper,
    URID_Map_Feature,
    URID_Unmap_Feature,
    LV2_Atom,
)

def atom_to_turtle(URID_Mapper mapper, const uint8_t* atom):
    cdef URID_Map_Feature map = URID_Map_Feature(mapper)
    cdef URID_Unmap_Feature unmap = URID_Unmap_Feature(mapper)

    cdef LV2_Atom* obj = <LV2_Atom*>atom

    cdef Sratom* sratom
    cdef char* turtle
    sratom = sratom_new(&map.data)
    assert sratom != NULL
    try:
        sratom_set_pretty_numbers(sratom, True)

        turtle = sratom_to_turtle(
            sratom, &unmap.data,
            b'http://example.org', NULL, NULL,
            obj.type, obj.size, <void*>(<uint8_t*>(obj) + sizeof(LV2_Atom)))
        try:
            return turtle.decode('utf-8')
        finally:
            stdlib.free(turtle)
    finally:
        sratom_free(sratom)
