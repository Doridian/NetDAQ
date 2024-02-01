from datetime import datetime
from dataclasses import dataclass
from asyncio import sleep, open_connection, StreamReader, StreamWriter, get_event_loop, Future, Task, CancelledError
from traceback import print_exc
from enums import DAQCommand
from config import DAQAnalogChannel, DAQComputedChannel, DAQConfiguration
from encoding import make_int, parse_float, parse_int, parse_short, make_time, parse_time, INT_LEN

class ResponseErrorCodeException(Exception):
    def __init__(self, code: int, payload: bytes) -> None:
        super().__init__(f'Response error: {code:08x}')
        self.code = code
        self.payload = payload

@dataclass(frozen=True, kw_only=True)
class DAQReading:
    time: datetime
    dio: int # short
    alarm1_bitmask: int
    alarm2_bitmask: int
    totalizer: int
    values: list[float]

    def get_dio_status(self, index: int) -> bool:
        return self.dio & (1 << index) != 0

    def is_channel_alarm1(self, index: int) -> bool:
        return self.alarm1_bitmask & (1 << index) != 0

    def is_channel_alarm2(self, index: int) -> bool:
        return self.alarm1_bitmask & (1 << index) != 0

@dataclass(frozen=True, kw_only=True)
class DAQReadingResult:
    readings: list[DAQReading]
    instrument_queue: int

CHANNEL_PAYLOAD_LENGTH = 2492

class NetDAQ:
    _FIXED_HEADER = bytes([0x46, 0x45, 0x4C, 0x58])
    _HEADER_LEN = 16
    _CHANNEL_COUNT_ANALOG = 20
    _CHANNEL_COUNT_COMPUTED = 10
    _NULL_INTEGER = b'\x00' * INT_LEN

    ip: str
    port: int
    _sock_writer: StreamWriter | None = None
    _reader_coroutine: Task[None] | None = None
    _response_futures: dict[int, Future[bytes]]

    def __init__(self, ip: str, port: int) -> None:
        super().__init__()
        self.ip = ip
        self.port = port
        self.sequence_id = 0x02

        self._sock_writer = None
        self._response_futures = {}

    async def close(self) -> None:
        reader_coroutine = self._reader_coroutine
        self._reader_coroutine = None
        if reader_coroutine:
            _ = reader_coroutine.cancel()
            await reader_coroutine

        sock_writer = self._sock_writer
        self._sock_writer = None
        if not sock_writer:
            return

        try:
            _ = await self.send_rpc(DAQCommand.CLEAR_MONITOR_CHANNEL, writer=sock_writer, wait_response=False)
            _ = await self.send_rpc(DAQCommand.STOP, writer=sock_writer, wait_response=False)
            _ = await self.send_rpc(DAQCommand.DISABLE_SPY, writer=sock_writer, wait_response=False)
            _ = await self.send_rpc(DAQCommand.CLOSE, writer=sock_writer, wait_response=False)
        except:
            pass

        sock_writer.close()
        await sock_writer.wait_closed()

    async def _reader_coroutine_func(self, sock_reader: StreamReader) -> None:
        try:
            while True:
                response_header = await sock_reader.readexactly(len(self._FIXED_HEADER) + (INT_LEN * 3))
                if response_header[0:len(self._FIXED_HEADER)] != self._FIXED_HEADER:
                    raise Exception('Invalid response header')

                response_sequence_id = parse_int(response_header[4:])

                response_code = parse_int(response_header[8:])
                response_payload_length = parse_int(response_header[12:])

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
        except CancelledError:
            return
        except Exception:
            print_exc()
            self._reader_coroutine = None
            await self.close()

    async def connect(self) -> None:
        await self.close()

        reader, writer = await open_connection(self.ip, self.port)
        self._sock_writer = writer
        self._reader_coroutine = get_event_loop().create_task(self._reader_coroutine_func(sock_reader=reader))

    async def send_rpc(self, command: DAQCommand, payload: bytes = b'', writer: StreamWriter | None = None, wait_response: bool = True) -> bytes:
        if not writer:
            writer = self._sock_writer
        if not writer:
            raise Exception('Not connected')

        sequence_id = self.sequence_id
        self.sequence_id += 1

        packet = self._FIXED_HEADER + \
                    make_int(sequence_id) + \
                    make_int(command.value) + \
                    make_int(len(payload) + self._HEADER_LEN) + \
                    payload

        response_future: Future[bytes] = get_event_loop().create_future()
        if wait_response:
            self._response_futures[sequence_id] = response_future

        writer.write(packet)
        await writer.drain()

        if not wait_response:
            return b''
        return await response_future

    async def ping(self) -> None:
        _ = await self.send_rpc(DAQCommand.PING)

    async def reset_totalizer(self) -> None:
        _ = await self.send_rpc(DAQCommand.RESET_TOTALIZER)

    async def get_base_channel(self) -> int:
        return parse_int(await self.send_rpc(DAQCommand.GET_BASE_CHANNEL))

    async def get_version_info(self, command: DAQCommand = DAQCommand.GET_VERSION_INFO) -> list[bytes]:
        data = await self.send_rpc(command)
        blobs: list[bytes] = []
        current: list[int] = []
        for i in data:
            if i == 0x00:
                blobs.append(bytes(current))
                current = []
                continue
            current.append(i)
        if current:
            blobs.append(bytes(current))
        return blobs

    async def get_lc_version(self) -> list[bytes]:
        return await self.get_version_info(command=DAQCommand.GET_LC_VERSION)

    async def wait_for_idle(self) -> None:
        while True:
            status = parse_int(await self.send_rpc(DAQCommand.STATUS_QUERY))
            if status & 0x80000000 == 0x00000000:
                break
            await sleep(0.01)

    async def set_time(self, time: datetime | None = None) -> None:
        if not time:
            time = datetime.now()

        packet = make_time(time) + make_int(int(time.microsecond / 1000))

        _ = await self.send_rpc(DAQCommand.SET_TIME, packet)
        await self.wait_for_idle()

    async def set_config(self, config: DAQConfiguration) -> None:
        payload = make_int(config.bits()) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    make_int(int(config.interval_time)) + \
                    make_int(int(config.interval_time * 1000) % 1000) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    make_int(int(config.alarm_time)) + \
                    make_int(int(config.alarm_time * 1000) % 1000) + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    self._NULL_INTEGER + \
                    b'\x00\x00\x00\x64'

        analog_channels = config.analog_channels
        if len(analog_channels) < self._CHANNEL_COUNT_ANALOG:
            analog_channels += [DAQAnalogChannel() for _ in range(self._CHANNEL_COUNT_ANALOG - len(analog_channels))]
        elif len(analog_channels) > self._CHANNEL_COUNT_ANALOG:
            raise ValueError('Too many analog channels')

        computed_channels = config.computed_channels
        if len(computed_channels) < self._CHANNEL_COUNT_COMPUTED:
            computed_channels += [DAQComputedChannel() for _ in range(self._CHANNEL_COUNT_COMPUTED - len(computed_channels))]
        elif len(computed_channels) > self._CHANNEL_COUNT_COMPUTED:
            raise ValueError('Too many computed channels')

        equation_buffer = b''
        for chan in analog_channels:
            res, equation = chan.write(len(equation_buffer))
            payload += res
            equation_buffer += equation

        for chan in computed_channels:
            res, equation = chan.write(len(equation_buffer))
            payload += res
            equation_buffer += equation

        payload += equation_buffer

        length_left = CHANNEL_PAYLOAD_LENGTH - len(payload)
        if length_left < 0:
            raise ValueError('Payload too large (too many equations?)')
        elif length_left > 0:
            payload += (b'\x00' * length_left)

        _ = await self.send_rpc(DAQCommand.SET_CONFIG, payload)
        await self.wait_for_idle()

    async def set_monitor_channel(self, channel: int) -> None:
        if channel <= 0:
            _ = await self.send_rpc(DAQCommand.CLEAR_MONITOR_CHANNEL)
        else:
            _ = await self.send_rpc(DAQCommand.SET_MONITOR_CHANNEL, make_int(channel))

    async def get_readings(self, max_readings: int = 0xFF) -> DAQReadingResult:
        data = await self.send_rpc(DAQCommand.GET_READINGS, make_int(max_readings))
        result: list[DAQReading] = []

        chunk_length = parse_int(data[0:])
        chunk_count = parse_int(data[4:])
        instrument_queue = parse_int(data[8:])

        chunks_buf = data[12:]
        for i in range(chunk_count):
            chunk_data = chunks_buf[i * chunk_length:(i + 1) * chunk_length]
            if parse_int(chunk_data[0:]) != 0x10:
                raise Exception('Invalid chunk header')

            result.append(DAQReading(
                time=parse_time(chunk_data[4:]),
                dio=parse_short(chunk_data[12:]),
                alarm1_bitmask=parse_int(chunk_data[16:]),
                alarm2_bitmask=parse_int(chunk_data[20:]),
                totalizer=parse_int(chunk_data[24:]),
                values=[parse_float(chunk_data[i:]) for i in range(28, len(chunk_data), 4)],
            ))

        return DAQReadingResult(readings=result, instrument_queue=instrument_queue)

    async def stop_spy(self) -> None:
        _ = await self.send_rpc(DAQCommand.DISABLE_SPY)

    async def query_spy(self, channel: int) -> float:
        return parse_float(await self.send_rpc(DAQCommand.QUERY_SPY, make_int(channel)))

    async def stop(self) -> None:
        try:
            _ = await self.send_rpc(DAQCommand.STOP)
        except ResponseErrorCodeException:
            pass

    async def start(self) -> None:
        _ = await self.send_rpc(DAQCommand.START, b'\x00' * 16)

    async def handshake(self) -> None:
        await self.ping()
