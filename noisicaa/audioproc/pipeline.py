#!/usr/bin/python3

import logging
import mmap
import threading
import os
import pprint
import sys
import time

import toposort

from ..rwlock import RWLock
from .exceptions import Error
from noisicaa import core
from . import data
from . import ports

logger = logging.getLogger(__name__)


# TODO
# - audio ports get their format's sample rate from pipeline


class Pipeline(object):
    def __init__(self, shm=None):
        self._shm = shm
        self._shm_data = None
        self._crasher_id = None
        self._sample_rate = 44100
        self._frame_size = 1024
        self._nodes = set()
        self._backend = None
        self._thread = None
        self._started = threading.Event()
        self._stopping = threading.Event()
        self._running = False
        self._lock = RWLock()
        self.utilization_callback = None

        self._notifications = []
        self.notification_listener = core.CallbackRegistry()

        self.listeners = core.CallbackRegistry()

        self._mainloop_logging = False

    @property
    def sample_rate(self):
        return self._sample_rate

    def reader_lock(self):
        return self._lock.reader_lock

    def writer_lock(self):
        return self._lock.writer_lock

    @property
    def running(self):
        return self._running

    def clear(self):
        assert not self._running
        self._nodes = set()
        self._backend = None

    def start(self):
        assert not self._running
        self._running = True

        self._crasher_id = None
        if self._shm is not None:
            assert self._shm.size >= 1024, self._shm.size
            self._shm_data = mmap.mmap(self._shm.fd, 1024)

            if self._shm_data[512] != 0:
                id_encoded = self._shm_data[512:1024]
                eos = id_encoded.find(0)
                if eos != -1:
                    id_encoded = id_encoded[:eos]
                self._crasher_id = id_encoded.decode('ascii')

            elif self._shm_data[0] != 0:
                id_encoded = self._shm_data[0:512]
                eos = id_encoded.find(0)
                if eos != -1:
                    id_encoded = id_encoded[:eos]
                self._crasher_id = id_encoded.decode('ascii')

            if self._crasher_id is not None:
                logger.info("Crasher ID: %s", self._crasher_id)

        self._stopping.clear()
        self._started.clear()
        self._thread = threading.Thread(target=self.mainloop)
        self._thread.start()
        self._started.wait()
        logger.info("Pipeline running.")

    def stop(self):
        if self._backend is not None:
            logger.info("Stopping backend...")
            self._backend.stop()
            logger.info("Backend stopped...")

        if self._thread is not None:
            logger.info("Stopping pipeline thread...")
            self._stopping.set()
            self.wait()
            logger.info("Pipeline thread stopped.")
            self._thread = None

        if self._backend is not None:
            self._backend.cleanup()
            self._backend = None

        if self._shm_data is not None:
            self._shm_data.close()
            self._shm_data = None

        self._running = False

    def wait(self):
        if self._thread is not None:
            self._thread.join()

    def dump(self):
        d = {}
        for node in self._nodes:
            n = {}
            for pn, p in node.inputs.items():
                n[pn] = []
                for up in p.inputs:
                    n[pn].append(
                        '%s(%s:%s)' % (
                            up.owner.name, up.owner.id, up.name))
            d['%s(%s)' % (node.name, node.id)] = n

        logger.info("Pipeline dump:\n%s", pprint.pformat(d))
        logger.info("%s", dict((node.name, [n.name for n in node.parent_nodes])
                               for node in self._nodes))

    def mainloop(self):
        try:
            logger.info("Starting mainloop...")
            self._started.set()
            ctxt = data.FrameContext()
            ctxt.perf = core.PerfStats()
            ctxt.sample_pos = 0
            ctxt.duration = self._frame_size

            while not self._stopping.is_set():
                backend = self._backend
                if backend is None:
                    time.sleep(0.1)
                    continue

                ctxt.in_frame = None
                ctxt.out_frame = None

                t0 = time.time()
                with ctxt.perf.track('backend_wait'):
                    backend.wait(ctxt)
                if backend.stopped:
                    break

                self.listeners.call('perf_data', ctxt.perf.get_spans())

                ctxt.perf = core.PerfStats()

                with ctxt.perf.track('frame(%d)' % ctxt.sample_pos):
                    with ctxt.perf.track('process'):
                        t1 = time.time()
                        if self._mainloop_logging:
                            logger.debug("Processing frame @%d", ctxt.sample_pos)

                        self.process_frame(ctxt)

                    notifications = self._notifications
                    self._notifications = []

                    with ctxt.perf.track('send_notifications'):
                        for node_id, notification in notifications:
                            if self._mainloop_logging:
                                logger.info(
                                    "Node %s fired notification %s",
                                    node_id, notification)
                            self.notification_listener.call(
                                node_id, notification)

                    t2 = time.time()
                    if t2 - t0 > 0:
                        utilization = (t2 - t1) / (t2 - t0)
                        # if self.utilization_callback is not None:
                        #     self.utilization_callback(utilization)

                backend.write(ctxt)
                ctxt.sample_pos += ctxt.duration
                ctxt.duration = self._frame_size

        except:  # pylint: disable=bare-except
            sys.stdout.flush()
            sys.excepthook(*sys.exc_info())
            sys.stderr.flush()
            os._exit(1)

        finally:
            logger.info("Mainloop finished.")

    def process_frame(self, ctxt):
        with self.reader_lock():
            assert not self._notifications

            with ctxt.perf.track('sort_nodes'):
                nodes = self.sorted_nodes
            for node in nodes:
                if node.broken:
                    for port in node.outputs.values():
                        if isinstance(port, ports.AudioOutputPort):
                            port.frame.resize(ctxt.duration)
                            port.frame.clear()
                        elif isinstance(port, ports.ControlOutputPort):
                            port.frame.resize(ctxt.duration)
                            port.frame.fill(0.0)
                        elif isinstance(port, ports.EventOutputPort):
                            port.events.clear()
                        else:
                            raise ValueError(port)
                    continue

                if self._mainloop_logging:
                    logger.debug("Running node %s", node.name)
                with ctxt.perf.track('collect_inputs(%s)' % node.id):
                    node.collect_inputs(ctxt)
                with ctxt.perf.track('run(%s)' % node.id):
                    if self._shm_data is not None:
                        marker = node.id.encode('ascii') + b'\0'
                        self._shm_data[0:len(marker)] = marker
                    node.run(ctxt)
                    if self._shm_data is not None:
                        self._shm_data[0] = 0
                with ctxt.perf.track('post_run(%s)' % node.id):
                    node.post_run(ctxt)

    def add_notification(self, node_id, notification):
        self._notifications.append((node_id, notification))

    @property
    def sorted_nodes(self):
        graph = dict((node, set(node.parent_nodes))
                     for node in self._nodes)
        try:
            return toposort.toposort_flatten(graph, sort=False)
        except ValueError as exc:
            raise Error(exc.args[0]) from exc

    def find_node(self, node_id):
        for node in self._nodes:
            if node.id == node_id:
                return node
        raise Error("Unknown node %s" % node_id)

    async def setup_node(self, node):
        if node.id == self._crasher_id:
            logger.warning(
                "Node %s (%s) has been deactivated, because it crashed the pipeline.",
                node.id, type(node).__name__)
            self.listeners.call('node_state', node.id, broken=True)
            node.broken = True
            return

        if self._shm_data is not None:
            marker = node.id.encode('ascii') + b'\0'
            self._shm_data[512:512+len(marker)] = marker
        await node.setup()
        if self._shm_data is not None:
            self._shm_data[512] = 0

    def add_node(self, node):
        if node.pipeline is not None:
            raise Error("Node has already been added to a pipeline")
        node.pipeline = self
        self._nodes.add(node)

    def remove_node(self, node):
        if node.pipeline is not self:
            raise Error("Node has not been added to this pipeline")
        node.pipeline = None
        self._nodes.remove(node)

    def set_backend(self, backend):
        with self.writer_lock():
            if self._backend is not None:
                logger.info(
                    "Clean up backend %s", type(self._backend).__name__)
                self._backend.cleanup()
                self._backend = None

            if backend is not None:
                logger.info(
                    "Set up backend %s", type(backend).__name__)
                backend.setup(self._sample_rate)
                self._backend = backend

    def set_frame_size(self, frame_size):
        with self.writer_lock():
            self._frame_size = frame_size

    @property
    def backend(self):
        return self._backend
