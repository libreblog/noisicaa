// -*- mode: c++ -*-

#ifndef _NOISICAA_AUDIOPROC_VM_VM_H
#define _NOISICAA_AUDIOPROC_VM_VM_H

#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include <stdint.h>
#include "noisicaa/core/logging.h"
#include "noisicaa/core/status.h"
#include "noisicaa/audioproc/vm/control_value.h"
#include "noisicaa/audioproc/vm/spec.h"
#include "noisicaa/audioproc/vm/processor.h"

namespace noisicaa {

using namespace std;

class Backend;
class BlockContext;
class HostData;
class NotificationQueue;

class Program {
public:
  Program(Logger* logger, uint32_t version);
  ~Program();

  Status setup(HostData* host_data, const Spec* spec, uint32_t block_size);

  uint32_t version = 0;
  bool initialized = false;
  unique_ptr<const Spec> spec;
  uint32_t block_size;
  vector<unique_ptr<Buffer>> buffers;

private:
  Logger* _logger;
};

struct ProgramState {
  Logger* logger;
  HostData* host_data;
  Program* program;
  Backend* backend;
  int p;
  bool end;
};

struct ActiveProcessor {
  ActiveProcessor(Processor* processor) : processor(processor), ref_count(0) {}

  unique_ptr<Processor> processor;
  int ref_count;
};

struct ActiveControlValue {
  ActiveControlValue(ControlValue* cv) : control_value(cv), ref_count(0) {}

  unique_ptr<ControlValue> control_value;
  int ref_count;
};

class VM {
public:
  VM(HostData* host_data);
  ~VM();

  Status setup();
  void cleanup();

  Status add_processor(Processor* processor);
  Status add_control_value(ControlValue* cv);

  Status set_block_size(uint32_t block_size);
  Status set_spec(const Spec* spec);

  Status set_float_control_value(const string& name, float value);

  Status process_block(Backend* backend, BlockContext* ctxt);

  Buffer* get_buffer(const string& name);

private:
  void activate_program(Program* program);
  void deactivate_program(Program* program);

  Logger* _logger;
  HostData* _host_data;
  atomic<uint32_t> _block_size;
  atomic<Program*> _next_program;
  atomic<Program*> _current_program;
  atomic<Program*> _old_program;
  uint32_t _program_version = 0;
  map<uint64_t, unique_ptr<ActiveProcessor>> _processors;
  map<string, unique_ptr<ActiveControlValue>> _control_values;
};

}  // namespace noisicaa

#endif
