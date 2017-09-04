#include "backend_ipc.h"
#include "audio_stream.h"
#include "misc.h"
#include "vm.h"

namespace noisicaa {

IPCBackend::IPCBackend(const BackendSettings& settings)
  : Backend(settings) {}
IPCBackend::~IPCBackend() {}

Status IPCBackend::setup(VM* vm) {
  Status status = Backend::setup(vm);
  if (status.is_error()) { return status; }

  if (_settings.ipc_address.size() == 0) {
    return Status::Error("ipc_address not set.");
  }

  _stream.reset(new AudioStreamServer(_settings.ipc_address));
  status = _stream->setup();
  if (status.is_error()) { return status; }

  for (int c = 0 ; c < 2 ; ++c) {
    _samples[c].reset(new BufferData[_block_size * sizeof(float)]);
  }

  vm->set_block_size(_block_size);

  return Status::Ok();
}

void IPCBackend::cleanup() {
  if (_stream.get() != nullptr) {
    _stream->cleanup();
    _stream.reset();
  }

  Backend::cleanup();
}

Status IPCBackend::begin_block() {
  // try:

  StatusOr<capnp::BlockData::Reader> stor_request = _stream->receive_block();
  if (stor_request.is_error()) { return stor_request; }
  capnp::BlockData::Reader request = stor_request.result();

  //     ctxt.perf.start_span('frame')

  //     ctxt.entities = {
  //         entity.id: entity
  //         for entity in in_frame.entities
  //     }
  //     ctxt.messages = in_frame.messages

  _out_block = _stream->block_data_builder();
  _out_block.setBlockSize(request.getBlockSize());
  _out_block.setSamplePos(request.getSamplePos());

  if (_block_size != request.getBlockSize()) {
    log(LogLevel::INFO, "Block size changed %d -> %d", _block_size, request.getBlockSize());
    _block_size = request.getBlockSize();
    for (int c = 0 ; c < 2 ; ++c) {
      _samples[c].reset(new BufferData[_block_size * sizeof(float)]);
    }
    _vm->set_block_size(_block_size);
  }

  for (int c = 0 ; c < 2 ; ++c) {
    _channel_written[c] = false;
  }

  // except audio_stream.StreamClosed:
  //     logger.warning("Stopping IPC backend.")
  //     self.stop()

  return Status::Ok();
}

Status IPCBackend::end_block() {
        // if self.__out_frame is not None:
        //     self.ctxt.perf.end_span()

  int num_buffers = 0;
  for (int c = 0 ; c < 2 ; ++c) {
    if (_channel_written[c]) {
      ++num_buffers;
    }
  }

  auto buffers = _out_block.initBuffers(num_buffers);
  int b = 0;
  for (int c = 0 ; c < 2 ; ++c) {
    if (_channel_written[c]) {
      auto buffer = buffers[b];

      char id[64];
      snprintf(id, sizeof(id), "output:%d", b);
      buffer.setId(id);

      auto data = buffer.initData(_block_size * sizeof(float));
      memmove(data.begin(), _samples[c].get(), _block_size * sizeof(float));

      ++b;
    }
  }

        //     assert self.ctxt.perf.current_span_id == 0
        //     self.__out_frame.perfData = self.ctxt.perf.serialize()

  Status status = _stream->send_block(_out_block);
  if (status.is_error()) { return status; }

        // self.__out_frame = None

  return Status::Ok();
}

Status IPCBackend::output(const string& channel, BufferPtr samples) {
  int c;
  if (channel == "left") {
    c = 0;
  } else if (channel == "right") {
    c = 1;
  } else {
    return Status::Error(sprintf("Invalid channel %s", channel.c_str()));
  }

  if (_channel_written[c]) {
    return Status::Error(sprintf("Channel %s written multiple times.", channel.c_str()));
  }
  _channel_written[c] = true;
  memmove(_samples[c].get(), samples, _block_size * sizeof(float));

  return Status::Ok();
}

}  // namespace noisicaa