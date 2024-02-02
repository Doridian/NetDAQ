from enum import Enum
from typing import Any, cast
from ..utils.encoding import make_int, make_float
from dataclasses import dataclass

@dataclass(frozen=True, eq=True)
class DAQEquationOpcodeConfig:
    code: int
    args: list[type[int] | type[float]]
    pops: int
    pushes: int

class DAQEquationOpcode(Enum):
    EXIT         = DAQEquationOpcodeConfig(0x00, [], 1, 0)
    PUSH_CHANNEL = DAQEquationOpcodeConfig(0x01, [int], 0, 1)
    PUSH_FLOAT   = DAQEquationOpcodeConfig(0x02, [float], 0, 1)
    UNARY_MINUS  = DAQEquationOpcodeConfig(0x04, [], 1, 1)
    SUBTRACT     = DAQEquationOpcodeConfig(0x05, [], 2, 1)
    ADD          = DAQEquationOpcodeConfig(0x06, [], 2, 1)
    MULTIPLY     = DAQEquationOpcodeConfig(0x07, [], 2, 1)
    DIVIDE       = DAQEquationOpcodeConfig(0x08, [], 2, 1)
    POWER        = DAQEquationOpcodeConfig(0x09, [], 2, 1)
    EXP          = DAQEquationOpcodeConfig(0x0A, [], 1, 1)
    LN           = DAQEquationOpcodeConfig(0x0B, [], 1, 1)
    LOG          = DAQEquationOpcodeConfig(0x0C, [], 1, 1)
    ABS          = DAQEquationOpcodeConfig(0x0D, [], 1, 1)
    INT          = DAQEquationOpcodeConfig(0x0E, [], 1, 1)
    SQRT         = DAQEquationOpcodeConfig(0x0F, [], 1, 1)

class DAQEquationOperation:
    opcode: DAQEquationOpcode
    params: list[Any]

    def __init__(self, opcode: DAQEquationOpcode, params: list[Any]) -> None:
        super().__init__()

        expected_types = opcode.value.args
        if len(expected_types) != len(params):
            raise ValueError(f"Invalid number of arguments for opcode {opcode.name} (expected {len(expected_types)}, got {len(params)})")

        for i, (expected_type, arg) in enumerate(zip(expected_types, params)):
            if not isinstance(arg, expected_type):
                raise ValueError(f"Invalid type for argument {i} of opcode {opcode.name} (expected {expected_type}, got {type(arg)})")

        self.opcode = opcode
        self.params = params

    def encode(self) -> bytes:
        expected_types = self.opcode.value.args

        payload = bytes([self.opcode.value.code])
        for i, (expected_type, arg) in enumerate(zip(expected_types, self.params)):
            if not isinstance(arg, expected_type):
                raise ValueError(f"UNREACHABLE: Late invalid type for argument {i} of opcode {self.opcode.name} (expected {expected_type}, got {type(arg)})")

            if expected_type == int:
                payload += make_int(cast(int, arg))
            elif expected_type == float:
                payload += make_float(cast(float, arg))
            else:
                raise ValueError(f"UNREACHABLE: Invalid instruction parameter type {expected_type} for opcode {self.opcode.name}")

        return payload

class DAQEquation:
    _ops: list[DAQEquationOperation]
    _has_end: bool = False
    _stack_depth: int = 0

    def __init__(self) -> None:
        super().__init__()
        self._ops = []

    def _push_op(self, op: DAQEquationOperation) -> None:
        if self._has_end:
            raise ValueError("Cannot add operation to equation after end opcode")

        if op.opcode == DAQEquationOpcode.EXIT:
            if self._stack_depth != 1:
                raise ValueError(f"Invalid stack depth at end of equation (expected 1, got {self._stack_depth})")
            self._has_end = True

        opcode = op.opcode.value

        if self._stack_depth < opcode.pops:
            raise ValueError(f"Stack underflow for opcode {op.opcode.name} (expected >= {opcode.pops} elements, got {self._stack_depth})")
        
        self._stack_depth -= opcode.pops
        self._stack_depth += opcode.pushes

        self._ops.append(op)

    def clear(self) -> "DAQEquation":
        self._ops = []
        self._has_end = False
        self._stack_depth = 0
        return self

    def end(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.EXIT, []))
        return self

    def push_channel(self, channel: int) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.PUSH_CHANNEL, [channel]))
        return self

    def push_float(self, value: float) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.PUSH_FLOAT, [value]))
        return self

    def unary_minus(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.UNARY_MINUS, []))
        return self

    def subtract(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.SUBTRACT, []))
        return self

    def add(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.ADD, []))
        return self

    def multiply(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.MULTIPLY, []))
        return self

    def divide(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.DIVIDE, []))
        return self

    def power(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.POWER, []))
        return self

    def exp(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.EXP, []))
        return self

    def ln(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.LN, []))
        return self

    def log(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.LOG, []))
        return self

    def abs(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.ABS, []))
        return self

    def int(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.INT, []))
        return self

    def sqrt(self) -> "DAQEquation":
        self._push_op(DAQEquationOperation(DAQEquationOpcode.SQRT, []))
        return self

    def encode(self) -> bytes:
        if not self._has_end:
            raise ValueError("Cannot encode equation without end opcode")

        payload = b''
        for op in self._ops:
            payload += op.encode()
        return payload
