from struct import pack, unpack
from datetime import datetime

INT_LEN = 4
NULL_INT = b'\x00' * INT_LEN

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
    now = datetime.now()
    measurement_month = data[3]

    # Handle cases where a measurement came in December 2099
    # but the current date is January 2100 etc...
    decades_year = now.year
    if measurement_month == 12:
        if now.month == 1:
            decades_year -= 1
    decades_year -= decades_year % 100

    return datetime(
        hour=data[0],
        minute=data[1],
        second=data[2],
        month=measurement_month,
        day=data[5],
        year=decades_year + data[6],
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
        return NULL_INT
    return make_int(1 << bit)
