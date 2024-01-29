from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from struct import pack, unpack
from time import sleep

class ResponseErrorCodeException(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f'Response error: {code:08x}')
        self.code = code

class NetDAQCommand(Enum):
    PING                  = 0x00000000
    CLOSE                 = 0x00000001
    STATUS_QUERY          = 0x00000002
    GET_READINGS          = 0x00000064
    START                 = 0x00000067
    STOP                  = 0x00000068
    SET_TIME              = 0x0000006A
    RESET_TOTALIZER       = 0x00000071
    GET_VERSION_INFO      = 0x00000072
    SET_MONITOR_CHANNEL   = 0x00000075
    CLEAR_MONITOR_CHANNEL = 0x00000076
    GET_BASE_CHANNEL      = 0x00000077
    GET_LC_VERSION        = 0x0000007F
    SET_CONFIG            = 0x00000081

class DAQConfigBits(Enum):
    MEDIUM_SPEED       = 0x0001
    FAST_SPEED         = 0x0002
    FAHRENHEIT         = 0x0004
    TRIGGER_OUT        = 0x0008
    DRIFT_CORRECTION   = 0x0010
    TOTALIZER_DEBOUNCE = 0x0020
    INTERVAL_TRIGGER   = 0x0040
    ALARM_TRIGGER      = 0x0080
    EXTERNAL_TRIGGER   = 0x0100

class DAQConfigSpeed(Enum):
    SLOW   = 0x0000
    MEDIUM = 0x0001
    FAST   = 0x0002

class DAQConfigTrigger(Enum):
    INTERVAL = 0x0040
    ALARM    = 0x0080
    EXTERNAL = 0x0100

class DAQMeasuremenType(Enum):
    OFF          = 0x00000000
    Ohms         = 0x00000001
    Ohms_4Wire   = 0x00000001
    VDC          = 0x00000002
    VAC          = 0x00000004
    Frequency    = 0x00000008
    RTD          = 0x00000010
    Thermocouple = 0x00000020
    Current      = 0x00010002

class DAQRange(Enum):
    NONE = 0x0000

    VDC_90mV   = 0x2001
    VDC_300mV  = 0x2102
    VDC_3V     = 0x2308
    VDC_30V    = 0x2410
    VDC_AUTO   = 0x2520
    VDC_50V    = 0x2640

    VAC_300mV  = 0x3001
    VAC_3V     = 0x3102
    VAC_30V    = 0x3204
    VAC_AUTO   = 0x3308

    Ohms_300   = 0x1001
    Ohms_3k    = 0x1102
    Ohms_30k   = 0x1204
    Ohms_300k  = 0x1308
    Ohms_3M    = 0x1410
    Ohms_AUTO  = 0x1520

    TC_J = 0x6001
    TC_K = 0x6101
    TC_E = 0x6201
    TC_T = 0x6301
    TC_R = 0x6401
    TC_S = 0x6501
    TC_B = 0x6601
    TC_C = 0x6701
    TC_N = 0x6801

    RTD_FIXED_385  = 0x5020
    RTD_CUSTOM_385 = 0x5021

    Frequency_AUTO = 0x0000

    Current_20mA  = 0x2102
    Current_100mA = 0x2520

@dataclass(frozen=True)
class DAQChannelConfiguration:
    mtype: DAQMeasuremenType = DAQMeasuremenType.OFF
    range: DAQRange = DAQRange.NONE

    aux2: float = 0.0 # RTD ALpha
    aux1: float = 0.0 # RTD R0 / Shunt resistance
    open_thermocouple_detect: bool = True

    alarm_bits: int = 0
    alarm1_level: float = 0.0
    alarm2_level: float = 0.0
    alarm1_digital: int = 0
    alarm2_digital: int = 0

    mxab_multuplier: float = 1.0
    mxab_offset: float = 0.0

    def extra_bits(self) -> int:
        if self.mtype == DAQMeasuremenType.Ohms:
            return 0x9000
        if self.mtype == DAQMeasuremenType.Ohms_4Wire or self.mtype == DAQMeasuremenType.RTD:
            return 0x9001

        if self.mtype == DAQMeasuremenType.Thermocouple:
            return 0x0001 if self.open_thermocouple_detect else 0x0000

        if self.mtype == DAQMeasuremenType.Current:
            if self.range == DAQRange.Current_20mA:
                return 0x7000
            return 0x7001

        return 0x0000

@dataclass(frozen=True)
class DAQConfiguration:
    speed: DAQConfigSpeed = DAQConfigSpeed.SLOW
    temperature_fahrenheit: bool = False
    trigger_out: bool = False
    drift_correction: bool = True
    totalizer_debounce: bool
    triggers: list[DAQConfigTrigger] = []

    interval_time: float = 1.0
    alarm_time: float = 1.0
    phy_channels: list[DAQChannelConfiguration] = []
    computed_channels: list[DAQChannelConfiguration] = []

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

@dataclass(frozen=True)
class DAQReading:
    time: datetime
    null1: int
    null2: int
    null3: int
    values: list[float]

class NetDAQ:
    _FIXED_HEADER = bytearray([0x46, 0x45, 0x4C, 0x58])
    _HEADER_LEN = 16
    _INT_LEN = 4
    _CHANNEL_COUNT_PHY = 20
    _CHANNEL_COUNT_COMPUTED = 10

    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.sequence_id = 0x02
        self.sock = None

    def close(self) -> None:
        if not self.sock:
            return

        try:
            self.stop()
        except:
            pass

        try:
            self.send_rpc(NetDAQCommand.CLOSE)
        except:
            pass

        self.sock.close()

    def connect(self) -> None:
        self.close()

        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        self.sock.settimeout(1)

    def _parse_int(self, data: bytes) -> int:
        return int.from_bytes(data[:self._INT_LEN], 'big')

    def _make_int(self, value: int) -> None:
        return int.to_bytes(int(value), self._INT_LEN, 'big')

    def _parse_float(self, data: bytes) -> float:
        return unpack('>f', data[:4])

    def _make_float(self, value: float) -> None:
        return pack('>f', value)

    def _parse_time(self, data: bytes) -> datetime:
        return datetime(
            hour=data[0],
            minute=data[1],
            second=data[2],
            month=data[3],
            day=data[5],
            year=2000 + data[6], # Well this is gonna break in 2100 lol
            microsecond=(self._parse_int(data[8:]) & 0xFFFF) * 1000,
        )

    def _make_time(self, time: datetime) -> bytes:
        return bytes([
            time.hour,
            time.minute,
            time.second,
            time.month,
            0x08, # unknown value
            time.day,
            time.year % 100,
            0x00, # unknown value
        ])

    def send_rpc(self, command: NetDAQCommand, payload: bytes = b'') -> bytes:
        sequence_id = self.sequence_id
        self.sequence_id += 1

        packet = self._FIXED_HEADER + \
                    self._make_int(sequence_id) + \
                    self._make_int(command.value) + \
                    self._make_int(len(payload) + self._HEADER_LEN) + \
                    payload

        self.sock.sendall(packet)


        response_header = self.sock.recv(len(self._FIXED_HEADER) + (self._INT_LEN * 3))
        if response_header[0:len(self._FIXED_HEADER)] != self._FIXED_HEADER:
            raise Exception('Invalid response header')
        
        response_sequence_id = self._parse_int(response_header[4:])
        if response_sequence_id != sequence_id:
            raise Exception('Invalid response sequence id')
        
        response_payload_length = self._parse_int(response_header[12:])

        if response_payload_length > self._HEADER_LEN:
            payload = self.sock.recv(response_payload_length - self._HEADER_LEN)
        else:
            payload = b''

        response_command = self._parse_int(response_header[8:])
        if response_command != 0x00000000:
            raise ResponseErrorCodeException(response_command)
        
        return payload

    def ping(self) -> None:
        self.send_rpc(NetDAQCommand.PING)

    def reset_totalizer(self) -> None:
        self.send_rpc(NetDAQCommand.RESET_TOTALIZER)

    def get_base_channel(self) -> int:
        return self._parse_int(self.send_rpc(NetDAQCommand.GET_BASE_CHANNEL))

    def get_version_info(self, command: NetDAQCommand = NetDAQCommand.GET_VERSION_INFO) -> list[str]:
        data = self.send_rpc(command)
        blobs = []
        current = []
        for i in data:
            if i == 0x00:
                blobs.append(bytes(current))
                current = []
                continue
            current.append(i)
        if current:
            blobs.append(bytes(current))
        return blobs

    def get_lc_version(self) -> str:
        return self.get_version_info(command=NetDAQCommand.GET_LC_VERSION)

    def wait_for_idle(self) -> None:
        while True:
            status = self._parse_int(self.send_rpc(NetDAQCommand.STATUS_QUERY))
            if status & 0x80000000 == 0x00000000:
                break
            sleep(0.01)

    def set_time(self, time: datetime | None = None) -> None:
        if not time:
            time = datetime.now()

        packet = self._make_time(time) + self._make_int(time.microsecond / 1000)

        self.send_rpc(NetDAQCommand.SET_TIME, packet)
        self.wait_for_idle()

    def set_config(self, config: DAQConfiguration) -> None:
        payload = self._make_int(config.bits()) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    self._make_int(config.interval_time) + \
                    self._make_int(int(config.interval_time * 1000) % 1000) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    self._make_int(config.alarm_time) + \
                    self._make_int(int(config.alarm_time * 1000) % 1000) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    bytes([0x00, 0x00, 0x00, 0x00]) + \
                    bytes([0x00, 0x00, 0x00, 0x64])

        phy_channels = config.phy_channels
        if len(phy_channels) < self._CHANNEL_COUNT_PHY:
            phy_channels += [DAQChannelConfiguration() for _ in range(self._CHANNEL_COUNT_PHY - len(phy_channels))]

        for chan in phy_channels:
            payload += self._make_int(chan.mtype.value) + \
                        self._make_int(chan.range.value) + \
                        self._make_float(chan.aux2) + \
                        self._make_float(chan.aux1) + \
                        self._make_int(chan.extra_bits()) + \
                        self._make_int(chan.alarm_bits) + \
                        self._make_float(chan.alarm1_level) + \
                        self._make_float(chan.alarm2_level) + \
                        self._make_int(chan.alarm1_digital) + \
                        self._make_int(chan.alarm2_digital) + \
                        self._make_float(chan.mxab_multuplier) + \
                        self._make_float(chan.mxab_offset)

        computed_channels = config.computed_channels
        if len(computed_channels) < self._CHANNEL_COUNT_COMPUTED:
            computed_channels += [DAQChannelConfiguration() for _ in range(self._CHANNEL_COUNT_COMPUTED - len(computed_channels))]

        for chan in computed_channels:
            payload += self._make_int(chan.mtype.value) + \
                        self._make_int(chan.range.value) + \
                        self._make_float(chan.aux2) + \
                        self._make_float(chan.aux1) + \
                        self._make_int(chan.extra_bits()) + \
                        self._make_int(chan.alarm_bits) + \
                        self._make_float(chan.alarm1_level) + \
                        self._make_float(chan.alarm2_level) + \
                        self._make_int(chan.alarm1_digital) + \
                        self._make_int(chan.alarm2_digital) + \
                        self._make_float(chan.mxab_multuplier) + \
                        self._make_float(chan.mxab_offset)

        payload = payload + bytes([0x00] * (2492 - len(payload)))
        self.send_rpc(NetDAQCommand.SET_CONFIG, payload)
        self.wait_for_idle()

    def set_monitor_channel(self, channel: int) -> None:
        if channel <= 0:
            self.send_rpc(NetDAQCommand.CLEAR_MONITOR_CHANNEL)
        else:
            self.send_rpc(NetDAQCommand.SET_MONITOR_CHANNEL, self._make_int(channel))

    def get_readings(self) -> list[DAQReading]:
        data = self.send_rpc(NetDAQCommand.GET_READINGS, b'\x00\x00\x00\xFF')
        result: list[DAQReading] = []

        chunk_length = self._parse_int(data[0:])
        chunk_count = self._parse_int(data[4:])
        # 8:12 = unknown/null

        chunks_buf = data[12:]
        for i in range(chunk_count):
            chunk_data = chunks_buf[i * chunk_length:(i + 1) * chunk_length]
            if self._parse_int(chunk_data[0:]) != 0x10:
                raise Exception('Invalid chunk header')

            result.append(DAQReading(
                time=self._parse_time(chunk_data[4:]),
                null1=self._parse_int(chunk_data[16:]),
                null2=self._parse_int(chunk_data[20:]),
                null3=self._parse_int(chunk_data[24:]),
                values=[self._parse_float(chunk_data[i:]) for i in range(28, len(chunk_data), 4)],
            ))

        return result

    def stop(self) -> None:
        try:
            self.send_rpc(NetDAQCommand.STOP)
        except ResponseErrorCodeException:
            pass

    def start(self) -> None:
        self.send_rpc(NetDAQCommand.START, b'\x00' * 16)

    def handshake(self) -> None:
        self.ping()
