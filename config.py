from dataclasses import dataclass, field
from enums import DAQConfigAlarm, DAQAnalogMeasuremenType, DAQComputedMeasurementType, DAQRange, DAQConfigSpeed, DAQConfigTrigger, DAQConfigBits

@dataclass(frozen=True, kw_only=True)
class DAQChannelConfiguration:
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

@dataclass(frozen=True, kw_only=True)
class DAQAnalogChannelConfiguration(DAQChannelConfiguration):
    mtype: DAQAnalogMeasuremenType = DAQAnalogMeasuremenType.OFF
    aux1: float = 0.0 # RTD ALpha
    aux2: float = 0.0 # RTD R0 / Shunt resistance
    open_thermocouple_detect: bool = True
    range: DAQRange = DAQRange.NONE

    def extra_bits(self) -> int:
        if self.mtype == DAQAnalogMeasuremenType.Ohms:
            return 0x9000
        if self.mtype == DAQAnalogMeasuremenType.Ohms_4Wire or self.mtype == DAQAnalogMeasuremenType.RTD:
            return 0x9001

        if self.mtype == DAQAnalogMeasuremenType.Thermocouple:
            return 0x0001 if self.open_thermocouple_detect else 0x0000

        if self.mtype == DAQAnalogMeasuremenType.Current:
            if self.range == DAQRange.Current_20mA:
                return 0x7000
            return 0x7001

        return 0x0000

@dataclass(frozen=True, kw_only=True)
class DAQComputedChannelConfiguration(DAQChannelConfiguration):
    mtype: DAQComputedMeasurementType = DAQComputedMeasurementType.OFF
    channel_a: int = 0
    aux1: int = 0 # Channel bitmask / Channel B / Equation offset
    equation: bytes = b''

@dataclass(frozen=True, kw_only=True)
class DAQConfiguration:
    speed: DAQConfigSpeed = DAQConfigSpeed.SLOW
    temperature_fahrenheit: bool = False
    trigger_out: bool = False
    drift_correction: bool = True
    totalizer_debounce: bool = True
    triggers: list[DAQConfigTrigger] = field(default_factory=lambda: [DAQConfigTrigger.INTERVAL])

    interval_time: float = 1.0
    alarm_time: float = 1.0
    analog_channels: list[DAQAnalogChannelConfiguration] = field(default_factory=lambda: [])
    computed_channels: list[DAQComputedChannelConfiguration] = field(default_factory=lambda: [])

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
