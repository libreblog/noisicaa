from libc cimport stdlib

import unittest

from . cimport lv2
from . import sratom


class URIDTest(unittest.TestCase):
    def test_map(self):
        cdef lv2.URID_Mapper mapper
        cdef lv2.URID_Map_Feature feature
        cdef lv2.LV2_Feature* lv2_feature
        cdef lv2.LV2_URID_Map* map_feature

        mapper = lv2.URID_Mapper()
        feature = lv2.URID_Map_Feature(mapper)
        lv2_feature = &feature.lv2_feature

        self.assertEqual(lv2_feature.URI, b'http://lv2plug.in/ns/ext/urid#map')

        map_feature = <lv2.LV2_URID_Map*>lv2_feature.data
        urid1 = map_feature.map(map_feature.handle, b'http://example.org/foo')
        self.assertGreater(urid1, 0)

        urid2 = map_feature.map(map_feature.handle, b'http://example.org/bar')
        self.assertNotEqual(urid1, urid2)

    def test_unmap(self):
        cdef lv2.URID_Mapper mapper
        cdef lv2.URID_Map_Feature map_feature
        cdef lv2.LV2_Feature* map_lv2_feature
        cdef lv2.LV2_URID_Map* map
        cdef lv2.URID_Unmap_Feature unmap_feature
        cdef lv2.LV2_Feature* unmap_lv2_feature
        cdef lv2.LV2_URID_Unmap* unmap

        mapper = lv2.URID_Mapper()
        map_feature = lv2.URID_Map_Feature(mapper)
        map_lv2_feature = &map_feature.lv2_feature

        map = <lv2.LV2_URID_Map*>map_lv2_feature.data

        unmap_feature = lv2.URID_Unmap_Feature(mapper)
        unmap_lv2_feature = &unmap_feature.lv2_feature
        self.assertEqual(unmap_lv2_feature.URI, b'http://lv2plug.in/ns/ext/urid#unmap')

        unmap = <lv2.LV2_URID_Unmap*>unmap_lv2_feature.data
        self.assertTrue(unmap.unmap(unmap.handle, 100) == NULL)

        urid = map.map(map.handle, b'http://example.org/foo')
        self.assertEqual(unmap.unmap(unmap.handle, urid), b'http://example.org/foo')


class AtomForgeTest(unittest.TestCase):
    def test_forge(self):
        buf = bytearray(1024)

        mapper = lv2.URID_Mapper()

        forge = lv2.AtomForge(mapper)
        forge.set_buffer(buf, 1024)

        with forge.sequence():
            forge.write_midi_event(0, b'abc', 3)
            forge.write_midi_event(1, b'abc', 3)

        print(sratom.atom_to_turtle(mapper, buf))
