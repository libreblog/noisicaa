// -*- mode: c++ -*-

/*
 * @begin:license
 *
 * Copyright (c) 2015-2019, Benjamin Niemann <pink@odahoda.de>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * @end:license
 */

#ifndef _NOISICAA_AUDIOPROC_ENGINE_CONTROL_VALUE_H
#define _NOISICAA_AUDIOPROC_ENGINE_CONTROL_VALUE_H

#include <string>
#include <stdint.h>

namespace noisicaa {

using namespace std;

enum ControlValueType {
  FloatCV,
  IntCV,
};

class ControlValue {
public:
  virtual ~ControlValue();

  ControlValueType type() const { return _type; }
  const char* type_name() const;
  const string& name() const { return _name; }
  uint32_t generation() const { return _generation; }
  virtual string formatted_value() const = 0;

protected:
  ControlValue(ControlValueType type, const string& name, uint32_t generation);

  void set_generation(uint32_t generation) { _generation = generation; }

private:
  ControlValueType _type;
  string _name;
  uint32_t _generation;
};

class FloatControlValue : public ControlValue {
public:
  FloatControlValue(const string& name, float value, uint32_t generation);

  string formatted_value() const;
  float value() const { return _value; }
  void set_value(float value, uint32_t generation) {
    _value = value;
    set_generation(generation);
  }

private:
  float _value;
};

class IntControlValue : public ControlValue {
public:
  IntControlValue(const string& name, int64_t value, uint32_t generation);

  string formatted_value() const;
  int64_t value() const { return _value; }
  void set_value(int64_t value, uint32_t generation) {
    _value = value;
    set_generation(generation);
  }

private:
  int64_t _value;
};

}  // namespace noisicaa

#endif
