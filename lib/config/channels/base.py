from dataclasses import dataclass
from ..enums import DAQConfigAlarm
from ...utils.encoding import make_int, make_float, make_optional_indexed_bit, NULL_INTEGER
from typing import override

@dataclass(frozen=True, kw_only=True)
class DAQChannel:
    use_channel_as_alarm_trigger: bool = True
    alarm1_mode: DAQConfigAlarm = DAQConfigAlarm.OFF
    alarm2_mode: DAQConfigAlarm = DAQConfigAlarm.OFF
    alarm1_level: float = 0.0
    alarm2_level: float = 0.0
    alarm1_digital: int | None = None
    alarm2_digital: int | None = None

    mxab_multuplier: float = 1.0
    mxab_offset: float = 0.0

    def alarm_bits(self) -> int:
        result = 0x01 if self.use_channel_as_alarm_trigger else 0x00
        result |= self.alarm1_mode.value << 1
        result |= self.alarm2_mode.value << 3
        return result
    
    def write_common_trailer(self) -> bytes:
        return make_int(self.alarm_bits()) + \
                make_float(self.alarm1_level) + \
                make_float(self.alarm2_level) + \
                make_optional_indexed_bit(self.alarm1_digital) + \
                make_optional_indexed_bit(self.alarm2_digital) + \
                make_float(self.mxab_multuplier) + \
                make_float(self.mxab_offset)

    def write_with_aux(self, aux_offset: int) -> tuple[bytes, bytes]:
        return self.write(), b''

    def write(self) -> bytes:
        raise NotImplementedError('write or write_with_equation method must be implemented in subclass')


@dataclass(frozen=True, kw_only=True)
class DAQDisabledChannel(DAQChannel):
    @override
    def write(self) -> bytes:
            return NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    NULL_INTEGER + \
                    self.write_common_trailer()

@dataclass(frozen=True, kw_only=True)
class DAQAnalogChannel(DAQChannel):
    pass

@dataclass(frozen=True, kw_only=True)
class DAQComputedChannel(DAQChannel):
    pass
