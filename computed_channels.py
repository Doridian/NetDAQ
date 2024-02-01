from config import DAQComputedChannel
from enums import DAQComputedMeasurementType
from encoding import make_int, NULL_INTEGER
from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class DAQComputedAverageChannel(DAQComputedChannel):
    channel_bitmask: int

    def write(self) -> bytes:
        return make_int(DAQComputedMeasurementType.Average.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    make_int(self.channel_bitmask) + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedAminusBChannel(DAQComputedChannel):
    channel_a: int
    channel_b: int

    def write(self) -> bytes:
        return make_int(DAQComputedMeasurementType.AminusB.value) + \
                    NULL_INTEGER + \
                    make_int(self.channel_a) + \
                    NULL_INTEGER + \
                    make_int(self.channel_b) + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedAminusAvgChannel(DAQComputedChannel):
    channel_a: int
    channel_bitmask: int

    def write(self) -> bytes:
        return make_int(DAQComputedMeasurementType.AminusB.value) + \
                    NULL_INTEGER + \
                    make_int(self.channel_a) + \
                    NULL_INTEGER + \
                    make_int(self.channel_bitmask) + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQComputedEquationChannel(DAQComputedChannel):
    equation: bytes = b''

    def write_with_aux(self, aux_offset: int) -> tuple[bytes, bytes]:
        payload = make_int(DAQComputedMeasurementType.Equation.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    make_int(aux_offset) + \
                    self.write_common_trailer()

        return payload, self.equation
