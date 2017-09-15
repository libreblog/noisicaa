#!/usr/bin/python3

import enum
import textwrap


class NodeDescription(object):
    def __init__(self, *, display_name=None, ports=None, parameters=None):
        self.display_name = display_name
        self.ports = []
        if ports is not None:
            self.ports.extend(ports)
        self.parameters = []
        if parameters is not None:
            self.parameters.extend(parameters)

    def get_parameter(self, name):
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        raise KeyError("No parameter %r." % name)

    def __str__(self):
        s = []
        s.append("cls: %s" % type(self).__name__)
        s.append("display_name: %s" % self.display_name)
        s.append("%d ports" % len(self.ports))
        for port in self.ports:
            s.append(textwrap.indent(str(port), "  "))
        s.append("%d parameters" % len(self.parameters))
        for param in self.parameters:
            s.append(textwrap.indent(str(param), "  "))
        return '\n'.join(s)

class SystemNodeDescription(NodeDescription):
    pass


class UserNodeDescription(NodeDescription):
    def __init__(self, *, node_cls, **kwargs):
        super().__init__(**kwargs)
        self.node_cls = node_cls


class ProcessorDescription(NodeDescription):
    def __init__(self, *, processor_name, **kwargs):
        super().__init__(**kwargs)
        self.node_cls = 'processor'
        self.processor_name = processor_name


class PortType(enum.Enum):
    Audio = 'audio'
    ARateControl = 'arate_control'
    KRateControl = 'krate_control'
    Events = 'events'


class PortDirection(enum.Enum):
    Input = 'input'
    Output = 'output'


class PortDescription(object):
    def __init__(self, name, port_type, direction, bypass_port=None):
        self.name = name
        self.port_type = port_type
        self.direction = direction
        self.bypass_port = bypass_port

    def __str__(self):
        return "<Port name='%s' type=%s direction=%s>" % (
            self.name, self.port_type.name, self.direction.name)


class AudioPortDescription(PortDescription):
    def __init__(self, drywet_port=None, drywet_default=0.0, **kwargs):
        super().__init__(port_type=PortType.Audio, **kwargs)

        self.drywet_port = drywet_port
        self.drywet_default = drywet_default


class ARateControlPortDescription(PortDescription):
    def __init__(self, **kwargs):
        super().__init__(port_type=PortType.ARateControl, **kwargs)


class KRateControlPortDescription(PortDescription):
    def __init__(self, **kwargs):
        super().__init__(port_type=PortType.KRateControl, **kwargs)


class EventPortDescription(PortDescription):
    def __init__(self, csound_instr='1', **kwargs):
        super().__init__(port_type=PortType.Events, **kwargs)
        self.csound_instr = csound_instr


class ParameterType(enum.Enum):
    Internal = 'internal'
    String = 'string'
    Path = 'path'
    Text = 'text'
    Float = 'float'
    Int = 'int'


class ParameterDescription(object):
    def __init__(self, param_type, name, display_name=None):
        self.name = name
        self.display_name = display_name or name
        self.param_type = param_type

    def __str__(self):
        return "<Parameter name='%s' type=%s>" % (
            self.name, self.param_type.name)

    def validate(self, value):
        return value

    def to_string(self, value):
        return value

    def from_string(self, s):
        return s


class InternalParameterDescription(ParameterDescription):
    def __init__(self, value, **kwargs):
        super().__init__(param_type=ParameterType.Internal, **kwargs)
        self.value = value


class StringParameterDescription(ParameterDescription):
    def __init__(self, default='', **kwargs):
        super().__init__(param_type=ParameterType.String, **kwargs)
        self.default = default


class PathParameterDescription(ParameterDescription):
    def __init__(self, **kwargs):
        super().__init__(param_type=ParameterType.Path, **kwargs)


class TextParameterDescription(ParameterDescription):
    def __init__(self, content_type='text/plain', default='', **kwargs):
        super().__init__(param_type=ParameterType.Text, **kwargs)

        self.content_type = content_type
        self.default = default


class FloatParameterDescription(ParameterDescription):
    def __init__(self, min=0.0, max=1.0, default=0.0, **kwargs):
        super().__init__(param_type=ParameterType.Float, **kwargs)

        self.min = min
        self.max = max
        self.default = default

    def validate(self, value):
        if self.min is not None:
            value = max(self.min, value)
        if self.max is not None:
            value = min(self.max, value)
        return value

    def to_string(self, value):
        return str(value)

    def from_string(self, s):
        return float(s)

class IntParameterDescription(ParameterDescription):
    def __init__(self, min=None, max=None, default=0, **kwargs):
        super().__init__(param_type=ParameterType.Int, **kwargs)

        self.min = min
        self.max = max
        self.default = default

    def validate(self, value):
        if self.min is not None:
            value = max(self.min, value)
        if self.max is not None:
            value = min(self.max, value)
        return value

    def to_string(self, value):
        return str(value)

    def from_string(self, s):
        return int(s)
