# @begin:license
#
# Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
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

from typing import Iterator, List, Tuple

class Node(object):
    def __str__(self) -> str: ...
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...
    def __bool__(self) -> bool: ...
    def is_int(self) -> bool: ...

class Nodes(object):
    def __iter__(self) -> Iterator[Node]: ...

class UI(object):
    @property
    def required_features(self) -> List[str]: ...
    @property
    def optional_features(self) -> List[str]: ...
    @property
    def uri(self) -> str: ...
    @property
    def binary_path(self) -> str: ...
    @property
    def bundle_path(self) -> str: ...
    def get_classes(self) -> Nodes: ...

class UIs(object):
    def __iter__(self) -> Iterator[UI]: ...

class Port(object):
    def get_symbol(self) -> Node: ...
    def get_name(self) -> Node: ...
    def get_range(self) -> Tuple[Node, Node, Node]: ...
    def is_a(self, port_class: Node) -> bool: ...

class Plugin(object):
    @property
    def required_features(self) -> List[str]: ...
    @property
    def optional_features(self) -> List[str]: ...
    def get_uri(self) -> Node: ...
    def get_name(self) -> Node: ...
    def get_port_by_index(self, index: int) -> Port: ...
    def get_num_ports(self) -> int: ...
    def get_uis(self) -> UIs: ...

class Plugins(object):
    def __iter__(self) -> Iterator[Plugin]: ...

class Namespace(object):
    def __getattr__(self, suffix: str) -> Node: ...

class Namespaces(object):
    atom = ...  # type: Namespace
    doap = ...  # type: Namespace
    foaf = ...  # type: Namespace
    lilv = ...  # type: Namespace
    lv2  = ...  # type: Namespace
    midi = ...  # type: Namespace
    owl  = ...  # type: Namespace
    rdf  = ...  # type: Namespace
    rdfs = ...  # type: Namespace
    ui   = ...  # type: Namespace
    xsd  = ...  # type: Namespace

class World(object):
    ns = ...  # type: Namespaces

    def load_all(self) -> None: ...
    def get_all_plugins(self) -> Plugins: ...