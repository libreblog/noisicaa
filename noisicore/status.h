// -*- mode: c++ -*-

#ifndef _NOISICORE_STATUS_H
#define _NOISICORE_STATUS_H

#include <string>
#include <assert.h>

namespace noisicaa {

using namespace std;

class Status {
public:
  enum Code {
    OK,
    ERROR,
  };

  Status()
    : _code(Code::ERROR),
      _message("Uninitialized status") {
  }

  Status(Code code, const string& message)
    : _code(code),
      _message(message) {
  }

  Status(const Status& s)
    : _code(s._code),
      _message(s._message) {
  }

  Code code() const { return _code; }
  bool is_error() const { return _code == Code::ERROR; }
  string message() const { return _message; }

  static Status Ok() { return Status(Code::OK, ""); }
  static Status Error(const string& message) { return Status(Code::ERROR, message); }

private:
  Code _code;
  string _message;
};

template<class T> class StatusOr : public Status {
public:
  StatusOr()
    : Status(),
      _result() {}

  StatusOr(const StatusOr& s)
    : Status(s),
      _result(s._result) {}

  StatusOr(const Status& s)
    : Status(s),
      _result() {}

  StatusOr(T result)
    : Status(Code::OK, ""),
      _result(result) {}

  T result() const { assert(!is_error()); return _result; }

private:
  T _result;
};

}  // namespace noisicaa

#endif
