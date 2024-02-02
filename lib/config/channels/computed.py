from .base import DAQComputedChannel
from ..enums import DAQComputedMeasurementType
from ...utils.encoding import make_int, NULL_INT
from ..equation import DAQEquation
from dataclasses import dataclass
from typing import override

@dataclass(frozen=True, kw_only=True)
class DAQComputedAverageChannel(DAQComputedChannel):
    channel_bitmask: int

    @override
    def encode(self) -> bytes:
        return make_int(DAQComputedMeasurementType.Average.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    make_int(self.channel_bitmask) + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedAminusBChannel(DAQComputedChannel):
    channel_a: int
    channel_b: int

    @override
    def encode(self) -> bytes:
        return make_int(DAQComputedMeasurementType.AminusB.value) + \
                    NULL_INT + \
                    make_int(self.channel_a) + \
                    NULL_INT + \
                    make_int(self.channel_b) + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedAminusAvgChannel(DAQComputedChannel):
    channel_a: int
    channel_bitmask: int

    @override
    def encode(self) -> bytes:
        return make_int(DAQComputedMeasurementType.AminusB.value) + \
                    NULL_INT + \
                    make_int(self.channel_a) + \
                    NULL_INT + \
                    make_int(self.channel_bitmask) + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedEquationChannel(DAQComputedChannel):
    equation: DAQEquation

    @override
    def encode_with_aux(self, aux_offset: int) -> tuple[bytes, bytes]:
        payload = make_int(DAQComputedMeasurementType.Equation.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    make_int(aux_offset) + \
                    self.encode_common_trailer()

        return payload, self.equation.encode()
