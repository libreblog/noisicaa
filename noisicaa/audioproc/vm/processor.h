// -*- mode: c++ -*-

#ifndef _NOISICAA_AUDIOPROC_VM_PROCESSOR_H
#define _NOISICAA_AUDIOPROC_VM_PROCESSOR_H

#include <map>
#include <memory>
#include <string>
#include <stdint.h>
#include "noisicaa/core/logging.h"
#include "noisicaa/core/status.h"
#include "noisicaa/audioproc/vm/buffers.h"
#include "noisicaa/audioproc/vm/block_context.h"
#include "noisicaa/audioproc/vm/processor_spec.h"

namespace noisicaa {

using namespace std;

class HostData;
class NotificationQueue;

class Processor {
public:
  Processor(const string& node_id, const char* logger_name, HostData* host_data);
  virtual ~Processor();

  static StatusOr<Processor*> create(
      const string& node_id, HostData* host_data, const string& name);

  uint64_t id() const { return _id; }
  const string& node_id() const { return _node_id; }

  StatusOr<string> get_string_parameter(const string& name);
  Status set_string_parameter(const string& name, const string& value);

  StatusOr<int64_t> get_int_parameter(const string& name);
  Status set_int_parameter(const string& name, int64_t value);

  StatusOr<float> get_float_parameter(const string& name);
  Status set_float_parameter(const string& name, float value);

  virtual Status setup(const ProcessorSpec* spec);
  virtual void cleanup();

  virtual Status connect_port(uint32_t port_idx, BufferPtr buf) = 0;
  virtual Status run(BlockContext* ctxt) = 0;

protected:
  Logger* _logger;
  HostData* _host_data;
  uint64_t _id;
  string _node_id;
  unique_ptr<const ProcessorSpec> _spec;
  map<string, string> _string_parameters;
  map<string, int64_t> _int_parameters;
  map<string, float> _float_parameters;

  static uint64_t new_id();
};

}  // namespace noisicaa

#endif
