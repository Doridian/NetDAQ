from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime

class ResponseErrorCodeException(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f'Response error: {code:08x}')
        self.code = code

class NetDAQ:
    COMMAND_PING             = 0x00000000
    COMMAND_CLOSE            = 0x00000001
    COMMAND_STATUS_QUERY     = 0x00000002
    COMMAND_STOP             = 0x00000068
    COMMAND_SET_TIME         = 0x0000006A
    COMMAND_GET_VERSION_INFO = 0x00000072
    COMMAND_GET_BASE_CHANNEL = 0x00000077
    COMMAND_GET_LC_VERSION   = 0x0000007F
    COMMAND_SET_CHANNELS     = 0x00000081

    _FIXED_HEADER = bytearray([0x46, 0x45, 0x4C, 0x58])
    _HEADER_LEN = 16
    _INT_LEN = 4

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
            self.send_rpc(self.COMMAND_CLOSE)
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
        return 0 # TODO: float.from_bytes(data, 'big')

    def _make_float(self, value: float) -> None:
        return [0,0,0,0] # TODO: implement

    def send_rpc(self, command: int, payload: bytes = b'') -> bytes:
        sequence_id = self.sequence_id
        self.sequence_id += 1

        packet = self._FIXED_HEADER + \
                    self._make_int(sequence_id) + \
                    self._make_int(command) + \
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
        self.send_rpc(self.COMMAND_PING)

    def get_base_channel(self) -> int:
        return self._parse_int(self.send_rpc(self.COMMAND_GET_BASE_CHANNEL))

    def get_version_info(self, command: int = 0) -> list[str]:
        if not command:
            command = self.COMMAND_GET_VERSION_INFO
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
        return self.get_version_info(command=self.COMMAND_GET_LC_VERSION)

    def wait_for_idle(self) -> None:
        while True:
            status = self._parse_int(self.send_rpc(self.COMMAND_STATUS_QUERY))
            if status == 0x00000000:
                break

    def set_time(self, time: datetime | None = None) -> None:
        if not time:
            time = datetime.now()

        packet = bytes([
            time.hour,
            time.minute,
            time.second,
            time.month,
            0x08, # random value
            time.day,
            time.year % 100,
            0x00, # random value
        ]) + self._make_int(time.microsecond / 1000)

        self.send_rpc(self.COMMAND_SET_TIME, packet)
        self.wait_for_idle()

    def set_channels(self, config) -> None:
        # TODO: All of this
        self.wait_for_idle()

    def stop(self) -> None:
        try:
            self.send_rpc(self.COMMAND_STOP)
        except ResponseErrorCodeException:
            pass

    def handshake(self) -> None:
        self.ping()
