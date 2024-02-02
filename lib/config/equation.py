from enum import Enum
from typing import Any
from ..utils.encoding import make_int, make_float

_empty_list_types: list[type] = []

class DAQEquationOpcode(Enum):
    EXIT         = (0x00, _empty_list_types)
    PUSH_CHANNEL = (0x01, [int])
    PUSH_FLOAT   = (0x02, [float])
    UNARY_MINUS  = (0x04, _empty_list_types)
    SUBTRACT     = (0x05, _empty_list_types)
    ADD          = (0x06, _empty_list_types)
    MULTIPLY     = (0x07, _empty_list_types)
    DIVIDE       = (0x08, _empty_list_types)
    POWER        = (0x09, _empty_list_types)
    EXP          = (0x0A, _empty_list_types)
    LN           = (0x0B, _empty_list_types)
    LOG          = (0x0C, _empty_list_types)
    ABS          = (0x0D, _empty_list_types)
    INT          = (0x0E, _empty_list_types)
    SQRT         = (0x0F, _empty_list_types)

class DAQEquationOperation:
    opcode: DAQEquationOpcode
    params: list[Any]

    def __init__(self, opcode: DAQEquationOpcode, params: list[Any]) -> None:
        super().__init__()

        expected_types = opcode.value[1]
        if len(expected_types) != len(params):
            raise ValueError(f"Invalid number of arguments for opcode {opcode.name} (expected {len(expected_types)}, got {len(params)})")

        for i, (expected_type, arg) in enumerate(zip(expected_types, params)):
            if not isinstance(arg, expected_type):
                raise ValueError(f"Invalid type for argument {i} of opcode {opcode.name} (expected {expected_type}, got {type(arg)})")

        self.opcode = opcode
        self.params = params

    def encode(self) -> bytes:
        expected_types = self.opcode.value[1]

        payload = bytes([self.opcode.value[0]])
        for i, (expected_type, arg) in enumerate(zip(expected_types, self.params)):
            if not isinstance(arg, expected_type):
                raise ValueError(f"UNREACHABLE: Late invalid type for argument {i} of opcode {self.opcode.name} (expected {expected_type}, got {type(arg)})")

            if expected_type == int:
                payload += make_int(arg)
            elif expected_type == float:
                payload += make_float(arg)
            else:
                raise ValueError(f"UNREACHABLE: Invalid instruction parameter type {expected_type} for opcode {self.opcode.name}")

        return payload

class DAQEquation:
    ops: list[DAQEquationOperation]

    def __init__(self) -> None:
        super().__init__()
        self.ops = []

    def push_channel(self, channel: int) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.PUSH_CHANNEL, [channel]))
        return self

    def push_float(self, value: float) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.PUSH_FLOAT, [value]))
        return self

    def unary_minus(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.UNARY_MINUS, []))
        return self

    def subtract(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.SUBTRACT, []))
        return self

    def add(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.ADD, []))
        return self

    def multiply(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.MULTIPLY, []))
        return self

    def divide(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.DIVIDE, []))
        return self

    def power(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.POWER, []))
        return self

    def exp(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.EXP, []))
        return self

    def ln(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.LN, []))
        return self

    def log(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.LOG, []))
        return self

    def abs(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.ABS, []))
        return self

    def int(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.INT, []))
        return self

    def sqrt(self) -> "DAQEquation":
        self.ops.append(DAQEquationOperation(DAQEquationOpcode.SQRT, []))
        return self

    def encode(self) -> bytes:
        payload = b''
        for op in self.ops:
            payload += op.encode()
        return payload
