#!/usr/bin/python3

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

import asyncio
import logging
from typing import Dict, Iterable, Set, Tuple

from noisicaa import core
from noisicaa.core import empty_message_pb2
from noisicaa.core import ipc
from . import node_db_pb2
from . import node_description_pb2

logger = logging.getLogger(__name__)


class NodeDBClient(object):
    def __init__(self, event_loop: asyncio.AbstractEventLoop, server: ipc.Server) -> None:
        self.event_loop = event_loop
        self.server = server

        self.mutation_handlers = core.Callback[node_db_pb2.Mutation]()

        self.__cb_endpoint_name = 'node_db_cb'
        self.__cb_endpoint_address = None  # type: str
        self.__stub = None  # type: ipc.Stub
        self.__nodes = {}  # type: Dict[str, node_description_pb2.NodeDescription]

    def get_node_description(self, uri: str) -> node_description_pb2.NodeDescription:
        return self.__nodes[uri]

    @property
    def nodes(self) -> Iterable[Tuple[str, node_description_pb2.NodeDescription]]:
        return sorted(self.__nodes.items())

    async def setup(self) -> None:
        cb_endpoint = ipc.ServerEndpoint(self.__cb_endpoint_name)
        cb_endpoint.add_handler(
            'NODEDB_MUTATION', self.__handle_mutation,
            node_db_pb2.Mutation, empty_message_pb2.EmptyMessage)
        self.__cb_endpoint_address = await self.server.add_endpoint(cb_endpoint)

    async def cleanup(self) -> None:
        await self.disconnect()

        if self.__cb_endpoint_address is not None:
            await self.server.remove_endpoint(self.__cb_endpoint_name)
            self.__cb_endpoint_address = None

    async def connect(self, address: str, flags: Set[str] = None) -> None:
        assert self.__stub is None
        self.__stub = ipc.Stub(self.event_loop, address)

        request = core.StartSessionRequest(
            callback_address=self.__cb_endpoint_address,
            flags=flags)
        await self.__stub.connect(request)

    async def disconnect(self) -> None:
        if self.__stub is not None:
            await self.__stub.close()
            self.__stub = None

    async def start_scan(self) -> None:
        await self.__stub.call('START_SCAN')

    def __handle_mutation(
            self,
            request: node_db_pb2.Mutation,
            response: empty_message_pb2.EmptyMessage
    ) -> None:
        logger.info("Mutation received: %s", request)
        if request.WhichOneof('type') == 'add_node':
            assert request.add_node.uri not in self.__nodes
            self.__nodes[request.add_node.uri] = request.add_node
        else:
            raise ValueError(request)

        self.mutation_handlers.call(request)
