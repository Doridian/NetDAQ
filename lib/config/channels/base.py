from dataclasses import dataclass
from ..enums import DAQConfigAlarm
from ...utils.encoding import make_int, make_float, make_optional_indexed_bit, NULL_INT
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

    def _modified_mxab_multiplier(self) -> float:
        return self.mxab_multuplier

    def _modified_mxab_offset(self) -> float:
        return self.mxab_offset

    def encode_common_trailer(self) -> bytes:
        alarm_bits = 0x00
        if self.use_channel_as_alarm_trigger:
            alarm_bits |= 0x01
        alarm_bits |= self.alarm1_mode.value << 1
        alarm_bits |= self.alarm2_mode.value << 3

        return (
            make_int(alarm_bits)
            + make_float(self.alarm1_level)
            + make_float(self.alarm2_level)
            + make_optional_indexed_bit(self.alarm1_digital)
            + make_optional_indexed_bit(self.alarm2_digital)
            + make_float(self._modified_mxab_multiplier())
            + make_float(self._modified_mxab_offset())
        )

    def encode_with_aux(self, aux_offset: int) -> tuple[bytes, bytes]:
        return self.encode(), b""

    def encode(self) -> bytes:
        raise NotImplementedError(
            "write or write_with_aux method must be implemented in subclass"
        )


@dataclass(frozen=True, kw_only=True)
class DAQDisabledChannel(DAQChannel):
    @override
    def encode(self) -> bytes:
        return (
            NULL_INT
            + NULL_INT
            + NULL_INT
            + NULL_INT
            + NULL_INT
            + self.encode_common_trailer()
        )


@dataclass(frozen=True, kw_only=True)
class DAQAnalogChannel(DAQChannel):
    pass


@dataclass(frozen=True, kw_only=True)
class DAQComputedChannel(DAQChannel):
    pass
