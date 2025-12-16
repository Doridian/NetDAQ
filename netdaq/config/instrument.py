from dataclasses import dataclass, field
from datetime import timedelta
from .enums import DAQConfigSpeed, DAQConfigTrigger, DAQConfigBits
from .channels.base import DAQComputedChannel, DAQAnalogChannel


@dataclass(frozen=True, kw_only=True)
class DAQConfiguration:
    speed: DAQConfigSpeed = DAQConfigSpeed.SLOW
    temperature_fahrenheit: bool = False
    trigger_out: bool = False
    drift_correction: bool = True
    totalizer_debounce: bool = True
    triggers: list[DAQConfigTrigger] = field(
        default_factory=lambda: [DAQConfigTrigger.INTERVAL]
    )

    interval_time: timedelta = timedelta(seconds=1)
    alarm_time: timedelta = timedelta(seconds=1)
    unknown3_time: timedelta = timedelta(milliseconds=100)

    analog_channels: list[DAQAnalogChannel | None] = field(default_factory=lambda: [])
    computed_channels: list[DAQComputedChannel | None] = field(default_factory=lambda: [])

    def bits(self) -> int:
        result = self.speed.value
        if self.drift_correction or self.speed != DAQConfigSpeed.FAST:
            result |= DAQConfigBits.DRIFT_CORRECTION.value
        if self.trigger_out:
            result |= DAQConfigBits.TRIGGER_OUT.value
        if self.temperature_fahrenheit:
            result |= DAQConfigBits.FAHRENHEIT.value
        if self.totalizer_debounce:
            result |= DAQConfigBits.TOTALIZER_DEBOUNCE.value
        for trig in self.triggers:
            result |= trig.value
        return result
