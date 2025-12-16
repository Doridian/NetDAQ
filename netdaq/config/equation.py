from enum import Enum
from typing import Any, cast, override
from .base import ConfigError
from ..utils.encoding import make_int, make_float, make_double
from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class DAQEquationOpcodeConfig:
    code: int
    args: list[type[int] | type[float]]
    lengths: list[int]
    pops: int
    pushes: int

class DAQEquationOpcode(Enum):
    END = DAQEquationOpcodeConfig(0x00, [], [], 1, 0)
    PUSH_CHANNEL = DAQEquationOpcodeConfig(0x01, [int], [2], 0, 1)
    PUSH_FLOAT = DAQEquationOpcodeConfig(0x02, [float], [4], 0, 1)
    PUSH_DOUBLE = DAQEquationOpcodeConfig(0x03, [float], [8], 0, 1)
    UNARY_MINUS = DAQEquationOpcodeConfig(0x04, [], [], 1, 1)
    SUBTRACT = DAQEquationOpcodeConfig(0x05, [], [], 2, 1)
    ADD = DAQEquationOpcodeConfig(0x06, [], [], 2, 1)
    MULTIPLY = DAQEquationOpcodeConfig(0x07, [], [], 2, 1)
    DIVIDE = DAQEquationOpcodeConfig(0x08, [], [], 2, 1)
    POWER = DAQEquationOpcodeConfig(0x09, [], [], 2, 1)
    EXP = DAQEquationOpcodeConfig(0x0A, [], [], 1, 1)
    LN = DAQEquationOpcodeConfig(0x0B, [], [], 1, 1)
    LOG = DAQEquationOpcodeConfig(0x0C, [], [], 1, 1)
    ABS = DAQEquationOpcodeConfig(0x0D, [], [], 1, 1)
    INT = DAQEquationOpcodeConfig(0x0E, [], [], 1, 1)
    SQRT = DAQEquationOpcodeConfig(0x0F, [], [], 1, 1)


class DAQEquationOperation:
    _opcode: DAQEquationOpcode
    _params: list[Any]

    def __init__(self, opcode: DAQEquationOpcode, params: list[Any]) -> None:
        super().__init__()

        params = params.copy()

        expected_types = opcode.value.args
        if len(expected_types) != len(params):
            raise ConfigError(
                f"Invalid number of arguments for opcode {opcode.name} (expected {len(expected_types)}, got {len(params)})"
            )

        for i, (expected_type, arg) in enumerate(zip(expected_types, params)):
            if not isinstance(arg, expected_type):
                raise ConfigError(
                    f"Invalid type for argument {i} of opcode {opcode.name} (expected {expected_type}, got {type(arg)})"
                )

        self._opcode = opcode
        self._params = params

    def encode(self) -> bytes:
        expected_types = self._opcode.value.args
        expected_lengths = self._opcode.value.lengths

        payload = bytes([self._opcode.value.code])
        for expected_type, expected_length, arg in zip(expected_types, expected_lengths, self._params):
            if expected_type == int:
                payload += make_int(cast(int, arg), len=expected_length)
            elif expected_type == float:
                if expected_length == 4:
                    payload += make_float(cast(float, arg))
                elif expected_length == 8:
                    payload += make_double(cast(float, arg))
                else:
                    raise ValueError(f"Invalid length for float argument: {expected_length}")

        return payload

    def get_opcode(self) -> DAQEquationOpcode:
        return self._opcode

    @override
    def __repr__(self) -> str:
        return f"{self._opcode.name} {", ".join(map(str, self._params))}"


class DAQEquation:
    _ops: list[DAQEquationOperation]
    _has_end: bool = False
    _has_channel: bool = False
    _stack_depth: int = 0
    _max_stack_depth: int = 0
    _input_stack_depth: int

    def __init__(self, input_stack_depth: int = 0) -> None:
        super().__init__()
        self._ops = []
        self._input_stack_depth = input_stack_depth

    def append(self, eq: "DAQEquation") -> None:
        if self._has_end:
            raise ConfigError("Cannot append to equation after end opcode")

        if self._stack_depth < eq._input_stack_depth:
            raise ConfigError(
                f"Stack underflow for equation append (expected >= {eq._input_stack_depth} elements, got {self._stack_depth})"
            )

        self._ops += eq._ops
        self._has_channel = self._has_channel or eq._has_channel
        self._has_end = eq._has_end

        # Following equation has to deal with our whole stack depth for its entire duration
        eq_max_stack_depth = eq._max_stack_depth + self._stack_depth
        if eq_max_stack_depth > self._max_stack_depth:
            self._max_stack_depth = eq_max_stack_depth

        self._stack_depth += eq._stack_depth

    def get_max_stack_depth(self) -> int:
        return self._max_stack_depth

    def get_stack_depth(self) -> int:
        return self._stack_depth

    @override
    def __repr__(self) -> str:
        return f"# Begin program\n{'\n'.join(map(str, self._ops))}\n# End program"

    def _push_op(self, op: DAQEquationOperation) -> None:
        if self._has_end:
            raise ConfigError("Cannot add operation to equation after end opcode")

        opcode_enum = op.get_opcode()
        opcode = opcode_enum.value

        effective_stack_depth = self._stack_depth + self._input_stack_depth
        if effective_stack_depth < opcode.pops:
            raise ConfigError(
                f"Stack underflow for opcode {opcode_enum.name} (expected >= {opcode.pops} elements, got {effective_stack_depth})"
            )

        self._stack_depth -= opcode.pops
        self._stack_depth += opcode.pushes
        if self._stack_depth > self._max_stack_depth:
            self._max_stack_depth = self._stack_depth

        self._ops.append(op)

    def validate(self) -> None:
        if not self._has_end:
            raise ConfigError("Equation is missing end opcode")

        if not self._has_channel:
            raise ConfigError("Equation requires at least one channel reference")

        if self._input_stack_depth != 0:
            raise ConfigError("Valid equation input stack depth must be 0")

    def end(self) -> "DAQEquation":
        if self._stack_depth != 1:
            raise ConfigError(
                f"Invalid stack depth at end of equation (expected 1, got {self._stack_depth})"
            )
        self._push_op(DAQEquationOperation(DAQEquationOpcode.END, []))
        self._has_end = True
        return self

    def push_channel(self, channel: int) -> "DAQEquation":
        if isinstance(channel, float):
            channel = int(channel)
        self._push_op(DAQEquationOperation(DAQEquationOpcode.PUSH_CHANNEL, [channel]))
        self._has_channel = True
        return self

    def push_float(self, value: float) -> "DAQEquation":
        if isinstance(value, int):
            value = float(value)
        self._push_op(DAQEquationOperation(DAQEquationOpcode.PUSH_FLOAT, [value]))
        return self

    def push_double(self, value: float) -> "DAQEquation":
        if isinstance(value, int):
            value = float(value)
        self._push_op(DAQEquationOperation(DAQEquationOpcode.PUSH_DOUBLE, [value]))
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
        self.validate()
        payload = b""
        for op in self._ops:
            payload += op.encode()
        return payload
