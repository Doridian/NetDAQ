from struct import pack, unpack
from datetime import datetime

INT_LEN = 4
NULL_INTEGER = b'\x00' * INT_LEN

def parse_int(data: bytes) -> int:
        return int.from_bytes(data[:INT_LEN], 'big')

def parse_short(data: bytes) -> int:
    return int.from_bytes(data[:2], 'big')

def make_int(value: int) -> bytes:
    return int.to_bytes(value, INT_LEN, 'big')

def parse_float(data: bytes) -> float:
    return unpack('>f', data[:4])[0]

def make_float(value: float) -> bytes:
    return pack('>f', value)

def parse_time(data: bytes) -> datetime:
    return datetime(
        hour=data[0],
        minute=data[1],
        second=data[2],
        month=data[3],
        day=data[5],
        year=2000 + data[6], # Well this is gonna break in 2100 lol
        microsecond=(parse_int(data[8:]) & 0xFFFF) * 1000,
    )

def make_time(time: datetime) -> bytes:
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

def make_optional_indexed_bit(bit: int | None) -> bytes:
    if bit is None:
        return NULL_INTEGER
    return make_int(1 << bit)
