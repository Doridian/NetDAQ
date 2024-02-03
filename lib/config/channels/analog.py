from dataclasses import dataclass
from ..enums import DAQAnalogMeasuremenType, DAQOhmsRange, DAQVDCRange, DAQVACRange, DAQCurrentRange, DAQThermocoupleRange, DAQRTDRange
from ...utils.encoding import make_int, make_float, NULL_INT
from .base import DAQAnalogChannel
from typing import override

@dataclass(frozen=True, kw_only=True)
class DAQAnalogOhmsChannel(DAQAnalogChannel):
    range: DAQOhmsRange
    four_wire: bool = False

    def __post_init__(self) -> None:
        if (not self.four_wire) and (self.range == DAQOhmsRange.Ohms_300 or self.range == DAQOhmsRange.Ohms_3k):
            raise ValueError("2-wire ohms measurement is not supported for 300 or 3k Ohms range")

    @override
    def encode(self) -> bytes:
        extra_bits = 0x9000
        if self.four_wire:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Ohms.value) + \
                    make_int(self.range.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    make_int(extra_bits) + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogVDCChannel(DAQAnalogChannel):
    range: DAQVDCRange

    @override
    def encode(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.VDC.value) + \
                    make_int(self.range.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    self.encode_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogVACChannel(DAQAnalogChannel):
    range: DAQVACRange

    @override
    def encode(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.VAC.value) + \
                    make_int(self.range.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogFrequencyChannel(DAQAnalogChannel):
    @override
    def encode(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.Frequency.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    NULL_INT + \
                    self.encode_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogRTDChannel(DAQAnalogChannel):
    range: DAQRTDRange
    alpha: float = 0.0
    r0: float

    def __post_init__(self) -> None:
        if self.r0 < 10 or self.r0 > 1010:
            raise ValueError("Custom RTD R0 value must be between 10 and 1010 Ohms")

        if self.range == DAQRTDRange.RTD_FIXED_385:
            if self.alpha != 0.0:
                raise ValueError("Fixed RTD does not allow for Alpha value to be set")
        elif self.range == DAQRTDRange.RTD_CUSTOM_385:
            if self.alpha < 0.00374 or self.alpha > 0.00393:
                raise ValueError("Custom RTD Alpha value must be between 0.00374 and 0.00393")

    @override
    def encode(self) -> bytes:
        return make_int(DAQAnalogMeasuremenType.RTD.value) + \
                    make_int(self.range.value) + \
                    make_float(self.alpha) + \
                    make_float(self.r0) + \
                    make_int(0x9001) + \
                    self.encode_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogThermocoupleChannel(DAQAnalogChannel):
    range: DAQThermocoupleRange
    open_thermocouple_detect: bool = True

    @override
    def encode(self) -> bytes:
        extra_bits = 0x0000
        if self.open_thermocouple_detect:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Thermocouple.value) + \
                    make_int(self.range.value) + \
                    NULL_INT + \
                    NULL_INT + \
                    make_int(extra_bits) + \
                    self.encode_common_trailer()
    
@dataclass(frozen=True, kw_only=True)
class DAQAnalogCurrentChannel(DAQAnalogChannel):
    range: DAQCurrentRange
    shunt_resistance: float

    def __post_init__(self) -> None:
        if self.shunt_resistance < 10 or self.shunt_resistance > 250:
            raise ValueError("Shunt resistance must be between 10 and 250 Ohms")

    @override
    def encode(self) -> bytes:
        extra_bits = 0x7000
        if self.range == DAQCurrentRange.Current_100mA:
            extra_bits |= 0x0001

        return make_int(DAQAnalogMeasuremenType.Current.value) + \
                    make_int(self.range.value) + \
                    make_float(self.shunt_resistance) + \
                    NULL_INT + \
                    make_int(extra_bits) + \
                    self.encode_common_trailer()
