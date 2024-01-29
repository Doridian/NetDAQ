from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from struct import pack, unpack
from asyncio import sleep, open_connection, StreamReader, StreamWriter, get_event_loop, Future, Task, gather
from traceback import print_exc

class ResponseErrorCodeException(Exception):
    def __init__(self, code: int, payload: bytes) -> None:
        super().__init__(f'Response error: {code:08x}')
        self.code = code
        self.payload = payload

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

class DAQConfigAlarm(Enum):
    OFF  = 0x00
    HIGH = 0x01
    LOW  = 0x02

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
    totalizer_debounce: bool = True
    triggers: list[DAQConfigTrigger] = field(default_factory=lambda: [DAQConfigTrigger.INTERVAL])

    interval_time: float = 1.0
    alarm_time: float = 1.0
    phy_channels: list[DAQChannelConfiguration] = field(default_factory=lambda: [])
    computed_channels: list[DAQChannelConfiguration] = field(default_factory=lambda: [])

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

@dataclass(frozen=True)
class DAQReading:
    time: datetime
    dio: int # short
    unk1: int # short
    alarm1_bitmask: int
    alarm2_bitmask: int
    null1: int
    values: list[float]

    def get_dio_status(self, index: int) -> bool:
        return self.dio & (1 << index) != 0

    def is_channel_alarm1(self, index: int) -> bool:
        return self.alarm1_bitmask & (1 << index) != 0

    def is_channel_alarm2(self, index: int) -> bool:
        return self.alarm1_bitmask & (1 << index) != 0

@dataclass(frozen=True)
class DAQReadingResult:
    readings: list[DAQReading]
    instrument_queue: int

class NetDAQ:
    _FIXED_HEADER = bytearray([0x46, 0x45, 0x4C, 0x58])
    _HEADER_LEN = 16
    _INT_LEN = 4
    _CHANNEL_COUNT_PHY = 20
    _CHANNEL_COUNT_COMPUTED = 10
    _NULL_INTEGER = b'\x00' * _INT_LEN

    ip: str
    port: int
    _sock_writer: StreamWriter | None = None
    _reader_coroutine: Task | None = None
    _response_futures: dict[int, Future[bytes]]

    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.sequence_id = 0x02

        self._sock_writer = None
        self._response_futures = {}

    async def close(self, force: bool = False) -> None:
        sock_writer = self._sock_writer
        reader_coroutine = self._reader_coroutine
        self._sock_writer = None
        if not sock_writer:
            return

        if not force:
            try:
                clear_mon = self.send_rpc(NetDAQCommand.CLEAR_MONITOR_CHANNEL, writer=sock_writer)
                stop = self.send_rpc(NetDAQCommand.STOP, writer=sock_writer)
                close = self.send_rpc(NetDAQCommand.CLOSE, writer=sock_writer)
                await gather(clear_mon, stop, close)
            except:
                pass

        sock_writer.close()
        await sock_writer.wait_closed()
        if (not force) and reader_coroutine:
            await reader_coroutine

    async def _reader_coroutine_func(self, sock_reader: StreamReader) -> None:
        try:
            while True:
                response_header = await sock_reader.readexactly(len(self._FIXED_HEADER) + (self._INT_LEN * 3))
                if response_header[0:len(self._FIXED_HEADER)] != self._FIXED_HEADER:
                    raise Exception('Invalid response header')

                response_sequence_id = self._parse_int(response_header[4:])

                response_code = self._parse_int(response_header[8:])
                response_payload_length = self._parse_int(response_header[12:])

                if response_payload_length > self._HEADER_LEN:
                    payload = await sock_reader.readexactly(response_payload_length - self._HEADER_LEN)
                else:
                    payload = b''

                response_future = self._response_futures.pop(response_sequence_id, None)
                if (not response_future) or response_future.cancelled():
                    print('Got unsolicited response, ignoring...', response_sequence_id, response_code, payload)
                elif response_code != 0x00000000:
                    response_future.set_exception(ResponseErrorCodeException(code=response_code, payload=payload))
                else:
                    response_future.set_result(payload)
        except Exception:
            print_exc()
            await self.close(force=True)

    async def connect(self) -> None:
        await self.close()

        reader, writer = await open_connection(self.ip, self.port)
        self._sock_writer = writer
        self._reader_coroutine = get_event_loop().create_task(self._reader_coroutine_func(sock_reader=reader))

    def _parse_int(self, data: bytes) -> int:
        return int.from_bytes(data[:self._INT_LEN], 'big')

    def _parse_short(self, data: bytes) -> int:
        return int.from_bytes(data[:2], 'big')

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

    def _make_optional_indexed_bit(self, bit: int | None) -> bytes:
        if bit is None:
            return b'\x00\x00\x00\x00'
        return self._make_int(1 << bit)

    async def send_rpc(self, command: NetDAQCommand, payload: bytes = b'', writer: StreamWriter = None) -> bytes:
        if not writer:
            writer = self._sock_writer

        sequence_id = self.sequence_id
        self.sequence_id += 1

        packet = self._FIXED_HEADER + \
                    self._make_int(sequence_id) + \
                    self._make_int(command.value) + \
                    self._make_int(len(payload) + self._HEADER_LEN) + \
                    payload
        
        response_future: Future[bytes] = get_event_loop().create_future()
        self._response_futures[sequence_id] = response_future

        writer.write(packet)
        await writer.drain()

        return await response_future

    async def ping(self) -> None:
        await self.send_rpc(NetDAQCommand.PING)

    async def reset_totalizer(self) -> None:
        await self.send_rpc(NetDAQCommand.RESET_TOTALIZER)

    async def get_base_channel(self) -> int:
        return self._parse_int(await self.send_rpc(NetDAQCommand.GET_BASE_CHANNEL))

    async def get_version_info(self, command: NetDAQCommand = NetDAQCommand.GET_VERSION_INFO) -> list[str]:
        data = await self.send_rpc(command)
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

    async def get_lc_version(self) -> str:
        return await self.get_version_info(command=NetDAQCommand.GET_LC_VERSION)

    async def wait_for_idle(self) -> None:
        while True:
            status = self._parse_int(await self.send_rpc(NetDAQCommand.STATUS_QUERY))
            if status & 0x80000000 == 0x00000000:
                break
            await sleep(0.01)

    async def set_time(self, time: datetime | None = None) -> None:
        if not time:
            time = datetime.now()

        packet = self._make_time(time) + self._make_int(time.microsecond / 1000)

        await self.send_rpc(NetDAQCommand.SET_TIME, packet)
        await self.wait_for_idle()

    async def set_config(self, config: DAQConfiguration) -> None:
        payload = self._make_int(config.bits()) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    self._make_int(config.interval_time) + \
                    self._make_int(int(config.interval_time * 1000) % 1000) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    self._make_int(config.alarm_time) + \
                    self._make_int(int(config.alarm_time * 1000) % 1000) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    b'\x00\x00\x00\x64'

        phy_channels = config.phy_channels
        if len(phy_channels) < self._CHANNEL_COUNT_PHY:
            phy_channels += [DAQChannelConfiguration() for _ in range(self._CHANNEL_COUNT_PHY - len(phy_channels))]

        for chan in phy_channels:
            payload += self._make_int(chan.mtype.value) + \
                        self._make_int(chan.range.value) + \
                        self._make_float(chan.aux2) + \
                        self._make_float(chan.aux1) + \
                        self._make_int(chan.extra_bits()) + \
                        self._make_int(chan.alarm_bits()) + \
                        self._make_float(chan.alarm1_level) + \
                        self._make_float(chan.alarm2_level) + \
                        self._make_optional_indexed_bit(chan.alarm1_digital) + \
                        self._make_optional_indexed_bit(chan.alarm2_digital) + \
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
                        self._make_int(chan.alarm_bits()) + \
                        self._make_float(chan.alarm1_level) + \
                        self._make_float(chan.alarm2_level) + \
                        self._make_optional_indexed_bit(chan.alarm1_digital) + \
                        self._make_optional_indexed_bit(chan.alarm2_digital) + \
                        self._make_float(chan.mxab_multuplier) + \
                        self._make_float(chan.mxab_offset)

        payload = payload + (b'\x00' * (2492 - len(payload)))
        await self.send_rpc(NetDAQCommand.SET_CONFIG, payload)
        await self.wait_for_idle()

    async def set_monitor_channel(self, channel: int) -> None:
        if channel <= 0:
            await self.send_rpc(NetDAQCommand.CLEAR_MONITOR_CHANNEL)
        else:
            await self.send_rpc(NetDAQCommand.SET_MONITOR_CHANNEL, self._make_int(channel))

    async def get_readings(self, max_readings: int = 0xFF) -> DAQReadingResult:
        data = await self.send_rpc(NetDAQCommand.GET_READINGS, self._make_int(max_readings))
        result: list[DAQReading] = []

        chunk_length = self._parse_int(data[0:])
        chunk_count = self._parse_int(data[4:])
        instrument_queue = self._parse_int(data[8:])

        chunks_buf = data[12:]
        for i in range(chunk_count):
            chunk_data = chunks_buf[i * chunk_length:(i + 1) * chunk_length]
            if self._parse_int(chunk_data[0:]) != 0x10:
                raise Exception('Invalid chunk header')

            result.append(DAQReading(
                time=self._parse_time(chunk_data[4:]),
                dio=self._parse_short(chunk_data[12:]),
                unk1=self._parse_short(chunk_data[14:]),
                alarm1_bitmask=self._parse_int(chunk_data[16:]),
                alarm2_bitmask=self._parse_int(chunk_data[20:]),
                null1=self._parse_int(chunk_data[24:]),
                values=[self._parse_float(chunk_data[i:]) for i in range(28, len(chunk_data), 4)],
            ))

        return DAQReadingResult(readings=result, instrument_queue=instrument_queue)

    async def stop(self) -> None:
        try:
            await self.send_rpc(NetDAQCommand.STOP)
        except ResponseErrorCodeException:
            pass

    async def start(self) -> None:
        await self.send_rpc(NetDAQCommand.START, b'\x00' * 16)

    async def handshake(self) -> None:
        await self.ping()
