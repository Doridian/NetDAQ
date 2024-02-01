from dataclasses import dataclass
from ..enums import DAQAnalogMeasuremenType, DAQOhmsRange, DAQVDCRange, DAQVACRange, DAQCurrentRange, DAQThermocoupleRange, DAQRTDRange
from ...utils.encoding import make_int, make_float, NULL_INTEGER
from .base import DAQAnalogChannel
from typing import override

@dataclass(frozen=True, kw_only=True)
class DAQAnalogOhmsChannel(DAQAnalogChannel):
    four_wire: bool = False
    range: DAQOhmsRange

    @override
    def write(self) -> bytes:
        extra_bits = 0x9000
        if self.four_wire:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Ohms.value) + \
                    make_int(self.range.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    make_int(extra_bits) + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogVDCChannel(DAQAnalogChannel):
    range: DAQVDCRange

    @override
    def write(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.VDC.value) + \
                    make_int(self.range.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    self.write_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogVACChannel(DAQAnalogChannel):
    range: DAQVACRange

    @override
    def write(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.VAC.value) + \
                    make_int(self.range.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogFrequencyChannel(DAQAnalogChannel):
    @override
    def write(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.Frequency.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogRTDChannel(DAQAnalogChannel):
    range: DAQRTDRange
    alpha: float = 0.0
    r0: float = 0.0

    @override
    def write(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.RTD.value) + \
                    make_int(self.range.value) + \
                    make_float(self.alpha) + \
                    make_float(self.r0) + \
                    make_int(0x9001) + \
                    self.write_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogThermocoupleChannel(DAQAnalogChannel):
    range: DAQThermocoupleRange
    open_thermocouple_detect: bool = True

    @override
    def write(self) -> bytes:
        extra_bits = 0x0000
        if self.open_thermocouple_detect:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Thermocouple.value) + \
                    make_int(self.range.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    make_int(extra_bits) + \
                    self.write_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogCurrentChannel(DAQAnalogChannel):
    range: DAQCurrentRange

    @override
    def write(self) -> bytes:
        extra_bits = 0x7000
        if self.range == DAQCurrentRange.Current_100mA:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Current.value) + \
                    make_int(self.range.value) + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    make_int(extra_bits) + \
                    self.write_common_trailer()
