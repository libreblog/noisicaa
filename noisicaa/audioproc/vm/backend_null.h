// -*- mode: c++ -*-

#ifndef _NOISICAA_AUDIOPROC_VM_BACKEND_NULL_H
#define _NOISICAA_AUDIOPROC_VM_BACKEND_NULL_H

#include <string.h>
#include "noisicaa/core/status.h"
#include "noisicaa/audioproc/vm/backend.h"
#include "noisicaa/audioproc/vm/buffers.h"

namespace noisicaa {

class VM;

class NullBackend : public Backend {
 public:
  NullBackend(const BackendSettings& settings);
  ~NullBackend() override;

  Status setup(VM* vm) override;
  void cleanup() override;

  Status set_block_size(uint32_t block_size) override;

  Status begin_block(BlockContext* ctxt) override;
  Status end_block(BlockContext* ctxt) override;
  Status output(BlockContext* ctxt, const string& channel, BufferPtr samples) override;

private:
  uint32_t _new_block_size;
};

}  // namespace noisicaa

#endif
