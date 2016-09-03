#!/usr/bin/python3

import logging
import os
import os.path
from xml.etree import ElementTree

from noisicaa import core
from noisicaa import constants
from noisicaa import node_db

from . import csound_scanner

logger = logging.getLogger(__name__)


class NodeDB(object):
    def __init__(self):
        self._nodes = {}
        self.listeners = core.CallbackRegistry()

    def setup(self):
        scanners = [csound_scanner.CSoundScanner()]
        for scanner in scanners:
            for uri, node_description in scanner.scan():
                assert uri not in self._nodes
                self._nodes[uri] = node_description

    def cleanup(self):
        pass

    def initial_mutations(self):
        for uri, node_description in sorted(self._nodes.items()):
            yield node_db.AddNodeDescription(uri, node_description)

    def start_scan(self):
        pass